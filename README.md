# Agent Skills

用于集中维护可独立安装和持续迭代的 Agent Skills。

## 仓库结构

```text
agent-skills/
├─ README.md
└─ skills/
   └─ <skill-name>/
      ├─ SKILL.md
      ├─ references/   # 按需加载的详细规则
      ├─ assets/       # 输出模板与可复用资源
      ├─ scripts/      # 可选的确定性工具
      └─ agents/       # 可选的界面与调用配置
```

每个 `skills/<skill-name>/` 都是一个独立 skill，以 `SKILL.md` 为入口；只创建该 skill 实际需要的可选目录。

## 已收录 Skills

| Skill | 用途 |
|---|---|
| [local-research-knowledge-assistant](skills/local-research-knowledge-assistant/SKILL.md) | 将论文总结与讨论整理为 Obsidian 知识资产，维护 Topic 综述、研究推荐与 Git 同步流程。 |

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
