"""Small, non-resident Git sync worker. Python standard library + Git only."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
BEIJING = dt.timezone(dt.timedelta(hours=8))
ALLOWED = set(".md .html .htm .png .jpg .jpeg .gif .webp .svg .avif .pdf .mp4 .webm .mp3 .wav .ogg .canvas .base .csv .css .js .mjs .json .woff .woff2 .ttf .wasm".split())


class Blocked(Exception):
    pass


class Busy(Exception):
    pass


def stamp():
    return dt.datetime.now(BEIJING).isoformat(timespec="seconds")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {} if default is None else default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def process_lock(path):
    """OS-owned lock: automatically released even if the worker crashes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as f:
        f.seek(0)
        if not f.read(1):
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            raise Busy("已有任务正在运行")
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def execute(args, cwd=None, env=None, timeout=180):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                          stdin=subprocess.DEVNULL,
                          timeout=timeout, creationflags=0x08000000 if os.name == "nt" else 0)


def image_targets(text):
    # Ignore fenced examples, inline code and comments. Source files stay untouched.
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", text)
    text = re.sub(r"<!--.*?-->|`[^`\n]*`", "", text, flags=re.S)
    for match in re.finditer(r'!\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s]+?))\s*(?:[\"\'][^\n]*?[\"\'])?\s*\)', text):
        yield match.group(1) or match.group(2)
    definitions = dict(re.findall(r'^\s*\[([^\]]+)\]:\s*<?([^>\s]+)>?', text, re.M))
    for match in re.finditer(r'!\[([^\]]*)\]\[([^\]]*)\]', text):
        label = match.group(2) or match.group(1)
        if label in definitions:
            yield definitions[label]
    for match in re.finditer(r'!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]', text):
        yield match.group(1)
    for match in re.finditer(r'<img\b[^>]*\bsrc\s*=\s*[\"\']([^\"\']+)', text, re.I):
        yield html.unescape(match.group(1))


class Sync:
    def __init__(self, config, config_path=None):
        self.cfg = config
        self.config_path = Path(config_path).resolve() if config_path else None
        self.repo = Path(config["repository"]).resolve()
        self.runtime = Path(config["runtime"]).resolve()
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.state_path = self.runtime / "state.json"
        self.state = read_json(self.state_path)
        self.git = config.get("git", "git")
        self.branch = config.get("branch", "main")
        self.remote = config.get("remote", "origin")
        self.env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never",
                    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=20",
                    "GIT_LITERAL_PATHSPECS": "1"}
        # Never inherit an agent/editor's alternate repository or index.
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.env.pop(key, None)

    def g(self, *args, check=True, env=None):
        result = execute([self.git, "-c", "core.quotepath=false", *args], self.repo,
                         {**self.env, **(env or {})})
        if check and result.returncode:
            # Commands never contain credentials; avoid dumping arbitrary remote output.
            detail = result.stderr.decode("utf-8", errors="replace")[-1600:]
            raise Blocked(f"Git {args[0]} 未成功（退出码 {result.returncode}）。\n{detail}")
        return result

    def out(self, *args):
        return self.g(*args).stdout.decode("utf-8").strip()

    def status(self):
        parts = self.g("status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split(b"\0")
        result = []
        i = 0
        while i < len(parts) and parts[i]:
            code, name = parts[i][:2].decode(), parts[i][3:].decode("utf-8")
            result.append((code, name))
            i += 2 if "R" in code or "C" in code else 1
        return result

    def preflight(self):
        if Path(self.out("rev-parse", "--show-toplevel")).resolve() != self.repo:
            raise Blocked("配置路径不是仓库根目录")
        if self.out("branch", "--show-current") != self.branch:
            raise Blocked("当前分支不是配置的同步分支，请先完成手动分支工作")
        expected = self.cfg["remote_url"]
        if self.out("remote", "get-url", self.remote) != expected or self.out("remote", "get-url", "--push", self.remote) != expected:
            raise Blocked("远端地址已变化，请检查配置")
        for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "index.lock"):
            if Path(self.out("rev-parse", "--git-path", name)).is_absolute():
                target = Path(self.out("rev-parse", "--git-path", name))
            else:
                target = self.repo / self.out("rev-parse", "--git-path", name)
            if target.exists():
                raise Blocked(f"Git 有未完成操作或锁文件：{name}；请先处理，不会自动清除")
        if self.g("diff", "--cached", "--quiet", check=False).returncode:
            raise Blocked("已有手动暂存内容，请先完成你的提交")
        if self.out("ls-files", "-u"):
            raise Blocked("仓库存在未解决冲突")

    def snapshot(self, entries):
        result = {}
        for code, name in entries:
            p = self.repo / name
            if p.exists():
                st = p.stat()
                result[name] = [code, st.st_mtime_ns, st.st_size,
                                hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "directory"]
            else:
                result[name] = [code, None, None, None]
        return result

    def validate(self, entries):
        if len(entries) > self.cfg.get("max_changed_files", 40):
            raise Blocked(f"本轮有 {len(entries)} 个文件变化，超过自动提交上限，请人工检查")
        if any("D" in code or "R" in code for code, _ in entries):
            raise Blocked("发现删除或移动文件，请人工核对引用并提交")
        available = set(self.out("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0"))
        for code, name in entries:
            p = self.repo / name
            if code not in (" M", "??"):
                raise Blocked(f"需要人工处理的 Git 状态：{code} {name}")
            if p.suffix.lower() not in ALLOWED or any(part.startswith(".") for part in Path(name).parts) or p.name in ("AGENTS.md", "SKILL.md"):
                raise Blocked(f"文件不在知识内容自动提交范围：{name}")
            if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(self.repo):
                raise Blocked(f"不自动提交链接或特殊文件：{name}")
            if p.stat().st_size > self.cfg.get("max_file_mb", 25) * 1024 * 1024:
                raise Blocked(f"文件超过自动提交大小上限：{name}")
            if p.suffix.lower() in (".md", ".html", ".htm"):
                for url in image_targets(p.read_text(encoding="utf-8-sig")):
                    parsed = urlsplit(url)
                    if not url or url.startswith("#") or parsed.scheme in ("https", "http", "data") or url.startswith("//"):
                        continue
                    if parsed.scheme:
                        raise Blocked(f"图片使用了不可迁移路径：{name}")
                    decoded = unquote(parsed.path)
                    target = (p.parent / decoded).resolve()
                    if not target.is_relative_to(self.repo) or not target.is_file():
                        raise Blocked(f"本地图片或嵌入资源不存在：{name} → {decoded}")
                    relative = target.relative_to(self.repo).as_posix()
                    if relative not in available:
                        raise Blocked(f"图片被 Git 忽略，不会随笔记上传：{name} → {decoded}")

    def stable_delay(self, snapshot):
        now = time.time()
        quiet = self.cfg.get("quiet_minutes", 15) * 60
        latest = max((value[1] / 1e9 for value in snapshot.values() if value[1]), default=now)
        old = self.state.get("observation", {})
        # First observation always waits a full quiet window. This also covers
        # copied/restored files whose preserved mtime is older than the edit.
        changed = old.get("files") != snapshot
        since = now if changed else old.get("since", now)
        self.state["observation"] = {"files": snapshot, "since": since}
        return max(0, quiet - (now - max(latest, since)))

    def fetch_remote(self):
        tracking = f"refs/remotes/{self.remote}/{self.branch}"
        self.g("fetch", "--no-tags", self.remote, f"refs/heads/{self.branch}:{tracking}")
        return self.out("rev-parse", tracking)

    def integrate_remote(self, remote_head):
        head = self.out("rev-parse", "HEAD")
        if self.g("merge-base", "--is-ancestor", remote_head, head, check=False).returncode == 0:
            return remote_head
        if self.status():
            raise Blocked("远端有更新，但本地有未提交修改。请先整理并提交本地修改，再重新检查；未自动暂存或覆盖文件")
        probe = self.g("merge-tree", "--write-tree", head, remote_head, check=False)
        if probe.returncode:
            raise Blocked("本地与远端无法自动合并，请人工处理。冲突预检没有修改工作区，也没有留下进行中的 merge")
        self.preflight()
        if self.status() or self.out("rev-parse", "HEAD") != head:
            raise Blocked("合并前仓库状态发生变化，本轮已暂停")
        self.g("merge", "--no-edit", "--ff", remote_head)
        self.state["last_pull"] = stamp()
        return remote_head

    def commit_snapshot(self, entries, snapshot):
        self.preflight()
        head = self.out("rev-parse", "HEAD")
        index = Path(self.out("rev-parse", "--git-path", "index"))
        if not index.is_absolute():
            index = self.repo / index
        lock = Path(str(index) + ".lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
        except FileExistsError:
            raise Blocked("另一个 Git 操作正在进行，本轮没有提交")
        committed = False
        try:
            with tempfile.TemporaryDirectory(dir=self.runtime) as temporary:
                alt = Path(temporary) / "index"
                paths = Path(temporary) / "paths"
                paths.write_bytes(b"\0".join(name.encode("utf-8") for _, name in entries) + b"\0")
                env = {"GIT_INDEX_FILE": str(alt)}
                self.g("read-tree", head, env=env)
                self.g("add", "--pathspec-from-file=" + str(paths), "--pathspec-file-nul", env=env)
                if self.status() != entries or self.snapshot(entries) != snapshot or self.out("rev-parse", "HEAD") != head:
                    raise Blocked("准备提交时文件或分支发生变化，本轮已暂停")
                self.g("commit", "-m",
                       f"Sync knowledge notes ({len(entries)} files, {stamp()})", env=env)
                committed = True
                data = memoryview(alt.read_bytes())
                while data:
                    data = data[os.write(fd, data):]
                os.close(fd)
                fd = None
                os.replace(lock, index)
        finally:
            if fd is not None:
                os.close(fd)
            if not committed:
                lock.unlink(missing_ok=True)
            # On a post-commit index I/O failure, leave the lock for manual
            # recovery instead of risking a misleading/overwritten real index.
        self.state["last_commit"] = stamp()

    def schedule_retry(self, seconds, action):
        due = time.time() + max(60, seconds)
        self.state["retry"] = {"at": due, "action": action}
        write_json(self.state_path, self.state)
        if self.cfg.get("scheduler_enabled"):
            result = execute(["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                              str(HERE / "retry.ps1"), "-TaskName", self.cfg["task_prefix"] + "-Retry",
                              "-Epoch", str(int(due))], timeout=30)
            if result.returncode:
                raise Blocked("无法安排延后任务，请检查 Windows 任务计划程序；本轮未继续自动提交")

    def record(self, status, message):
        self.state.update(status=status, message=message, checked_at=stamp())
        write_json(self.state_path, self.state)
        log = self.runtime / "sync.log"
        if log.exists() and log.stat().st_size > 1_000_000:
            os.replace(log, self.runtime / "sync.previous.log")
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"time": stamp(), "status": status, "message": message}, ensure_ascii=False) + "\n")

    def run(self, action):
        start = time.perf_counter()
        with process_lock(self.runtime / "worker.lock"):
            self.state = read_json(self.state_path)
            committed_this_run = False
            previous_error = self.state.get("message") if self.state.get("status") == "attention" else None
            try:
                if read_json(self.runtime / "pause.json").get("paused"):
                    self.record("paused", "自动同步已暂停")
                    return self.state
                if action == "retry":
                    pending = self.state.get("retry")
                    if not pending:
                        return self.state
                    action = pending["action"]
                self.state.pop("retry", None)
                self.preflight()
                entries = self.status()
                snapshot = {}
                if action == "inspect":
                    self.validate(entries)
                    if self.state.get("status") != "attention":
                        self.record("ready", f"检查完成：{len(entries)} 个文件变化；未拉取、提交或推送")
                    return self.state
                self.state["last_attempt_" + action] = stamp()
                # Validate before any network/mutation when this is a sync run.
                if action == "sync" and entries:
                    self.validate(entries)
                    snapshot = self.snapshot(entries)
                    delay = self.stable_delay(snapshot)
                    if delay:
                        self.schedule_retry(delay + 2, "sync")
                        self.record("waiting", "正在等待文件连续 15 分钟没有变化；已安排一次延后检查")
                        return self.state
                remote_head = self.fetch_remote()
                if action == "sync":
                    entries = self.status()
                    self.validate(entries)
                    current = self.snapshot(entries)
                    if current != snapshot:
                        self.schedule_retry(self.cfg.get("quiet_minutes", 15) * 60, "sync")
                        self.record("waiting", "检查期间内容发生变化，延后提交")
                        return self.state
                    if entries:
                        self.commit_snapshot(entries, snapshot)
                        committed_this_run = True
                    self.preflight()
                    if self.status():
                        raise Blocked("提交后又出现本地修改，本轮暂停合并与推送；已创建的本地提交会保留")
                self.integrate_remote(remote_head)
                if action == "sync":
                    # Explicit destination; never force, and push only this branch.
                    if self.out("rev-parse", "HEAD") != remote_head:
                        self.g("push", self.remote, f"HEAD:refs/heads/{self.branch}")
                    self.state["last_push"] = stamp()
                    self.state.pop("observation", None)
                if action == "pull":
                    remaining = self.status()
                    self.validate(remaining)
                    if remaining or self.out("rev-parse", "HEAD") != remote_head:
                        self.record("pending", "远端已检查，本地仍有待提交或待推送内容，将在同步时段处理")
                    else:
                        self.record("ok", "本地与远端一致，检查完成")
                else:
                    self.record("ok", "同步完成，本地提交已推送")
            except Exception as error:
                message = str(error)
                if committed_this_run:
                    message += "\n本轮已创建的本地提交会保留，下次同步将重新检查远端。"
                self.record("attention", message)
                if self.cfg.get("notifications") and message != previous_error:
                    self.launch_ui()
            finally:
                self.state["duration_seconds"] = round(time.perf_counter() - start, 3)
                write_json(self.state_path, self.state)
        return self.state

    def launch_ui(self):
        if self.config_path:
            subprocess.Popen([self.cfg.get("pythonw", sys.executable), str(HERE / "status.py"),
                              "--config", str(self.config_path)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x08000000 if os.name == "nt" else 0)


def main():
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "pull", "sync", "retry", "session"])
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    worker = Sync(read_json(args.config), args.config)
    try:
        if args.action == "session":
            if worker.state.get("status") == "attention":
                worker.launch_ui()
            if worker.cfg.get("profile") == "secondary":
                worker.run("pull")
        else:
            result = worker.run(args.action)
            if sys.stdout:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if result.get("status") == "attention" else 0
    except Busy:
        return 0
    return 0


if __name__ == "__main__":
    # pythonw has no stderr. Keep startup failures visible instead of silently
    # returning task result 1 before the regular status handler can run.
    try:
        sys.exit(main())
    except Exception:
        import traceback
        if "--config" in sys.argv:
            config = read_json(sys.argv[sys.argv.index("--config") + 1])
            runtime = Path(config["runtime"])
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "launch-error.log").write_text(traceback.format_exc(), encoding="utf-8")
            previous = read_json(runtime / "state.json")
            previous.update(status="attention", message="任务启动失败，请查看记录中的 launch-error.log", checked_at=stamp())
            write_json(runtime / "state.json", previous)
        raise
