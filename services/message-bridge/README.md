# 通用消息桥接

`python service.py --config <private-instance.json>`。配置模板在`examples/message-bridge.json`。可选择不同机器人profile、群、本人身份、聊天及本地Codex连接地址；每个实例必须独立runtime。相同profile与群不重复登记监听实例，避免一条指令被投递到多个聊天。

SQLite queue、requests、delivery回执、acks、锁和心跳都在配置runtime。接收严格校验本人、群和@；原message_id去重、提交前持久化和模糊投递不重加的规则保留。群里的收到回执不代表指令已完成。

## 一个控制群，多个聊天

仍然只接受白名单本人在授权群内 @ 机器人。支持以下格式：

| 格式（均需 @机器人） | 行为 |
|---|---|
| `/help` 或 `/帮助` | 显示支持的格式，无需唤醒聊天 |
| `/任务` | 列出任务别名、默认任务和当前临时选择 |
| `/发 单视角 查看进度` | 仅本条发送给“单视角”，不改变临时选择 |
| `/切换 单视角` | 临时选择“单视角”，30分钟有效 |
| `/清除` | 取消临时选择，恢复默认目标 |
| 普通文本 | 进入当前临时选择；未使用临时选择时进入默认任务 |

临时选择过期、服务重启或所选绑定被修改后，普通文本会提示重新选择，不会静默发送到默认聊天；可用 `/清除`明确恢复默认。未知命令、别名或无效配置均不会投递。回执、延迟提示和每段结果带任务别名，并回复原飞书消息。

在 Orbit 的“消息桥接 → 服务详情 → 管理任务绑定”中编辑。新增/更新只改草稿，点击“保存绑定”才生效；删除默认任务前须先设置其他默认任务。别名不含空格或斜杠；聊天 ID 必须由用户核实，编辑器不猜测聊天。聊天 ID 使用 Codex 聊天的实际标识，不是飞书话题 ID。对同一聊天可设置多个别名，但仍串行处理。

绑定默认保存为实例 `runtime/bindings.json`，也可在私密配置中指定 `bindings_file`绝对路径。格式见 [bindings 示例](../../examples/message-bridge.bindings.json)，每个任务可选 `endpoint`，不填则沿用实例地址。没有绑定文件时兼容原 `thread_id`，别名为“默认”。保存时保留其他配置字段，并在本机 `binding-backups`备份旧绑定；检测到其他窗口已修改文件会拒绝覆盖。服务逐条接收时读取绑定，无需为修改别名而重启。

每条业务消息入队时固定别名、聊天 ID、endpoint 和正文。之后切换或删改绑定不影响它；已经接收的消息也不会因删除绑定而被取消。不同聊天独立排队，相同聊天的后续指令等待前条回执；投递不明确仍保留防重机制。控制命令单独回复，不受业务队列阻塞。首次升级仅给未完成旧消息补充原目标（优先使用已保存 request），保留 token、状态、去重 ID、delivery、acks 和完成历史；部署前备份数据库，禁止通过重发生产指令验证迁移。

`notify.send(text, config, idempotency_key=None)`供其他项目复用。账号密钥不进入实例JSON，由lark-cli profile保管。`endpoint`默认本机18773；更换地址须提供实际可用的Codex传输服务。

写`runtime/stop.request`请求优雅停止。再启动前移除该请求；Orbit负责处理。独立运行时应自行处理。`listener.json`的ready与`health.json`心跳分别表示接收端、处理循环健康。

测试：`python -m unittest discover -s services/message-bridge -p 'test_*.py'`，`node services/message-bridge/test_dispatch.mjs`。测试不发送真实消息、不唤醒聊天。

NVS的feishu_bridge目录只保存现有runtime数据与说明，没有旧服务代码；已有绝对回执路径继续有效。全新实例请用自己的运行目录。
