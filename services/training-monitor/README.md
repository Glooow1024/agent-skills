# 通用训练监测运行层

本层提供配置加载、项目适配器运行、有限期守护、心跳、通知outbox去重与退避。模型专用探针、指标解释、评估规则和恢复协议留在项目中。不同模型不能共用未经核实的“完成”判断。

适配器接口：`configure(config)`接收实例配置，`main()`执行监测。通过`runner.py --config <实例JSON>`运行；`--once`用于项目适配器支持的单轮探测。runner不拼接远端训练启动命令。`guard.py --config <实例JSON>`只启动同实例runner，默认最多3次退出重启，期限到达写expired而非完成。

项目可复用`runtime.queue/flush/save/sender/wait`。原outbox格式保留；sending无回执视为不确定，不盲目重发。`wait`支持轮次之间reload.request退出。新adapter必须在任务内实现取证、异常/质量门控、通知成功后派发及最终核验。不要因加载模板自动注册或启动实验。

NVS当前两个实例保留原有项目guard的告警/恢复行为，直接启动带--config参数的监测实现。实际业务代码在项目的`training_watch.py`、`alert_watch.py`，单视角事件协议在`alert_events.py`。既有看板同步和已完成几何任务作为项目服务登记，未强行改写。

归档需项目核实训练与约定评估完成、完成通知成功、进程退出，并写独立terminal回执。超时、失败、人工停止不能归档。不要复用旧实验的runtime或terminal启动新实验。

隔离测试：`python -m unittest discover -s services/training-monitor -p 'test_*.py'`。项目适配器还须以自己的真实探针验收，模板不能替代。
