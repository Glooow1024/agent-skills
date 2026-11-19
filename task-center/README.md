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

`install.ps1`创建“本地任务中心”桌面入口和“Orbit 本地服务”登录Startup项；`-NoLaunch`仅更新入口。登录守护仅对kind=message-bridge且autostart=true的实例生效。bootstrap_codex=true时准备默认本机18773传输；使用其他endpoint应自行提供对应传输。

手动停止某桥接只暂停该实例，本次登录期间不自动拉起；下次登录恢复。其他监测不会因登记自动启动。知识库仍由既有Windows计划任务调度。

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
