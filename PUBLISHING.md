# 博客文章发布与管理指南

本博客基于 Hugo + PaperMod 构建，托管在 GitHub Pages，由 GitHub Actions 自动部署。
本文档说明如何发布、修改、删除和管理文章。

---

## 1. 发布架构（30 秒理解）

```
本地写 Markdown ──git push──▶ GitHub 仓库 ──Actions 构建──▶ GitHub Pages
(content/posts/*.md)      (tjn9527/blogs)      (hugo --minify)   (https://tjn9527.github.io/blogs/)
```

- 文章 = 一个 Markdown 文件，带 YAML front matter（元信息）
- 发布 = 把文件提交并推送到 GitHub，剩下交给 Actions 自动完成
- 没有数据库、没有后台，站点就是构建产物

---

## 2. 快速开始

推荐直接用自动化脚本（见第 3 节），首次使用：

```bash
cd blogs
./scripts/publish.sh --dry-run   # 先体检：环境、git 状态、文章元信息、构建
./scripts/publish.sh             # 正式发布：检查 → 确认 → 提交推送 → 等部署 → 验证
```

手动流程（不想用脚本时，见第 4 节）。

---

## 3. 自动化脚本：scripts/publish.sh

脚本做的事（可理解为"发布前的体检 + 一键发布"）：

1. 环境检查：hugo 是否可用、gh 是否已登录
2. Git 检查：是否在仓库内、当前分支、提交邮箱是否为 GitHub 邮箱
3. 文章检查：遍历 content/posts/**/*.md，检查 front matter 是否完整
   （必须有 title、date；draft 状态会被明确列出；**待发布文章的 date 若在当前时间之后会报错**——
   Hugo 默认不构建未来文章，这种文章会被静默丢弃、线上看不到。见第 6 节「日期」。
     about/archives/search 等特殊页面不属于文章，不参与检查；
     `_index.md` 是章节/列表索引文件，同样跳过）
4. 图片整理：跑 scripts/sync-images.py 把图片搬进 assets/images/ 并统一引用写法
5. 构建验证：本地 hugo --minify --gc 全量构建，失败即中止
6. 发布：git add → 显示变更摘要 → 确认 → commit → push
7. 部署验证：等待 Actions 完成，curl 检查线上地址返回 200

用法：

| 命令 | 作用 |
|---|---|
| `./scripts/publish.sh` | 完整发布流程（有交互确认） |
| `./scripts/publish.sh --dry-run` | 只检查不发布，安全 |
| `./scripts/publish.sh --preview` | 本地实时预览（hugo server -D，含草稿） |
| `./scripts/publish.sh -m "msg"` | 指定 commit 消息 |
| `./scripts/publish.sh --yes` | 跳过交互确认（脚本化/CI 场景） |

---

## 4. 手动发布流程

### 4.1 写新文章

```bash
cd blogs

# 方式一：hugo 生成带模板的文章文件
~/.local/bin/hugo new posts/my-new-post.md

# 方式二：直接手写文件（推荐，完全可控）
# 新建 content/posts/xxx.md，内容见第 5 节模板
```

### 4.2 本地预览

```bash
~/.local/bin/hugo server -D
# 浏览器打开 http://localhost:1313 实时预览，Ctrl+C 退出
# -D 参数：预览时也显示 draft: true 的草稿文章
```

### 4.3 发布（提交并推送）

```bash
git add -A
git commit -m "add: 新文章 <标题>"
git push
# 等待 1~3 分钟，Actions 自动构建部署，站点更新
```

### 4.4 修改文章

编辑对应 .md 文件 → 重复 4.3。站点 1~3 分钟后自动更新。

### 4.5 删除文章

```bash
git rm content/posts/xxx.md
git commit -m "remove: 文章 <标题>"
git push
```

---

## 5. 文章规范（front matter）

每个文章文件开头必须有 YAML front matter（`---` 包裹）：

```yaml
---
title: "文章标题"
date: 2026-08-16
tags: ["Python", "后端"]
categories: ["技术"]
draft: false
description: "可选：文章摘要，用于列表页和 SEO"
---

正文内容，Markdown 语法。
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 文章标题，显示在页面和列表 |
| `date` | ✅ | 发布日期，格式 YYYY-MM-DD（按 `hugo.toml` 的 `timeZone` 解析） |
| `tags` | ❌ | 标签，逗号分隔数组，自动生成标签页 |
| `categories` | ❌ | 分类，数组，自动生成分类页 |
| `draft` | ❌ | `true` = 草稿（不发布），`false` = 正式发布 |
| `description` | ❌ | 摘要，出现在列表和搜索结果 |

命名规范：文件名即 URL，建议 `kebab-case`（小写 + 连字符），如 `python-fastapi-notes.md`。

---

## 6. 管理技巧

- **草稿**：`draft: true` 的文章 push 后不会出现在站点，本地用
  `hugo server -D` 预览；定稿后改成 `false` 再 push。
- **修改已发布文章**：直接改文件 push，Actions 会重新构建整站。
- **`date` 只写日期 = 当天 00:00（站点时区）**：`hugo.toml` 里设了
  `timeZone = 'Asia/Shanghai'`，`date: 2026-10-16` 就是北京时间当天 0 点，当天写当天发能立刻上线。
  不要删这一行配置：Hugo 默认按 **UTC** 解析裸日期，北京时间当天 8 点之前，所有"当天日期"的文章
  都算未来时间而被静默丢弃（构建成功、Actions 成功、首页 200，但那篇文章 404）。
  `publish.sh` 第 3 步会拦这种情况：待发布的文章日期在未来会直接报错。
- **定时发布（局限性说明）**：把 `date` 设为未来时间，Hugo 默认不会渲染
  未来文章（`hugo` 不带 `--buildFuture` 时）。注意：Actions 只在 push 时构建，
  到点不会自动重新构建，所以真正定时发布需要额外加一个 cron workflow
  定期触发构建。简单场景可直接到点手动 `gh workflow run hugo.yml`。
- **标签/分类**：front matter 里加 `tags`/`categories` 即自动生成对应页面，不需改配置。
  - 分类页在 `/categories/`（导航「分类」），标签页在 `/tags/`（导航「标签」）；
    列表页按分类名（中文按拼音/Unicode 序）列出条目和文章数。
  - 文章页底部会显示「分类」和标签，点一下即可跳到该分类/标签的文章列表
    （分类由 `layouts/_partials/extend_post_content.html` 渲染，PaperMod 默认只显示标签）。
  - **新增分类无需任何操作**：front matter 写一个新词即自动多出一个分类页。
  - 分类/标签页的标题、描述在 `content/categories/_index.md`、`content/tags/_index.md` 里改。
- **站点文案（中文）**：主题只有 `zh.yaml`，本站 locale 是 `zh-cn`，两者不匹配会回落英文
  （阅读时长 "7 min"、目录 "Table of Contents" 等）。要调整文案改 `i18n/zh-cn.yaml`。
- **图片**：放 `assets/images/`，文章里用 `/images/xxx.png` 引用；
  图片也会随 push 部署。（放 static/ 会因站点子路径 `/blogs/` 而 404）
- **用 Obsidian 编辑博客**：把 `notes/blogs` 作为独立仓库（vault）打开，
  附件目录已预置为 `assets/images/`（`.obsidian/app.json`），粘贴的图片直接落在那里。
  链接写法不用管：Obsidian 的 `![[xxx.png]]` 嵌入语法 Hugo 不认，
  但 `./scripts/publish.sh` 的第 4 步会先把所有引用整理成 `/images/xxx.png`
  （也可手动跑 `python3 scripts/sync-images.py`，`--check` 只检查）。
  发布前已在 `Career/attachments/` 里的图会被搬/拷进 `assets/images/`，
  若该图同时被别的笔记引用则只复制、不删除原件。
- **搜索**：搜索页 `/search/`（导航「搜索」），索引是构建时生成的 `index.json`，
  由 `hugo.toml` 里这两行开启——**删掉搜索立刻失效**：

  ```toml
  [outputs]
    home = ['HTML', 'RSS', 'JSON']
  ```

  索引只收文章（`content/posts/`），`about.md` 用 `searchHidden: true` 排除在外。
  搜索参数（Fuse.js）在 `[params.fuseOpts]`：threshold 越小越严格，默认 0.4 对中文偏松。

---

## 7. 故障排查

| 症状 | 原因与处理 |
|---|---|
| push 后站点 3 分钟没更新 | 打开 GitHub 仓库 → Actions 页看运行日志；常见：front matter 缺字段、Markdown 语法错误、主题 submodule 未更新 |
| 构建报错 Hugo 版本相关 | 检查 .github/workflows/hugo.yml 里 HUGO_VERSION 与本地一致 |
| 本地预览正常但线上 404 | 检查 hugo.toml 的 baseURL 是否正确（项目站点需带 /blogs/ 路径） |
| 提交没计入 GitHub 贡献图 | git 提交邮箱与 GitHub 账号邮箱不一致，`git config --global user.email` 改成 GitHub 邮箱 |
| 文章没显示但文件在 | 检查 `draft: true` 或 `date` 是未来日期（`hugo list future` 可列出全部未来文章；`date` 只写 YYYY-MM-DD 时按 `hugo.toml` 的 `timeZone` 解析，缺 `timeZone` 会按 UTC 算）。publish.sh 第 3 步会直接报错提示 |
| 搜索框点不动 / 搜不到东西 | 索引缺失：`curl -I https://tjn9527.github.io/blogs/index.json` 应返回 200。404 说明 `hugo.toml` 的 `[outputs] home` 没有 `JSON`（见第 6 节「搜索」）。控制台里 `fetch('../index.json')` 报 404 是同一个原因 |
| 搜索能出结果但中文不相关 | 调小 `[params.fuseOpts] threshold`（0.25 比默认 0.4 严格），改完重新构建 |
| 分类页标题显示 Categories / 文案是英文 | 建 `content/categories/_index.md`（标题写中文）；其余界面文案在 `i18n/zh-cn.yaml`（主题的 `zh.yaml` 对 `zh-cn` 不生效） |
| 文章目录没有固定在侧边 | 只在视口 ≥1320px 生效（窄屏是主题原样：正文顶部可折叠目录）。宽屏下仍不固定，先确认 `assets/css/extended/toc-sidebar.css` 存在，再比对页面引用的 `stylesheet.<hash>.css` 与本地 `hugo` 构建产物是否同一个 hash（不一致说明服务端/本地是旧构建） |

---

## 8. 自动化部署做了什么（.github/workflows/hugo.yml）

每次 push 到 main 分支触发：

1. 安装 Hugo extended（与本地同版本）
2. 检出代码（含主题 submodule）
3. 安装 Node 依赖（如需要）
4. `hugo --minify --baseURL <pages地址>` 构建
5. 上传构建产物 → 部署到 GitHub Pages

出问题优先看 Actions 日志，其次按第 7 节排查。
