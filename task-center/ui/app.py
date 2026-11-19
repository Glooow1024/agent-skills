"""Native desktop hub: shared navigation, asynchronous status, existing service adapters."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading,queue,datetime
from core.backend import *
from adapters import knowledge
from adapters import bindings
BG='#F3F5F7';WHITE='#FFFFFF';INK='#18283D';MUTED='#596C82';NAV='#142235';LINE='#E3E9EF';TEAL='#087F75';FONT='Microsoft YaHei UI'
def text(parent,value,size=11,color=INK,bold=False,**kw):
    return tk.Label(parent,text=value,font=(FONT,size,'bold' if bold else 'normal'),bg=parent.cget('bg'),fg=color,anchor='w',**kw)
def button(parent,label,command,primary=False):
    return ttk.Button(parent,text=label,command=command,style='Primary.TButton' if primary else 'TButton')
def date(value):
    try:return datetime.datetime.fromisoformat(value).strftime('%m/%d  %H:%M')
    except (ValueError,TypeError):return '暂无记录'
def completed(value):
    try:return datetime.datetime.fromtimestamp(float(value),datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d  %H:%M:%S')+'  北京时间'
    except (ValueError,TypeError,OverflowError):return '未记录完成时间'
class App:
    def __init__(self):
        try:
            import ctypes
            # Give the window its own taskbar identity instead of Python's group.
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Orbit.LocalTaskCenter')
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:pass
        self.root=tk.Tk();self.root.title('Orbit  ·  本地任务中心')
        self.root.iconbitmap(str(ROOT/'assets/orbit.ico'))
        self.scale=self.root.winfo_fpixels('1i')/96
        from ctypes import wintypes
        work=wintypes.RECT();ctypes.windll.user32.SystemParametersInfoW(48,0,ctypes.byref(work),0)
        width=min(round(1160*self.scale),work.right-work.left-40)
        height=min(round(790*self.scale),work.bottom-work.top-round(60*self.scale))
        self.root.geometry(f'{width}x{height}+{work.left+max(0,(work.right-work.left-width)//2)}+{work.top+20}')
        self.root.minsize(min(round(1000*self.scale),width),min(round(600*self.scale),height))
        self.root.update_idletasks()
        try:
            import ctypes
            hwnd=ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Load the ICO frame matching the real DPI, avoiding Tk's 32px
            # iconphoto intermediate and Windows enlarging it on the taskbar.
            user32=ctypes.windll.user32
            user32.LoadImageW.argtypes=[wintypes.HINSTANCE,wintypes.LPCWSTR,wintypes.UINT,ctypes.c_int,ctypes.c_int,wintypes.UINT]
            user32.LoadImageW.restype=wintypes.HANDLE
            user32.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            user32.SendMessageW.restype=wintypes.LPARAM
            self.native_icons=[]
            dpi=round(96*self.scale)
            for kind,metric in [(1,11),(0,49)]:
                size=user32.GetSystemMetricsForDpi(metric,dpi)
                icon=user32.LoadImageW(None,str(ROOT/'assets/orbit.ico'),1,size,size,0x10)
                if icon:
                    self.native_icons.append(icon)
                    user32.SendMessageW(hwnd,0x80,kind,icon)
            for attr,value in [(20,1),(35,0x352214),(36,0xFFFFFF)]:
                data=ctypes.c_int(value);ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,attr,ctypes.byref(data),4)
        except Exception:pass
        self.root.configure(bg=BG);self.root.option_add('*Font',(FONT,10))
        style=ttk.Style();style.theme_use('clam')
        style.configure('TButton',font=(FONT,10),padding=(18,10),background=WHITE,foreground=INK,borderwidth=1,bordercolor=LINE,focusthickness=0)
        style.map('TButton',background=[('active','#EAF1F5')],foreground=[('disabled','#A6AFBA')])
        style.configure('Primary.TButton',background=TEAL,foreground=WHITE,borderwidth=0)
        style.map('Primary.TButton',background=[('disabled','#C9D9D8'),('active','#06695F')],foreground=[('disabled','#7B9390')])
        style.layout('Orbit.Vertical.TScrollbar',[
            ('Vertical.Scrollbar.trough',{'sticky':'ns','children':[
                ('Vertical.Scrollbar.thumb',{'expand':'1','sticky':'nswe'})]})])
        style.configure('Orbit.Vertical.TScrollbar',background='#CDD7DF',troughcolor=BG,
            bordercolor=BG,lightcolor='#CDD7DF',darkcolor='#CDD7DF',borderwidth=0,
            arrowsize=round(8*self.scale),width=round(8*self.scale),gripcount=0)
        style.map('Orbit.Vertical.TScrollbar',background=[('pressed',TEAL),('active','#9BAFBF')],
            lightcolor=[('pressed',TEAL),('active','#9BAFBF')],
            darkcolor=[('pressed',TEAL),('active','#9BAFBF')])
        self.page='home';self.selected=None;self.knowledge_id=None;self.knowledge_states={};self.busy=False;self.inbox=queue.Queue();self.cache={};self.k={};self.notice=''
        self.sidebar=tk.Frame(self.root,bg=NAV,width=round(245*self.scale));self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
        self.logo=tk.PhotoImage(file=str(ROOT/'assets/orbit.png'))
        tk.Label(self.sidebar,image=self.logo,bg=NAV).pack(anchor='w',padx=23,pady=(24,8))
        text(self.sidebar,'ORBIT / LOCAL HUB',11,'#7EADA9',True).pack(anchor='w',padx=25,pady=(0,4))
        text(self.sidebar,'本地任务中心',19,WHITE,True).pack(anchor='w',padx=25,pady=(0,35))
        self.nav={}
        for key,label in [('home','总览'),('bridge','消息桥接'),('knowledge','知识库同步'),('monitors','训练监测'),('services','其他本地服务'),('history','已完成记录')]:
            b=tk.Button(self.sidebar,text='  '+label,anchor='w',font=(FONT,11),bg=NAV,fg='#B9C6D6',activebackground='#253B50',activeforeground=WHITE,
                relief='flat',bd=0,padx=18,pady=14,cursor='hand2',command=lambda p=key:self.go(p))
            b.pack(fill='x',padx=12,pady=3);self.nav[key]=b
        text(self.sidebar,'本地运行 · 私有控制',10,'#7D91A9').pack(side='bottom',anchor='w',padx=25,pady=26)
        host=tk.Frame(self.root,bg=BG);host.pack(side='left',fill='both',expand=True)
        self.canvas=tk.Canvas(host,bg=BG,highlightthickness=0)
        self.scrollbar=ttk.Scrollbar(host,orient='vertical',command=self.canvas.yview,style='Orbit.Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=self.scrollbar.set);self.canvas.pack(side='left',fill='both',expand=True)
        self.scroll_visible=False
        self.main=tk.Frame(self.canvas,bg=BG,padx=28,pady=18)
        self.content_id=self.canvas.create_window(0,0,window=self.main,anchor='nw')
        self.layout_size=None
        def fit(event=None):
            width=self.canvas.winfo_width();height=max(self.main.winfo_reqheight(),self.canvas.winfo_height())
            overflow=self.main.winfo_reqheight()>self.canvas.winfo_height()+2
            if overflow!=self.scroll_visible:
                self.scroll_visible=overflow
                if overflow:self.scrollbar.pack(side='right',fill='y',padx=(0,round(5*self.scale)),pady=round(10*self.scale))
                else:
                    self.scrollbar.pack_forget()
                    self.canvas.yview_moveto(0)
            if self.layout_size==(width,height):return
            self.layout_size=(width,height)
            self.canvas.itemconfigure(self.content_id,width=width,height=height)
            self.canvas.configure(scrollregion=(0,0,width,height))
        self.canvas.bind('<Configure>',fit);self.main.bind('<Configure>',fit)
        self.root.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units') if self.scroll_visible else None)
        self.draw();self.refresh_data();self.root.after(150,self.poll)
    def go(self,page,selected=None):
        self.page=page;self.selected=selected;self.notice=''
        if page=='bridge':
            rows=[s for s in registry() if s.get('kind')=='message-bridge']
            if len(rows)==1:self.selected=rows[0]['id']
            else:self.page='bridges'
        if page=='knowledge':
            rows=[s for s in registry() if s.get('kind')=='knowledge-sync']
            if selected:self.knowledge_id=selected
            elif len(rows)==1:self.knowledge_id=rows[0]['id']
            else:self.page='knowledge_instances'
            self.k=self.knowledge_states.get(self.knowledge_id,{})
        self.draw();self.canvas.yview_moveto(0)
    def card(self,parent=None):
        return tk.Frame(parent or self.main,bg=WHITE,highlightbackground=LINE,highlightthickness=1,padx=22,pady=14)
    def dynamic(self,parent,fn,size=11,color=INK,bold=False,**kw):
        w=text(parent,fn(),size,color,bold,**kw)
        self.updates.append(lambda w=w,fn=fn:self.set_text(w,fn()))
        return w
    def set_text(self,w,value):
        value=str(value)
        if w.cget('text')!=value:w.config(text=value)
    def wrapped(self,parent,value):
        w=text(parent,value,10,MUTED,wraplength=300,justify='left')
        w.pack(fill='x',anchor='w')
        parent.bind('<Configure>',lambda e:w.config(wraplength=max(120,e.width-48)),add='+')
        return w
    def heading(self,title,subtitle):
        text(self.main,title,24,bold=True).pack(anchor='w',pady=(0,7))
        text(self.main,subtitle,10,MUTED,wraplength=800,justify='left').pack(anchor='w',pady=(0,24))
    def draw(self):
        self.updates=[]
        for w in self.main.winfo_children():w.destroy()
        for key,b in self.nav.items():b.config(bg='#244237' if key==self.page else NAV,fg=WHITE if key==self.page else '#B9C6D6')
        if self.page=='home':self.home()
        elif self.page in ('monitors','services','history'):self.monitors()
        elif self.page in ('bridges','knowledge_instances'):self.instance_list()
        elif self.page=='knowledge':self.knowledge_page()
        else:self.detail()
        self.footer=self.dynamic(self.main,lambda:self.notice or '每 5 秒更新状态  ·  关闭窗口不停止后台服务',10,MUTED,wraplength=800,justify='left')
        self.footer.pack(side='bottom',anchor='w',pady=(16,0))
    def home(self):
        self.heading('工作台','消息、知识与实验状态。选择一个功能，查看详情或进行操作。')
        stats=tk.Frame(self.main,bg=BG);stats.pack(fill='x',pady=(0,22))
        for i,(value,label) in enumerate([(str(sum(bool(s.get('pids')) for s in self.cache.values())),'本地服务运行中'),(str(sum(s.get('hidden',False) for s in self.cache.values())),'任务已归档'),('自动','消息桥接登录启动')]):
            stats.columnconfigure(i,weight=1,uniform='stat');c=self.card(stats);c.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 7,0 if i==2 else 7))
            fn=(lambda:str(sum(bool(s.get('pids')) for s in self.cache.values()))) if i==0 else (lambda:str(sum(s.get('hidden',False) for s in self.cache.values()))) if i==1 else (lambda:'自动')
            self.dynamic(c,fn,25,TEAL,True).pack(anchor='w');text(c,label,10,MUTED).pack(anchor='w',pady=(5,0))
        grid=tk.Frame(self.main,bg=BG);grid.pack(fill='both',expand=True)
        cards=[('01','消息桥接','通过飞书接收指令，将处理结果带回群聊。','bridge',next((x.get('status','读取状态…') for x in self.cache.values() if x.get('kind')=='message-bridge'),'未配置')),
               ('02','知识库同步','保留原同步计划，查看变化与最近同步记录。','knowledge',self.k.get('status','读取状态…')),
               ('03','训练监测','巡检、通知与看板，按实验查看和管理。','monitors','查看活动任务'),
               ('04','已完成记录','完成的实验自动归档，让活动列表保持清晰。','history','保留历史记录')]
        for i,(n,title,desc,page,status) in enumerate(cards):
            grid.columnconfigure(i%2,weight=1,uniform='cards');grid.rowconfigure(i//2,weight=1)
            c=self.card(grid);c.grid(row=i//2,column=i%2,sticky='nsew',padx=(0 if i%2==0 else 8,8 if i%2==0 else 0),pady=(0,16))
            text(c,n,10,TEAL,True).pack(anchor='w');text(c,title,17,bold=True).pack(anchor='w',pady=(8,6))
            self.wrapped(c,desc)
            button(c,'进入  →',lambda p=page:self.go(p)).pack(side='bottom',anchor='e',pady=(12,0))
            fn=(lambda:next((x.get('status','读取状态…') for x in self.cache.values() if x.get('kind')=='message-bridge'),'未配置')) if page=='bridge' else (lambda:self.k.get('status','读取状态…')) if page=='knowledge' else (lambda value=status:value)
            self.dynamic(c,fn,10,TEAL).pack(anchor='w',pady=(12,0))
    def monitors(self):
        history=self.page=='history';self.heading('已完成记录' if history else '其他本地服务' if self.page=='services' else '训练监测','完成并停止的任务会自动从活动列表撤下。手动停止或异常退出的任务仍保留。')
        rows=self.visible_rows()
        self.row_ids=tuple(d['id'] for d in rows)
        for d in rows:
            c=self.card();c.pack(fill='x',pady=(0,12));line=tk.Frame(c,bg=WHITE);line.pack(fill='x')
            text(line,d['name'],13,bold=True).pack(side='left');self.dynamic(line,lambda key=d['id']:self.cache[key]['status'],10,TEAL).pack(side='right')
            text(c,d['description'],10,MUTED,wraplength=730,justify='left').pack(anchor='w',pady=(8,12))
            if history:self.dynamic(c,lambda key=d['id']:'完成于 '+completed(self.cache[key].get('completed_at')),10,MUTED).pack(anchor='w',pady=(0,8))
            button(c,'查看详情  →',lambda key=d['id']:self.go('detail',key)).pack(anchor='e')
        if not rows:text(self.main,'这里暂时没有任务。',12,MUTED).pack(anchor='w',pady=30)
    def instance_list(self):
        kind='message-bridge' if self.page=='bridges' else 'knowledge-sync'
        self.heading('消息桥接' if kind=='message-bridge' else '知识库同步','每个实例使用独立配置与运行记录。')
        for row in registry():
            if row.get('kind')!=kind:continue
            c=self.card();c.pack(fill='x',pady=(0,12))
            text(c,row['name'],13,bold=True).pack(anchor='w')
            text(c,row.get('project',''),10,MUTED).pack(anchor='w',pady=8)
            button(c,'查看详情 →',lambda row=row:self.go('knowledge' if kind=='knowledge-sync' else 'detail',row['id'])).pack(anchor='e')
    def knowledge_instance(self):
        return next((s for s in registry() if s['id']==self.knowledge_id),None)
    def detail(self):
        s=next(x for x in registry() if x['id']==self.selected);d=self.cache.get(s['id'],{})
        self.heading(s['name'],s['description']);c=self.card();c.pack(fill='x')
        text(c,'服务状态',10,MUTED).pack(anchor='w');self.dynamic(c,lambda:self.cache.get(s['id'],{}).get('status','读取状态…'),22,TEAL,True).pack(anchor='w',pady=(8,20))
        age=d.get('age');info=[('本地进程',', '.join(map(str,d.get('pids',[]))) or '无'),('最近心跳',f'{int(age)} 秒前' if age is not None else '暂无记录')]
        if s.get('kind')=='message-bridge':info += [('待处理请求',str(read(BASE/s['health']).get('unfinished','未知'))),('启动方式','Windows 登录后自动启动')]
        if d.get('done'):info += [('完成时间',completed(d.get('completed_at')))]
        for name,value in info:
            row=tk.Frame(c,bg=WHITE);row.pack(fill='x',pady=7);text(row,name,10,MUTED).pack(side='left')
            def field(name=name,value=value):
                now=self.cache.get(s['id'],{})
                if name=='本地进程':return ', '.join(map(str,now.get('pids',[]))) or '无'
                if name=='最近心跳':return f"{int(now['age'])} 秒前" if now.get('age') is not None else '暂无记录'
                if name=='待处理请求':return str(read(BASE/s['health']).get('unfinished','未知'))
                return value
            self.dynamic(row,field,11).pack(side='right')
        row=tk.Frame(self.main,bg=BG);row.pack(fill='x',pady=22)
        b=button(row,'启动服务',lambda:self.action(lambda:start(s)),True);b.pack(side='left');b.config(state='disabled' if self.busy or d.get('pids') or d.get('done') else 'normal')
        self.updates.append(lambda b=b:b.config(state='disabled' if self.busy or self.cache.get(s['id'],{}).get('pids') or self.cache.get(s['id'],{}).get('done') else 'normal'))
        b=button(row,'停止服务',lambda:self.action(lambda:stop(s)));b.pack(side='left',padx=12);b.config(state='disabled' if self.busy or not d.get('pids') else 'normal')
        self.updates.append(lambda b=b:b.config(state='disabled' if self.busy or not self.cache.get(s['id'],{}).get('pids') else 'normal'))
        button(row,'打开日志',lambda:os.startfile(str(BASE/s['folder']))).pack(side='right')
        if s.get('kind')=='message-bridge':
            button(row,'管理任务绑定',lambda:self.binding_editor(s)).pack(side='left')
        text(self.main,'停止只影响本地服务，不会停止远端训练。\n桥接手动停止后，本次登录期间保持停止；下次登录恢复。' if s.get('kind')=='message-bridge' else '停止只影响本地监测，不会停止远端训练。',10,MUTED,justify='left').pack(anchor='w')
    def binding_editor(self,service):
        try:path,data,version=bindings.load(service)
        except Exception as exc:
            messagebox.showerror('无法读取绑定',str(exc),parent=self.root);return
        window=tk.Toplevel(self.root);window.title('Orbit · 任务绑定');window.configure(bg=BG)
        window.iconbitmap(str(ROOT/'assets/orbit.ico'))
        width=round(820*self.scale);height=round(600*self.scale)
        window.geometry(f'{width}x{height}');window.minsize(width, height)
        window.update_idletasks()
        try:
            import ctypes
            hwnd=ctypes.windll.user32.GetParent(window.winfo_id())
            for kind,icon in zip((1,0),self.native_icons):ctypes.windll.user32.SendMessageW(hwnd,0x80,kind,icon)
        except Exception:pass
        style=ttk.Style(window)
        style.layout('Bindings.Treeview',[('Treeview.treearea',{'sticky':'nswe'})])
        style.configure('Bindings.Treeview',font=(FONT,10),rowheight=round(38*self.scale),
                        background=WHITE,fieldbackground=WHITE,foreground=INK,borderwidth=0)
        style.configure('Bindings.Treeview.Heading',font=(FONT,9),background='#EDF2F5',foreground=MUTED,
                        relief='flat',padding=(12,10))
        style.map('Bindings.Treeview',background=[('selected','#DDF2EE')],foreground=[('selected','#07685F')])
        style.configure('Bindings.TEntry',font=(FONT,10),padding=(10,9),bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
        frame=tk.Frame(window,bg=BG,padx=round(26*self.scale),pady=round(20*self.scale));frame.pack(fill='both',expand=True)
        header=tk.Frame(frame,bg=BG);header.pack(fill='x',pady=(0,18))
        text(header,'控制群 / 消息路由',9,TEAL,True).pack(anchor='w')
        text(header,'管理任务绑定',19,bold=True).pack(anchor='w',pady=(5,6))
        text(header,'为每个聊天取一个好记的名字，在飞书中用 /发 或 /切换 选择任务。',10,MUTED).pack(anchor='w')
        list_card=tk.Frame(frame,bg=WHITE,padx=16,pady=14,highlightbackground=LINE,highlightthickness=1)
        list_card.pack(fill='both',expand=True)
        list_title=tk.Frame(list_card,bg=WHITE);list_title.pack(fill='x',pady=(0,12))
        text(list_title,'已绑定任务',11,bold=True).pack(side='left')
        text(list_title,'选择一行，在下方编辑',9,MUTED).pack(side='right')
        list_host=tk.Frame(list_card,bg=WHITE);list_host.pack(fill='both',expand=True)
        tree=ttk.Treeview(list_host,columns=('alias','thread','default'),show='headings',height=3,style='Bindings.Treeview',selectmode='browse')
        for key,label,colwidth in [('alias','任务别名',170),('thread','Codex 聊天 ID',440),('default','默认任务',90)]:
            tree.heading(key,text=label,anchor='w');tree.column(key,width=round(colwidth*self.scale),minwidth=round(70*self.scale),anchor='w')
        tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(list_host,orient='vertical',command=tree.yview,style='Orbit.Vertical.TScrollbar')
        def scroll_state(first,last):
            scroll.set(first,last)
            if float(first)>0 or float(last)<1:scroll.pack(side='right',fill='y')
            else:scroll.pack_forget()
        tree.configure(yscrollcommand=scroll_state)
        list_actions=tk.Frame(list_card,bg=WHITE);list_actions.pack(fill='x',pady=(12,0))
        form=tk.Frame(frame,bg=WHITE,padx=16,pady=14,highlightbackground=LINE,highlightthickness=1)
        form.pack(fill='x',pady=(14,0))
        text(form,'编辑绑定',11,bold=True).pack(anchor='w',pady=(0,10))
        form_fields=tk.Frame(form,bg=WHITE);form_fields.pack(fill='x')
        form_fields.columnconfigure(0,weight=1);form_fields.columnconfigure(1,weight=3)
        fields={}
        for column,(key,label) in enumerate([('alias','任务别名'),('thread_id','Codex 聊天 ID')]):
            row=tk.Frame(form_fields,bg=WHITE);row.grid(row=0,column=column,sticky='ew',padx=(0,14) if column==0 else 0)
            text(row,label,9,MUTED).pack(anchor='w',pady=(0,5));fields[key]=tk.StringVar()
            ttk.Entry(row,textvariable=fields[key],style='Bindings.TEntry',width=18 if column==0 else 42).pack(fill='x')
        form_actions=tk.Frame(form,bg=WHITE);form_actions.pack(fill='x',pady=(12,0))
        text(form_actions,'聊天 ID 请从对应聊天核实。',9,MUTED).pack(side='left')
        hint=tk.StringVar(value='保存后对新消息生效，已入队消息保持原目标。')
        footer=tk.Frame(frame,bg=BG);footer.pack(fill='x',pady=(16,0))
        text_label=tk.Label(footer,textvariable=hint,font=(FONT,9),bg=BG,fg=MUTED,anchor='w',justify='left',wraplength=round(540*self.scale))
        text_label.pack(side='left',fill='x',expand=True)
        def refresh():
            tree.delete(*tree.get_children())
            for alias,target in data['tasks'].items():tree.insert('', 'end',iid=alias,values=(alias,target['thread_id'],'● 默认' if alias==data['default'] else '—'))
        def select(event=None):
            selected=tree.selection()
            if selected:
                alias=selected[0];fields['alias'].set(alias);fields['thread_id'].set(data['tasks'][alias]['thread_id'])
        tree.bind('<<TreeviewSelect>>',select)
        def edit():
            alias=fields['alias'].get().strip();target=fields['thread_id'].get().strip()
            candidate=json.loads(json.dumps(data));candidate['tasks'][alias]=dict(candidate['tasks'].get(alias,{}),thread_id=target)
            try:bindings.routing.validate(candidate)
            except ValueError as exc:hint.set(str(exc));return
            data.update(candidate);refresh();hint.set('已更新草稿；点击保存生效。修改别名请新增后删除旧项。')
        def remove():
            selected=tree.selection()
            if not selected:return
            alias=selected[0]
            if alias==data['default']:hint.set('请先选择另一个默认任务，再删除此项。');return
            del data['tasks'][alias];refresh();hint.set('已从草稿移除；点击保存生效。')
        def default():
            selected=tree.selection()
            if selected:data['default']=selected[0];refresh()
        def persist():
            nonlocal version
            try:version=bindings.store(path,data,version)
            except Exception as exc:hint.set(str(exc));return
            hint.set('已保存，新消息立即生效；原绑定备份保存在本机。')
        button(list_actions,'设为默认',default).pack(side='left')
        button(list_actions,'移除所选',remove).pack(side='left',padx=8)
        button(form_actions,'新增 / 更新草稿',edit).pack(side='right')
        button(footer,'保存绑定',persist,True).pack(side='right',padx=(16,0))
        refresh()
        if data['tasks']:
            tree.selection_set(data['default']);select()
        return window
    def knowledge_page(self):
        k=self.k;self.heading('知识库同步','Knowledge Sync  /  沿用原有同步规则与计划任务')
        c=self.card();c.pack(fill='x',pady=(0,16));text(c,Path(k.get('repository','knowledge_base')).name,13,bold=True).pack(anchor='w')
        text(c,k.get('repository','读取配置…'),10,MUTED).pack(anchor='w',pady=(6,0))
        c=self.card();c.pack(fill='both',expand=True);self.dynamic(c,lambda:self.k.get('status','读取状态…'),22,TEAL,True).pack(anchor='w',pady=(0,14))
        box=tk.Text(c,height=5,wrap='word',font=(FONT,11),fg=INK,bg=WHITE,bd=0,highlightthickness=0)
        box.pack(fill='both',expand=True);box.insert('1.0',k.get('message',''));box.config(state='disabled')
        def update_message():
            value=self.k.get('message','')
            if box.get('1.0','end-1c')!=value:
                box.config(state='normal');box.delete('1.0','end');box.insert('1.0',value);box.config(state='disabled')
        self.updates.append(update_message)
        stats=tk.Frame(self.main,bg=BG);stats.pack(fill='x',pady=16)
        for i,(key,title) in enumerate([('checked_at','最近检查'),('last_pull','最近合并远端'),('last_push','最近推送检查')]):
            stats.columnconfigure(i,weight=1,uniform='times');c=self.card(stats);c.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 6,0 if i==2 else 6))
            text(c,title,10,MUTED).pack(anchor='w');self.dynamic(c,lambda key=key:date(self.k.get(key)),12,bold=True).pack(anchor='w',pady=(8,0))
        row=tk.Frame(self.main,bg=BG);row.pack(fill='x')
        b=button(row,'立即同步',lambda:self.action(lambda:knowledge.sync_now(self.knowledge_instance())),True);b.pack(side='left');b.config(state='disabled' if self.busy or k.get('paused') or k.get('running') or not k.get('repository') else 'normal')
        self.updates.append(lambda b=b:b.config(state='disabled' if self.busy or self.k.get('paused') or self.k.get('running') or not self.k.get('repository') else 'normal'))
        b=button(row,'恢复自动同步' if k.get('paused') else '暂停自动同步',lambda:self.action(lambda:knowledge.toggle_pause(self.knowledge_instance())));b.pack(side='left',padx=10)
        self.updates.append(lambda b=b:b.config(text='恢复自动同步' if self.k.get('paused') else '暂停自动同步',state='disabled' if self.busy else 'normal'))
        button(row,'打开知识库',lambda:os.startfile(self.k['repository'])).pack(side='right')
        button(row,'查看记录',lambda:os.startfile(self.k['runtime'])).pack(side='right',padx=10)
        text(self.main,'原计划：每天 09:00 / 12:30 / 18:30（北京时间）' if k.get('profile')=='primary' else '原计划：登录、解锁后拉取，每 30 分钟检查',10,MUTED).pack(anchor='w',pady=(16,0))
    def action(self,fn):
        if self.busy:return
        self.busy=True;self.notice='正在处理…';self.update_values()
        def work():
            try:r=fn()
            except Exception as e:r='操作未完成：'+str(e)
            self.inbox.put(('result',r))
        threading.Thread(target=work,daemon=True).start()
    def refresh_data(self):
        def work():
            try:
                items=inventory()
                rows=registry()
                values={s['id']:knowledge.state(items,s) for s in rows if s.get('kind')=='knowledge-sync'}
                states={s['id']:snapshot(s,items) for s in rows}
                for ident,value in values.items():states[ident]['status']=value['status']
                self.inbox.put(('data',(states,values)))
            except Exception as e:self.inbox.put(('error',str(e)))
        threading.Thread(target=work,daemon=True).start()
    def update_values(self):
        if self.page in ('monitors','services','history'):
            ids=tuple(d['id'] for d in self.visible_rows())
            if ids!=getattr(self,'row_ids',()):self.draw();return
        for update in self.updates:update()
    def visible_rows(self):
        return [d for d in self.cache.values() if d.get('kind') not in ('message-bridge','knowledge-sync') and d['id']!='bridge' and
            (d['hidden'] if self.page=='history' else not d['hidden'] and
             ((d['group']=='训练监测') if self.page=='monitors' else d['group']!='训练监测'))]
    def poll(self):
        try:
            while True:
                kind,data=self.inbox.get_nowait()
                if kind=='data':
                    self.cache,self.knowledge_states=data
                    if not self.knowledge_id:self.knowledge_id=next(iter(self.knowledge_states),None)
                    self.k=self.knowledge_states.get(self.knowledge_id,{})
                    self.update_values();self.root.after(5000,self.refresh_data)
                elif kind=='result':self.busy=False;self.notice=data;self.update_values()
                else:self.notice='状态读取失败：'+data;self.update_values();self.root.after(5000,self.refresh_data)
        except queue.Empty:pass
        self.root.after(150,self.poll)
    def run(self):self.root.mainloop()
if __name__=='__main__':App().run()
