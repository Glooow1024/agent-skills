# Orbit · 本地任务中心

跨项目Windows桌面入口。代码、实例配置、运行记录分离；关闭界面不停止后台服务。

## 目录与职责

- `ui/app.py`：界面与动态刷新；页面每5秒后台采样，更新现有控件，内容溢出才显示滚动条。
- `core/backend.py`：实例注册读取、精确进程识别、启停与完成归档。
- `core/supervisor.py`：登录后守护显式启用自启的消息桥接；不启动训练。
- `adapters/knowledge.py`：按注册实例读取知识库状态和调用同步服务。
- 同级`services/message-bridge`、`services/knowledge-sync`、`services/training-monitor`：可独立运行的通用服务。
- `orbit.py`是唯一正式入口：gui打开窗口，supervise运行登录守护，register登记实例。包内直接导入core/ui/adapters，无转发模块。

## 本机配置与历史

注册表唯一位置为 **`%USERPROFILE%/.orbit/services.json`**，本机即 **`C:/Users/Lenovo/.orbit/services.json`**。程序直接读取此文件，代码目录不保存注册表或指针文件。`%USERPROFILE%/.orbit/instances/`保存监测实例配置，`%USERPROFILE%/.orbit/installation.json`保存安装根目录。原飞书私密配置和知识库配置继续作为唯一来源，通过引用使用，不复制密钥。

各实例的runtime/health/terminal/folder显式登记。现有桥接SQLite、delivery、acks、监测state/outbox/事件与完成回执全部保留原路径，因此在途请求和历史绝对路径仍有效。新的实例应使用独立目录。迁移备份在本机`.orbit/backups`，迁移验收见本目录runtime/migration_verification.json。

## 桌面与自启

桌面调用`orbit.py gui`；登录Startup调用`orbit.py supervise --boot`。

`install.ps1`安装依赖、初始化本机目录，并创建“本地任务中心”桌面入口和“Orbit 本地服务”登录Startup项；`-NoLaunch`仍完成安装，只跳过启动界面和守护进程。登录守护仅对kind=message-bridge且autostart=true的实例生效。bootstrap_codex=true时准备默认本机18773传输；使用其他endpoint应自行提供对应传输。

手动停止某桥接只暂停该实例，本次登录期间不自动拉起；下次登录恢复。其他监测不会因登记自动启动。知识库仍由既有Windows计划任务调度。

消息桥接详情中的“管理任务绑定”可新增、修改、删除任务别名并设置默认聊天。点击“保存绑定”后对新消息生效，已入队消息保持原目标；凭证与主配置不被覆盖。控制群支持 `/help`、`/任务`、`/发 <别名> <指令>`、`/切换 <别名>`及 `/清除`，详见[桥接路由说明](../services/message-bridge/README.md#一个控制群多个聊天)。临时选择有效期30分钟，过期或重启须重新选择或明确恢复默认。

## 新电脑安装与配置

### 1. 获取代码并安装

支持 Windows 10/11 的交互式用户会话。把整个仓库放在固定的可写目录；已有 Git 时可克隆，没有 Git 时可从仓库页面下载 ZIP 后解压。以下命令在仓库根目录执行：

```powershell
# 默认安装，也可以直接双击 task-center 目录内的 install.cmd
.\task-center\install.ps1

# 可选：同时准备飞书与知识库所需的外部工具
.\task-center\install.ps1 -WithBridge -WithKnowledgeSync

# 指定已有 Python；完成安装，但不打开窗口或启动守护进程
.\task-center\install.ps1 -Python 'D:\Python\python.exe' -NoLaunch
```

安装器逐项检查退出码，失败时停止并显示原因，不会将缺依赖报告为成功。它执行以下操作：

| 项目 | 安装行为 |
|---|---|
| Python | 复用可用的 Python 3.11+、Tk、venv；缺少时通过 winget 安装 Python 3.13 到当前用户。指定 `-Python` 时该解释器必须有效。 |
| Python 依赖 | 使用 `%USERPROFILE%\.orbit\venv` 独立环境，按 `requirements.txt` 安装 psutil；已满足版本范围则跳过下载，不改项目环境。 |
| 本机配置 | 仅在缺失时创建空 `services.json`；更新 `installation.json` 的代码根目录和解释器，保留其他字段。创建 `instances`、`runtime`、`setup-examples` 目录。 |
| 示例 | 将 examples 复制到本机 `setup-examples`，替换用户目录和代码根目录；保留已有草稿。项目路径、身份和聊天仍需填写；示例不会自动登记或启动。 |
| 桌面与自启 | 创建或更新当前用户的两个快捷方式，指向独立环境的 pythonw.exe；自启是**用户登录后**执行，不是无人登录时的系统服务。 |
| 可选依赖 | `-WithBridge`准备 Node.js 22+ 和 `@larksuite/cli`；`-WithKnowledgeSync`准备 Git。已有工具满足要求就复用。 |

通常不需要管理员权限；Node.js/Git 的系统安装可能触发 Windows 提权。缺少 winget 时安装 Microsoft Store 的 App Installer，或手动安装缺失工具后重跑。网络不可用时，预装依赖再运行；安装器不会跳过失败继续创建入口。若 PowerShell 阻止下载的脚本，先核对来源，再对可信脚本执行 `Unblock-File`；若组织执行策略仍禁止脚本，需要管理员提供获准的执行方式，安装器不修改执行策略。

重复安装不会覆盖注册表、账号配置、消息队列或历史，不会重启已运行的任务中心和守护进程，也不改变知识库计划任务。安装后已有进程继续使用原解释器，下次正常启动使用新环境。已有登记实例时若代码目录变更，安装器会报错：先核对并修改实例中的绝对路径及 `installation.json` 的 root，再重跑；不要把旧电脑的绝对路径直接当作新电脑配置。

### 2. 配置需要的服务

**飞书消息桥接**

1. 使用 `-WithBridge`准备工具。在新电脑上按 Lark CLI 的交互配置流程建立所需 profile，并授权机器人收发消息所需权限和事件订阅；以 CLI 当前 `--help` 为准。凭证由 CLI 管理，不填入仓库模板。
2. 安装并登录 Codex，确认目标聊天及本地传输可用。当前 `bootstrap_codex=true`实现寻找 `%USERPROFILE%\AppData\Local\OpenAI\Codex\bin\*\codex.exe` 并启动本机 18773 端口；若安装布局不符，应提供可用传输、配置 `endpoint` 并保持 `bootstrap_codex=false`。安装 Orbit 本身不代表聊天连接已成功。
3. 从 `.orbit\setup-examples\message-bridge.json`复制到 `.orbit\instances\<实例名>.json`，填写 profile、本人 owner_id、授权群 chat_id、机器人 bot_id、目标聊天 thread_id 和独立 runtime。核实后设 `enabled=true`。若 Node.js 不在登录时的 PATH 中，配置 `cli` 数组，填 Node 可执行文件绝对路径及 `%USERPROFILE%\AppData\Roaming\npm\node_modules\@larksuite\cli\scripts\run.js` 的实际绝对路径。
4. 另复制 `message-bridge.service.json`，填写唯一 ID、配置引用及状态路径。先保持 `autostart=false`，按下方“跨项目接入”校验并登记；在界面手动启动，用本人在授权群内 @ 机器人验证发送、接收和结果回传。验证后需要登录自动运行的实例再设 `autostart=true`，用 `--replace`更新登记。

同一机器人和群应仅有一个电脑监听，不能把旧电脑的启用配置照搬后同时启动。新电脑通常使用全新运行目录；确需接管在途消息与历史时，先停止旧实例，再迁移完整 runtime 并核对绝对路径，不能运行中只复制 SQLite 单文件。

**知识库同步**

先安装 Git、配置本人 Git 身份及远端认证，将知识库克隆到新电脑并确认分支和 origin 正确。然后在本仓库根目录执行（替换实际路径与实例名）：

```powershell
$orbitPython = "$env:USERPROFILE\.orbit\venv\Scripts\python.exe"
.\services\knowledge-sync\install.ps1 -Repository 'D:\Knowledge\my-vault' -Name 'my-vault' -Profile secondary -Python $orbitPython
```

此命令会创建该知识库的本机配置、计划任务并登记到 Orbit，**会启用后续定时同步**。主力电脑选 `primary`，备用电脑选 `secondary`；具体时间和 Git 保护规则见[知识库 README](../services/knowledge-sync/README.md)。仅运行 Orbit 安装器的 `-WithKnowledgeSync`不会启用这些任务。

**训练监测**

先准备该项目代码、Python 依赖和 SSH/服务器访问配置，再填写本机的 `training-monitor.json`和 `training-monitor.service.json`草稿。项目适配器及实验路径必须属于这台电脑实际接管的实验；登记仅使其出现在界面，不启动训练或监测。启动前确认旧电脑没有为同一实验重复监测，完成后的自动撤下仍以真实完成回执和进程退出为准。

### 3. 检查安装结果

双击桌面“本地任务中心”，新安装应能显示空服务列表；按上述步骤接入后出现对应实例。按 `Win+R`输入 `shell:startup`，应看到“Orbit 本地服务”。登录后仅启动显式启用的桥接，训练监测不自动启动。

| 本机数据 | 默认位置 |
|---|---|
| 服务注册表（唯一） | `%USERPROFILE%\.orbit\services.json` |
| 安装路径与 Python | `%USERPROFILE%\.orbit\installation.json` |
| 独立环境 / 配置草稿 / 实例配置 | `%USERPROFILE%\.orbit\venv` / `setup-examples` / `instances` |
| 新桥接运行记录 | 实例配置的 runtime，模板为 `%USERPROFILE%\.orbit\runtime\<实例名>` |
| 知识库配置与记录 | `%USERPROFILE%\.knowledge-sync\<实例名>` |
| 界面与守护诊断 | 本仓库 `task-center\runtime`（忽略提交） |

旧实例沿用其已登记路径，不能仅看默认目录判断数据位置。所有本机账号、配置、队列、日志、环境均不提交 Git。全新电脑只克隆代码时不会带入旧电脑的服务与凭证。

## 跨项目接入

1. 在本机私密目录创建实例配置；参考仓库examples中的桥接、知识库和监测模板。
2. 项目特有探针、评估和恢复协议保留在项目；通用训练监测runner调用项目的configure(config)/main()适配器。
3. 准备服务登记JSON：唯一id、project、kind、name、group、绝对entry/scripts/cwd、health/folder，以及需要的config/args/match_config/terminal。
4. 在任意工作目录使用下面的绝对入口。先校验，再登记；两步都不会启动服务。更新已有ID时，两步都加`--replace`，不要用新ID重复登记同一实例。

```powershell
$orbit = "F:/Development/research/agent-skills/task-center/orbit.py"
$manifest = "C:/Users/Lenovo/.orbit/instances/<实例ID>.service.json" # 替换为实际登记文件
python $orbit register --file $manifest --check
python $orbit register --file $manifest
```

登记JSON描述入口、配置引用和状态路径；服务自己的配置JSON描述账号/聊天或仓库/实验参数，两者不是同一个文件。示例在[examples](../examples/)，占位符填写并核实后才能登记。

同一通用脚本的不同实例必须提供match_config，以“脚本路径+配置路径”识别进程。否则无法安全区分启停对象。桥接不允许同一profile+群的重复路由或共享队列目录。

多个桥接和知识库实例会先展示选择列表。训练监测与其他本地服务按分组显示。完成记录显示回执中的北京时间日期与秒；只有已核实完成原因且进程退出才移出活动入口，失败/超时/手动停止仍保留。

## 验证

在仓库根目录执行`python -m unittest discover -s task-center -p 'test_*.py'`；各服务README列出隔离测试。验证不可发送虚假完成通知、重复投递生产指令或启动远端训练。
