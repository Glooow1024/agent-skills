"""On-demand status window using Tkinter and the Python standard library."""
import argparse
import datetime as dt
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import ttk

from sync import BEIJING, Busy, HERE, Sync, process_lock, read_json, write_json

BG, INK, MUTED, BORDER, ACCENT = '#F3F6F7', '#20343B', '#61757D', '#DDE6E8', '#176B60'
FONT = 'Microsoft YaHei UI'
STATES = {
    'ok': ('已同步', '本地与远端已完成同步', ACCENT),
    'ready': ('已检查', '本地检查完成，等待下一次同步', ACCENT),
    'waiting': ('等待编辑结束', '文件稳定后会自动继续', '#93601B'),
    'pending': ('等待同步', '还有内容将在同步时段处理', '#386F95'),
    'attention': ('需要处理', '查看下方详情，处理后重新同步', '#AD4938'),
    'paused': ('自动同步已暂停', '恢复后将在计划时间继续检查', MUTED),
    'running': ('正在同步', '正在检查本地内容与远端更新', '#386F95'),
}


def display_time(value):
    if not value:
        return '暂无记录'
    try:
        return dt.datetime.fromisoformat(value).astimezone(BEIJING).strftime('%m/%d  %H:%M')
    except (TypeError, ValueError):
        return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    cfg = read_json(args.config)
    worker = Sync(cfg, args.config)
    with process_lock(worker.runtime / 'window.lock'):
        dpi_result = None
        if os.name == 'nt':
            import ctypes
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.SetProcessDpiAwarenessContext.restype = ctypes.c_int
            dpi_result = bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
        root = tk.Tk()
        scale = root.winfo_fpixels('1i') / 96
        write_json(worker.runtime / 'display.json', {'dpi_enabled': dpi_result,
                   'pixels_per_inch': root.winfo_fpixels('1i'), 'tk_version': root.tk.call('info', 'patchlevel')})

        def px(value):
            if isinstance(value, tuple):
                return tuple(px(item) for item in value)
            return round(value * scale)

        root.title('知识库同步')
        root.geometry(f'{px(760)}x{px(650)}')
        root.minsize(px(680), px(600))
        root.configure(bg=BG)
        root.option_add('*Font', (FONT, 10))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('Action.TButton', font=(FONT, 10), padding=px((16, 10)),
                        background='white', foreground=INK, borderwidth=1,
                        bordercolor=BORDER, focusthickness=px(2), focuscolor=ACCENT)
        style.map('Action.TButton', background=[('pressed', '#DEE9EA'), ('active', '#EAF1F2')])
        style.configure('Primary.TButton', font=(FONT, 10, 'bold'), padding=px((20, 10)),
                        background=ACCENT, foreground='white', borderwidth=0,
                        focusthickness=px(2), focuscolor='white')
        style.map('Primary.TButton', background=[('disabled', '#DCE5E5'), ('pressed', '#104C44'), ('active', '#205F57')],
                  foreground=[('disabled', MUTED)])
        style.configure('Vertical.TScrollbar', background='#CEDBDD', troughcolor='white', borderwidth=0, arrowsize=px(12))

        def label(parent, text='', size=10, color=INK, bold=False, **kwargs):
            return tk.Label(parent, text=text, font=(FONT, size, 'bold' if bold else 'normal'),
                            fg=color, bg=parent.cget('bg'), anchor='w', **kwargs)

        def card(parent):
            return tk.Frame(parent, bg='white', highlightbackground=BORDER, highlightthickness=1)

        frame = tk.Frame(root, bg=BG, padx=px(28), pady=px(24))
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        header = tk.Frame(frame, bg=BG)
        header.grid(row=0, column=0, sticky='ew', pady=px((0, 18)))
        label(header, '知识库同步', size=14, bold=True).pack(side='left')
        label(header, 'KNOWLEDGE SYNC', size=10, color=MUTED).pack(side='right', anchor='s', pady=px(3))

        repository = card(frame)
        repository.grid(row=1, column=0, sticky='ew', pady=px((0, 14)))
        repository.columnconfigure(0, weight=1)
        label(repository, Path(cfg['repository']).name, size=11, bold=True).grid(row=0, column=0, sticky='w', padx=px(18), pady=px((12, 0)))
        path_label = label(repository, cfg['repository'], size=10, color=MUTED, justify='left')
        path_label.grid(row=1, column=0, sticky='ew', padx=px(18), pady=px((2, 12)))
        repository.bind('<Configure>', lambda event: path_label.configure(wraplength=max(px(200), event.width - px(40))))

        panel = card(frame)
        panel.grid(row=2, column=0, sticky='nsew', pady=px((0, 14)))
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(2, weight=1)
        heading = label(panel, size=13, bold=True)
        heading.grid(row=0, column=0, columnspan=2, sticky='w', padx=px(20), pady=px((18, 0)))
        subtitle = label(panel, color=MUTED)
        subtitle.grid(row=1, column=0, columnspan=2, sticky='w', padx=px(20), pady=px((3, 14)))
        details = tk.Frame(panel, bg='white')
        details.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=px(20), pady=px((0, 10)))
        details.rowconfigure(0, weight=1)
        details.columnconfigure(0, weight=1)
        text = tk.Text(details, wrap='word', height=4, width=1, relief='flat', bg='white', fg=INK, font=(FONT, 11),
                       padx=px(0), pady=px(4), spacing1=px(3), spacing3=px(6), highlightthickness=0,
                       selectbackground='#D5EAE5', selectforeground=INK, cursor='arrow')
        text.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(details, orient='vertical', command=text.yview)
        scrollbar.grid(row=0, column=1, sticky='ns', padx=px((8, 0)))
        def scroll_position(first, last):
            scrollbar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scrollbar.grid_remove()
            else:
                scrollbar.grid()

        text.configure(yscrollcommand=scroll_position)
        retry_label = label(panel, size=10, color=MUTED)
        retry_label.grid(row=3, column=0, columnspan=2, sticky='ew', padx=px(20), pady=px((0, 16)))

        activity = tk.Frame(frame, bg=BG)
        activity.grid(row=3, column=0, sticky='ew', pady=px((0, 18)))
        time_labels = {}
        for column, (key, title) in enumerate((('checked_at', '最近检查'), ('last_pull', '最近合并远端'), ('last_push', '最近推送检查'))):
            activity.columnconfigure(column, weight=1, uniform='activity')
            item = card(activity)
            item.grid(row=0, column=column, sticky='ew', padx=px((0 if column == 0 else 5, 0 if column == 2 else 5)))
            label(item, title, size=10, color=MUTED).pack(anchor='w', padx=px(14), pady=px((12, 3)))
            value = label(item, size=11)
            value.pack(anchor='w', padx=px(14), pady=px((0, 12)))
            time_labels[key] = value

        buttons = tk.Frame(frame, bg=BG)
        buttons.grid(row=4, column=0, sticky='ew')
        process = None
        launch_error = None
        last = None

        def retry():
            nonlocal process, launch_error
            if process is not None and process.poll() is None:
                return
            try:
                process = subprocess.Popen([cfg['pythonw'], str(HERE / 'sync.py'), 'sync', '--config', args.config],
                                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           creationflags=0x08000000 if os.name == 'nt' else 0)
                launch_error = None
            except OSError as error:
                launch_error = f'无法启动同步：{error}'
            render()

        def pause():
            path = worker.runtime / 'pause.json'
            write_json(path, {'paused': not read_json(path).get('paused', False)})
            render()

        sync_button = ttk.Button(buttons, text='重新同步', style='Primary.TButton', command=retry)
        sync_button.pack(side='left')
        pause_button = ttk.Button(buttons, text='暂停自动同步', style='Action.TButton', command=pause)
        pause_button.pack(side='left', padx=px((10, 0)))
        ttk.Button(buttons, text='查看记录', style='Action.TButton', command=lambda: os.startfile(str(worker.runtime))).pack(side='right')
        ttk.Button(buttons, text='打开知识库', style='Action.TButton', command=lambda: os.startfile(cfg['repository'])).pack(side='right', padx=px((0, 10)))
        schedule = '每天 09:00 · 12:30 · 18:30（北京时间）' if cfg.get('profile') == 'primary' else '登录 / 解锁后拉取 · 每 30 分钟检查'
        label(frame, schedule + '\n关闭窗口后，计划任务仍会自动运行。', size=10, color=MUTED, justify='left').grid(row=5, column=0, sticky='w', pady=px((16, 0)))

        def render():
            nonlocal last
            state = read_json(worker.state_path)
            paused = read_json(worker.runtime / 'pause.json').get('paused', False)
            running = process is not None and process.poll() is None
            key = (str(state), paused, running, launch_error)
            if key == last:
                return
            last = key
            status = 'paused' if paused else 'running' if running else 'attention' if launch_error else state.get('status')
            title, caption, color = STATES.get(status, ('等待首次同步', '到达计划时间后会自动检查', MUTED))
            root.title('知识库同步 · ' + title)
            heading.configure(text=title, fg=color)
            subtitle.configure(text=caption)
            body = launch_error or state.get('message', '尚无同步记录。你也可以点击下方按钮，开始第一次检查。')
            if paused:
                body = '自动同步已暂停。恢复后等待下一次计划检查，或点击“重新同步”。\n\n最近记录：' + body
            elif running:
                body = '正在检查，请稍候。若修改尚未稳定，会安排延后检查。'
            text.configure(state='normal')
            text.delete('1.0', 'end')
            text.insert('1.0', body)
            text.configure(state='disabled')
            for name, value in time_labels.items():
                value.configure(text=display_time(state.get(name)))
            due = state.get('retry', {}).get('at')
            retry_label.configure(text=('已安排检查 · ' + dt.datetime.fromtimestamp(due, BEIJING).strftime('%m/%d %H:%M')
                                        if due and not paused else '关闭窗口不会清除问题，登录或解锁时会再次提醒。' if status == 'attention'
                                        else f"自动提交前，修改需连续 {cfg.get('quiet_minutes', 15)} 分钟保持稳定。"))
            pause_button.configure(text='恢复自动同步' if paused else '暂停自动同步')
            sync_button.configure(text='同步中…' if running else '重新同步', state='disabled' if running or paused else 'normal')

        def refresh():
            render()
            root.after(2000, refresh)

        refresh()
        root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Busy:
        pass  # The existing window already carries the pending reminder.
