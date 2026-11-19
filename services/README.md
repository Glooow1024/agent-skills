# 可复用本地服务

此目录只放程序及测试，不存实际账号、群、聊天、实验路径、运行队列或凭证。

| 服务 | 入口 | 配置方式 |
|---|---|---|
| message-bridge | `service.py --config <绝对路径>` | 机器人profile、owner_id、chat_id、bot_id、thread_id、runtime、endpoint |
| knowledge-sync | `sync.py <inspect/sync/pull/session> --config <绝对路径>` | 仓库、分支、远端、运行目录与同步策略 |
| training-monitor | `runner.py --config <绝对路径>`；可用`guard.py`守护 | 项目adapter、cwd、runtime及适配器参数 |

共同约定：每个实例有唯一ID、独立状态和完成回执。注册不会启动服务；只有明确设置autostart的消息桥接随Orbit登录启动。脚本可脱离Orbit界面运行。

生产注册表唯一位置：`%USERPROFILE%/.orbit/services.json`（本机`C:/Users/Lenovo/.orbit/services.json`）。代码目录不保存注册表或指针文件。已有私密配置和运行目录通过绝对路径引用，迁移不复制数据库或重建状态。凭证仍由原凭证管理工具保存。

新增实例先参照仓库`examples/`，填入自己的实际路径和身份，在任意目录运行`python F:/Development/research/agent-skills/task-center/orbit.py register --file <实例登记JSON> --check`，校验后去掉`--check`登记。校验及替换已有ID时均须显式加`--replace`。完整路径及登记JSON与服务配置的区别见[任务中心接入说明](../task-center/README.md#跨项目接入)。不支持通过“第一个发消息的人”自动授予身份。
