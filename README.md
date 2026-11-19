# Agent Skills

用于集中维护可独立安装和持续迭代的 Agent Skills。

## 配套工具

- [Orbit 本地任务中心](task-center/README.md)：跨项目桌面入口，统一消息桥接、知识库同步、训练监测及其他本地服务；完成任务自动归档并保留完成时间。

- [Knowledge Sync](services/knowledge-sync/README.md)：Windows 本地知识库定时 Git 同步工具，支持主力电脑与晚间/周末电脑的独立调度、编辑稳定窗口及冲突提醒。

## 仓库结构

```text
agent-skills/
├─ README.md
├─ install.cmd             # Windows 双击安装 Orbit
├─ task-center/            # 桌面入口、安装器与服务管理
├─ services/               # 消息桥接、知识库同步、训练监测
├─ examples/               # 不含身份与凭证的配置模板
└─ skills/
   └─ <skill-name>/
      ├─ SKILL.md
      ├─ references/   # 按需加载的详细规则
      ├─ assets/       # 输出模板与可复用资源
      ├─ scripts/      # 可选的确定性工具
      └─ agents/       # 可选的界面与调用配置
```

每个 `skills/<skill-name>/` 都是一个独立 skill，以 `SKILL.md` 为入口；只创建该 skill 实际需要的可选目录。

实际注册表：`%USERPROFILE%/.orbit/services.json`，本机为 `C:/Users/Lenovo/.orbit/services.json`。所有接入操作使用 `task-center/orbit.py register`，具体命令见[接入说明](task-center/README.md#跨项目接入)。

## 新电脑安装 Orbit（Windows）

1. 把仓库克隆或下载 ZIP 后解压到固定目录，例如 `D:\Tools\agent-skills`。不要在 ZIP 内直接运行，也不要安装后随意移动目录。
2. 双击根目录 **`install.cmd`**。安装器自动检查 Python 3.11+（含 Tk），缺少时通过 winget 安装 Python 3.13；创建用户目录下的独立 Python 环境并安装依赖，初始化本机配置，创建桌面入口和登录自启项，最后打开任务中心。首次下载需联网；缺少 winget 时按报错安装微软 App Installer 或手动安装 Python 后重试。
3. 新电脑的服务列表初始为空。按[完整安装和配置说明](task-center/README.md#新电脑安装与配置)分别配置消息桥接、知识库或训练监测。账号授权、Git 身份、项目路径与聊天绑定不会从代码仓库自动带过来。

需要同时准备飞书和知识库依赖时，在仓库根目录运行：

```powershell
.\task-center\install.ps1 -WithBridge -WithKnowledgeSync
```

这两个选项检查并在缺失时安装 Node.js 22+ / Lark CLI、Git，不会自动登录账号或启用同步计划。重复执行保留已有配置和运行中的服务。`-NoLaunch`执行完整安装但不启动界面与守护进程。安装范围、排错和本机文件位置见[任务中心 README](task-center/README.md)。

## 已收录 Skills

仓库还包含跨项目本地工具：`task-center/`是Orbit桌面入口（ui/core/adapters），`services/`存放可独立运行的消息桥接、知识库同步和训练监测通用层，`examples/`提供不含真实身份的配置模板。实际实例配置在本机用户目录，项目特有探针和实验协议仍留在项目中。知识库同步只有`services/knowledge-sync/`一份实现。详见[服务说明](services/README.md)与[任务中心接入说明](task-center/README.md)。

| Skill | 用途 |
|---|---|
| [local-research-knowledge-assistant](skills/local-research-knowledge-assistant/SKILL.md) | 将论文总结与讨论整理为 Obsidian 知识资产，维护 Topic 综述、研究推荐与 Git 同步流程。 |
| [training-workflow](skills/training-workflow/SKILL.md) | 管理训练协议、监控面板、周期巡检、异常恢复、启动与完成通知，以及任务完成后的自动停止。 |

## 使用方式

克隆仓库后，选择 `skills/` 下需要的目录，将整个目录安装或复制到所用 Agent 环境的 skills 目录中。保留 skill 文件夹名称及其内部相对路径。

```bash
git clone git@github.com:Glooow1024/agent-skills.git
```

## 新增 Skill

1. 在 `skills/` 下新建以小写字母、数字和连字符命名的目录。
2. 提供包含 `name` 与 `description` frontmatter 的 `SKILL.md`。
3. 只添加真实需要的 `references/`、`assets/`、`scripts/` 或 `agents/`。
4. 提交前验证入口描述、相对链接和必要脚本，并更新上方索引。
