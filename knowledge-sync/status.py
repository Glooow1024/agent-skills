"""Persistent attention window; starts only on demand or when an issue occurs."""
import argparse
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import ttk

from sync import Busy, HERE, Sync, process_lock, read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = read_json(args.config)
    worker = Sync(cfg, args.config)
    with process_lock(worker.runtime / "window.lock"):
        root = tk.Tk()
        root.title("知识库同步")
        root.geometry("640x430")
        root.minsize(520, 360)
        root.option_add("*Font", "{Microsoft YaHei UI} 10")
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        heading = ttk.Label(frame, text="知识库同步", font=("Microsoft YaHei UI", 16, "bold"))
        heading.pack(anchor="w")
        text = tk.Text(frame, wrap="word", height=14, relief="flat", padx=8, pady=8)
        text.pack(fill="both", expand=True, pady=12)
        last = None

        def refresh():
            nonlocal last
            state = read_json(worker.state_path)
            paused = read_json(worker.runtime / "pause.json").get("paused", False)
            key = (str(state), paused)
            if key != last:
                last = key
                title = {"attention": "需要处理", "waiting": "等待编辑结束", "pending": "等待同步时段", "ok": "已同步", "ready": "已检查", "paused": "已暂停"}.get(state.get("status"), "尚未运行")
                if paused:
                    title = "已暂停"
                root.title("知识库同步 · " + title)
                heading.configure(text=title)
                body = f"仓库：{cfg['repository']}\n\n{state.get('message', '到达计划时间后将自动检查。')}\n\n"
                body += f"上次检查：{state.get('checked_at', '—')}\n上次拉取更新：{state.get('last_pull', '—')}\n上次推送检查：{state.get('last_push', '—')}\n"
                if state.get("retry"):
                    import datetime
                    body += "下次延后检查：" + datetime.datetime.fromtimestamp(state["retry"]["at"]).strftime("%Y-%m-%d %H:%M:%S") + "\n"
                body += "\n问题解决后点击“重新同步”。关闭窗口不会清除待处理状态。"
                text.configure(state="normal")
                text.delete("1.0", "end")
                text.insert("1.0", body)
                text.configure(state="disabled")
                pause_button.configure(text="恢复自动同步" if paused else "暂停自动同步")
            root.after(2000, refresh)

        def retry():
            subprocess.Popen([cfg["pythonw"], str(HERE / "sync.py"), "sync", "--config", args.config],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x08000000)

        def pause():
            path = worker.runtime / "pause.json"
            write_json(path, {"paused": not read_json(path).get("paused", False)})

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="重新同步", command=retry).pack(side="left", padx=3)
        pause_button = ttk.Button(buttons, text="暂停自动同步", command=pause)
        pause_button.pack(side="left", padx=3)
        ttk.Button(buttons, text="打开知识库", command=lambda: os.startfile(cfg["repository"])).pack(side="left", padx=3)
        ttk.Button(buttons, text="查看记录", command=lambda: os.startfile(str(worker.runtime))).pack(side="left", padx=3)
        refresh()
        root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Busy:
        pass  # An existing taskbar window already carries the pending reminder.
