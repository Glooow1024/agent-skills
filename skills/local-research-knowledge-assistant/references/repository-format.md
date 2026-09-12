# 知识库文件约定

入库和更新时读取。已有仓库格式优先，不自动全库迁移；以下作为新库默认值，也作为未来软件读取内容的最小约定。

此文件夹作为 Obsidian vault 使用；笔记正文采用普通 Markdown、相对链接和本地图片，不要求安装插件或连接 MCP。个人 Obsidian 布局与插件配置按现有仓库习惯处理，不因归档笔记就改动。

## 组织

```text
knowledge-base/
  papers/       文献笔记
  topics/       Topic 综述与对比表
  inbox/        信息嗅探条目及汇总
  roadmaps/     用户要求整理的研究路线
  assets/       论文图片与其他实际附件
  templates/    按需保存的笔记模板
```

只建立当前需要的目录。正文为 UTF-8 Markdown，以 YAML frontmatter 保存元信息；不为相同正文另存 JSON。笔记可以不依赖任何管理软件直接编辑。

## 元信息

每条新记录使用如下字段；下列示例仅说明格式，实际 ID 必须新生成，日期使用实际创建/更新日期。

```yaml
---
schema_version: 1
id: "9c747bbd-472b-4c66-b0a4-52a016b87089"
type: paper
title: "论文标题"
created: "2026-09-10"
updated: "2026-09-10"
status: draft
tags: []
topics: []
paper_url: null
discussion_url: null
---
```

- `id` 为稳定 UUID，不随改名或移动改变。`type` 使用 `paper`、`topic`、`info`、`roadmap` 或 `digest`；`status` 使用 `draft` 或 `final`，不表示 Git 状态。
- `tags` 为术语数组；`topics` 为 Topic 记录 ID 数组。其他关联按需使用 `related` ID 数组，Topic 层级按需使用 `parent` ID。正文放可点击相对链接；不要仅凭标签生成 Topic 文档。
- 新笔记优先使用扁平属性：`paper_url`、`discussion_url`（无则省略或 null）、`input_type`（summary/conversation/mixed）、`verification`（unverified/partial/primary_checked）。核验范围及每条来源写在正文“来源与整理说明”，状态只概括实际核验范围，不保证全文正确。`final` 表示已整理成稿，不等于已核验论文。已有 `sources` 结构继续保留，不批量改格式。
- 文献按需增加 `authors`（数组）、`year`（整数）、`venue`、`doi`、`arxiv_id`、`version`。资讯可增加 `publisher`、`published`、`event_date`。未知字段省略或为 `null`，不能臆造。
- YAML 是元信息的权威来源，正文基础信息是阅读展示；更新时保持一致。保留已有未知字段，方便以后软件扩展。

## 文件与图片

新文件优先用简短名称加 ID 前缀，避免不同系统禁用字符、尾随空格和仅大小写不同的文件名。已有文件无需为统一外观改名。

资源放在 `assets/<完整记录ID>/`，笔记引用例如 `../assets/<完整记录ID>/figure-1.png`；路径统一使用 `/`。正文 Markdown 链接相对当前文件，元信息中的资源路径相对仓库根目录。禁止将机器绝对路径或临时图片 URL 当成仓库资产。

保存可查看的真实图像，保留图号、图注和来源。按内容判断重复文件，不反复复制。不默认保存 PDF，也不在笔记中依赖某台电脑的 PDF 路径。临时读原文用于核验并不意味着应纳入 Git；现有 PDF 不因本规则被删除。

## 为后续软件保留的边界

Markdown、YAML 和资产文件是内容来源；未来搜索索引、向量索引或数据库视为可重建缓存，不另设一份正文作为真相来源。软件应保留未知元信息和人工编辑，使用稳定 ID 维护关系。只有确实需要改格式时才升级版本并做显式迁移；当前不搭建应用框架。
