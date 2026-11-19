# Orbit 本地任务中心

跨项目桌面控制台，使用中文。修改前检查Git状态，保留他人改动。不自动提交或推送。

先读README。唯一入口orbit.py；实现分别在ui/core/adapters，禁止保留同功能转发层。可复用业务逻辑放同级services，不能重新塞回项目或界面。实际实例配置在用户.orbit及已有私密目录，注册表唯一位置为`%USERPROFILE%/.orbit/services.json`（本机`C:/Users/Lenovo/.orbit/services.json`），不在task-center目录内；凭证、消息、日志、状态和备份不入Git。

只管理显式登记脚本的绝对路径。同一脚本多实例须match_config区分，不能按文件名或进程名启停。新实例通过`python F:/Development/research/agent-skills/task-center/orbit.py register --file <登记JSON绝对路径> --check`校验，去掉`--check`后登记。已有ID的校验与更新均显式加`--replace`。登记不启动训练。登录自启仅显式设置的message-bridge实例；停止本地监测不停止远端训练。

常规刷新更新现有控件，不周期重建页面；后台每轮只枚举一次Python进程。内容溢出时才显示滚动条。修改后验证首页换行、完成时间、DPI和实例选择。

项目适配器保留训练/评估协议。新实验有独立id、project、entry/scripts/cwd、health/folder、terminal。只在核实完成且通知成功、对应进程退出后归档；失败、超时、手动停止不隐藏，不复用旧实验回执。

迁移保留队列、去重/提交回执、状态、历史和调度；先备份后切换。不得为验收重复唤醒真实聊天或发送虚假完成通知。Knowledge Sync保持Git检查与原计划；不因UI重构触发提交推送。
