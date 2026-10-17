import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from sync import Blocked, Sync, image_targets, read_json


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return p.stdout.decode("utf-8").strip()


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knowledge-sync-test-")
        self.root = Path(self.tmp.name).resolve()
        self.remote = self.root / "remote.git"
        self.local = self.root / "local"
        self.other = self.root / "other"
        self.remote.mkdir()
        git(self.remote, "init", "--bare", "--initial-branch=main")
        self.local.mkdir()
        git(self.local, "init", "--initial-branch=main")
        self.identity(self.local)
        (self.local / "note.md").write_text("# Initial\n", encoding="utf-8")
        (self.local / ".gitignore").write_text(".obsidian/\n", encoding="utf-8")
        git(self.local, "add", "note.md", ".gitignore")
        git(self.local, "commit", "-m", "Initial")
        git(self.local, "remote", "add", "origin", str(self.remote))
        git(self.local, "push", "-u", "origin", "main")
        git(self.root, "clone", str(self.remote), str(self.other))
        self.identity(self.other)
        self.config = dict(repository=str(self.local), runtime=str(self.root / "state"),
                           remote_url=str(self.remote), quiet_minutes=0, notifications=False)

    def identity(self, repo):
        git(repo, "config", "user.name", "Sync Test")
        git(repo, "config", "user.email", "sync-test@example.invalid")
        git(repo, "config", "commit.gpgsign", "false")
        git(repo, "config", "core.autocrlf", "false")

    def tearDown(self):
        self.tmp.cleanup()

    def worker(self):
        return Sync(self.config)

    def remote_change(self, name="remote.md", text="# Remote\n"):
        (self.other / name).write_text(text, encoding="utf-8")
        git(self.other, "add", "--", name)
        git(self.other, "commit", "-m", "Remote edit")
        git(self.other, "push", "origin", "main")

    def test_sync_commits_new_and_modified_files_with_clean_index(self):
        (self.local / "note.md").write_text("# Edited\n", encoding="utf-8")
        (self.local / "中文 [draft].md").write_text("# New\n", encoding="utf-8")
        result = self.worker().run("sync")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(git(self.local, "status", "--porcelain"), "")
        self.assertEqual(git(self.remote, "rev-parse", "main"), git(self.local, "rev-parse", "HEAD"))

    def test_no_changes_creates_no_empty_commit(self):
        before = git(self.local, "rev-parse", "HEAD")
        self.assertEqual(self.worker().run("sync")["status"], "ok")
        self.assertEqual(before, git(self.local, "rev-parse", "HEAD"))

    def test_pull_fast_forward(self):
        self.remote_change()
        self.assertEqual(self.worker().run("pull")["status"], "ok")
        self.assertTrue((self.local / "remote.md").exists())

    def test_pull_non_conflicting_divergence(self):
        (self.local / "local.md").write_text("local")
        git(self.local, "add", "local.md")
        git(self.local, "commit", "-m", "Local edit")
        self.remote_change()
        result = self.worker().run("pull")
        self.assertEqual(result["status"], "pending", result)
        self.assertEqual(len(git(self.local, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)
        self.assertTrue((self.local / "local.md").exists())

    def test_conflict_preflight_does_not_leave_a_merge_or_touch_notes(self):
        (self.local / "note.md").write_text("# Local\n")
        git(self.local, "add", "note.md")
        git(self.local, "commit", "-m", "Local edit")
        before = git(self.local, "rev-parse", "HEAD")
        self.remote_change("note.md", "# Remote\n")
        result = self.worker().run("pull")
        self.assertEqual(result["status"], "attention")
        self.assertEqual(before, git(self.local, "rev-parse", "HEAD"))
        self.assertEqual((self.local / "note.md").read_text(), "# Local\n")
        self.assertFalse((self.local / ".git/MERGE_HEAD").exists())

    def test_remote_update_with_dirty_worktree_is_preserved(self):
        (self.local / "note.md").write_text("# In progress\n")
        self.remote_change()
        self.assertEqual(self.worker().run("pull")["status"], "attention")
        self.assertEqual((self.local / "note.md").read_text(), "# In progress\n")
        self.assertFalse((self.local / "remote.md").exists())

    def test_staged_content_is_not_touched(self):
        (self.local / "note.md").write_text("# Staged\n")
        git(self.local, "add", "note.md")
        index = (self.local / ".git/index").read_bytes()
        self.assertEqual(self.worker().run("sync")["status"], "attention")
        self.assertEqual(index, (self.local / ".git/index").read_bytes())

    def test_recent_edits_schedule_one_retry_without_commit(self):
        self.config["quiet_minutes"] = 15
        (self.local / "note.md").write_text("# Editing\n")
        before = git(self.local, "rev-parse", "HEAD")
        result = self.worker().run("sync")
        self.assertEqual(result["status"], "waiting")
        self.assertGreater(result["retry"]["at"], time.time() + 890)
        self.assertEqual(before, git(self.local, "rev-parse", "HEAD"))

    def test_missing_image_prevents_commit(self):
        (self.local / "note.md").write_text("![](missing.png)\n")
        self.assertEqual(self.worker().run("sync")["status"], "attention")
        self.assertEqual(git(self.local, "rev-list", "--count", "HEAD"), "1")

    def test_ignored_image_prevents_commit(self):
        (self.local / ".obsidian").mkdir()
        (self.local / ".obsidian/image.png").write_bytes(b"example")
        (self.local / "note.md").write_text("![](.obsidian/image.png)")
        self.assertEqual(self.worker().run("sync")["status"], "attention")

    def test_deletion_and_unknown_files_require_attention(self):
        (self.local / "note.md").unlink()
        self.assertEqual(self.worker().run("sync")["status"], "attention")
        (self.local / "note.md").write_text("# Initial\n")
        (self.local / "credentials.env").write_text("not a note")
        self.assertEqual(self.worker().run("sync")["status"], "attention")

    def test_change_during_staging_leaves_real_index_and_head_untouched(self):
        (self.local / "note.md").write_text("# Ready\n")
        worker = self.worker()
        entries = worker.status()
        snapshot = worker.snapshot(entries)
        head = git(self.local, "rev-parse", "HEAD")
        original = worker.g
        def racing_git(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[0] == "add":
                (self.local / "note.md").write_text("# More edits\n")
            return result
        with patch.object(worker, "g", side_effect=racing_git):
            with self.assertRaises(Blocked):
                worker.commit_snapshot(entries, snapshot)
        self.assertEqual(head, git(self.local, "rev-parse", "HEAD"))
        self.assertEqual(git(self.local, "diff", "--cached"), "")
        self.assertFalse((self.local / ".git/index.lock").exists())

    def test_failed_push_preserves_commit_and_next_run_retries(self):
        (self.local / "note.md").write_text("# Ready\n")
        worker = self.worker()
        original = worker.g
        def unavailable(*args, **kwargs):
            if args[0] == "push":
                raise Blocked("network unavailable")
            return original(*args, **kwargs)
        with patch.object(worker, "g", side_effect=unavailable):
            self.assertEqual(worker.run("sync")["status"], "attention")
        self.assertEqual(git(self.local, "rev-list", "--count", "HEAD"), "2")
        self.assertEqual(git(self.local, "status", "--porcelain"), "")
        self.assertEqual(self.worker().run("sync")["status"], "ok")
        self.assertEqual(git(self.remote, "rev-parse", "main"), git(self.local, "rev-parse", "HEAD"))

    def test_image_parser_ignores_examples_and_handles_html(self):
        targets = list(image_targets('```md\n![](example.png)\n```\n`![](code.png)`\n<img src="image.png">\n![x](<space image.png>)'))
        self.assertEqual(targets, ["space image.png", "image.png"])


if __name__ == "__main__":
    unittest.main()
