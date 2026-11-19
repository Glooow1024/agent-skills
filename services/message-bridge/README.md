# 通用消息桥接

`python service.py --config <private-instance.json>`。配置模板在`examples/message-bridge.json`。可选择不同机器人profile、群、本人身份、聊天及本地Codex连接地址；每个实例必须独立runtime。相同profile与群不重复登记监听实例，避免一条指令被投递到多个聊天。

SQLite queue、requests、delivery回执、acks、锁和心跳都在配置runtime。接收严格校验本人、群和@；原message_id去重、提交前持久化和模糊投递不重加的规则保留。群里的收到回执不代表指令已完成。

`notify.send(text, config, idempotency_key=None)`供其他项目复用。账号密钥不进入实例JSON，由lark-cli profile保管。`endpoint`默认本机18773；更换地址须提供实际可用的Codex传输服务。

写`runtime/stop.request`请求优雅停止。再启动前移除该请求；Orbit负责处理。独立运行时应自行处理。`listener.json`的ready与`health.json`心跳分别表示接收端、处理循环健康。

测试：`python -m unittest discover -s services/message-bridge -p 'test_*.py'`，`node services/message-bridge/test_dispatch.mjs`。测试不发送真实消息、不唤醒聊天。

NVS的feishu_bridge目录只保存现有runtime数据与说明，没有旧服务代码；已有绝对回执路径继续有效。全新实例请用自己的运行目录。
