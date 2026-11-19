# 可复用本地服务约定

先读各服务README和task-center/AGENTS.md。代码不写用户账号、聊天ID、项目路径或实例运行目录；这些必须来自显式配置。认证只引用既有凭证管理，日志不输出密钥。

保留用户已有消息队列、幂等键、delivery和回执，不为代码搬迁重投指令。多实例采用独立runtime、锁、队列和配置匹配，禁止按相同脚本路径把其他实例一起停止。

训练项目探针、指标和完成核验留在项目adapter，通用层不能擅自启动训练、修改实验协议或猜测完成。归档仅在核实完成、通知成功和监测退出后发生。知识库同步保持既定Git保护与计划。

新增实例使用`task-center/orbit.py register`登记到`%USERPROFILE%/.orbit/services.json`（本机`C:/Users/Lenovo/.orbit/services.json`）。先--check，后登记；更新已有ID两步都加--replace。登记不启动服务，不创建分散的永久桌面入口。部署前隔离测试，再验证现有实例真实心跳；模拟成功不能声称真实端到端成功。
