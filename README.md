# Andy's Tech Blog

个人技术博客，基于 **Hugo + PaperMod** 构建，托管于 **GitHub Pages**，
由 **GitHub Actions** 自动构建部署。

- 线上地址：https://tjn9527.github.io/blogs/
- 源码仓库：https://github.com/tjn9527/blogs
- 本机位置：`/mnt/c/Users/tjn/Documents/notes/blogs`（WSL）

```
本地写 Markdown ──./scripts/publish.sh──▶ GitHub ──Actions 构建──▶ GitHub Pages
(content/posts/*.md)     (git push)   (tjn9527/blogs)   (hugo --minify)   (线上站点)
```

---

## 技术栈

| 组件 | 说明 |
|---|---|
| Hugo v0.165.0 (extended) | 静态站点生成器，单二进制，构建 <1s |
| PaperMod 主题 | git submodule 引入，`themes/PaperMod` |
| GitHub Pages | 免费静态托管，域名 `tjn9527.github.io/blogs/` |
| GitHub Actions | 每次 push 自动构建部署（`.github/workflows/hugo.yml`） |
| scripts/publish.sh | 一键发布脚本：检查 → 构建 → 推送 → 部署 → 验证 |

## 目录结构

```
blogs/
├── content/
│   ├── posts/            # ✅ 文章目录，Markdown 文件即文章
│   │   └── _index.md     # 「文章」列表页标题（/posts/）
│   ├── categories/_index.md  # 「分类」页标题/描述（/categories/）
│   ├── tags/_index.md    # 「标签」页标题/描述（/tags/）
│   ├── about.md          # 关于页（特殊页面，searchHidden 不入搜索索引）
│   ├── archives.md       # 归档页（特殊页面）
│   └── search.md         # 搜索页（特殊页面）
├── assets/images/        # 图片资源，文章用 /images/xxx.png 引用
├── assets/css/extended/  # 站点自定义 CSS（PaperMod 自动加载该目录）
├── i18n/zh-cn.yaml       # 站点中文文案（覆盖主题英文，locale=zh-cn）
├── themes/PaperMod/      # 主题（submodule）
├── layouts/              # 项目级覆盖（图片钩子、文章页「分类」区块）
├── .github/workflows/hugo.yml   # 自动部署流水线
├── scripts/publish.sh    # 一键发布脚本
├── scripts/sync-images.py # 图片引用整理（发布前自动运行）
├── PUBLISHING.md         # 📖 发布与管理完整规范
└── hugo.toml             # 站点配置（标题/菜单/社交链接/搜索/输出格式）
```

---

## 一、本地搭建（新机器从零开始）

### 1. 安装 Hugo extended

Hugo 必须在 `~/.local/bin`（或加入 PATH）。注意：**必须用 extended 版**，
PaperMod 主题依赖 SCSS 支持。WSL 的 apt 里是旧版，推荐直接下载官方二进制：

```bash
mkdir -p ~/.local/bin
cd /tmp
HUGO_VER=0.165.0   # 与 .github/workflows/hugo.yml 里的 HUGO_VERSION 保持一致
wget "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_linux-amd64.tar.gz"
tar -xzf hugo_extended_${HUGO_VER}_linux-amd64.tar.gz hugo
mv hugo ~/.local/bin/ && chmod +x ~/.local/bin/hugo
export PATH="$HOME/.local/bin:$PATH"   # 非登录 shell 需手动加
hugo version
```

### 2. 克隆仓库（含主题 submodule）

```bash
git clone https://github.com/tjn9527/blogs.git
cd blogs
git submodule update --init --recursive
```

### 3. 本地运行（预览）

```bash
hugo server -D
# 浏览器打开 http://localhost:1313 ，Ctrl+C 退出
# -D：预览时也显示 draft: true 的草稿
```

---

## 二、部署配置（GitHub 端，首次需确认）

以下配置已在仓库内完成，克隆后可检查：

1. **仓库必须为 public**：GitHub 免费版不允许 private 仓库使用 Pages，
   且变 private 会触发 GitHub 自动删除 Pages 配置（站点直接 404）。
2. **Pages 构建源 = GitHub Actions**：
   Settings → Pages → Source 选 `GitHub Actions`（不是 Deploy from a branch）。
3. **workflow 触发分支**：`.github/workflows/hugo.yml` 中
   `on.push.branches` 必须显式为 `[main]`（官方模板的 `$default-branch`
   占位符是字面量，push 不会触发）。

push 到 main 后，Actions 自动执行：装 Hugo → 拉 submodule → `hugo --minify`
构建 → 部署到 Pages。可在仓库 Actions 页查看运行日志。

---

## 三、写文章与发布

### 1. 新建文章

```bash
hugo new posts/文章名.md      # 文件名用英文 kebab-case，如 python-fastapi-notes.md
```

文件内容模板（front matter 在 `---` 之间）：

```yaml
---
title: "文章标题"            # 必填
date: 2026-08-16            # 必填，YYYY-MM-DD
tags: ["Python", "后端"]     # 可选
categories: ["技术"]         # 可选
draft: false                # true=草稿不发布；false=发布
description: "可选摘要"
---
正文 Markdown ...
```

### 2. 本地预览

```bash
hugo server -D
```

### 3. 发布（推荐）

```bash
./scripts/publish.sh          # 一键发布：检查→构建→推送→等部署→验证线上
```

脚本自动完成 6 步：环境检查（hugo/gh）→ git 检查（分支/邮箱/变更清单）→
文章元信息检查（缺 title/date 会拦截）→ 本地构建验证 → 提交推送 →
等待 Actions 并验证线上 HTTP 200。任何一步失败即中止（非零退出码）。

其他参数：

| 命令 | 作用 |
|---|---|
| `./scripts/publish.sh --dry-run` | 只体检不发布 |
| `./scripts/publish.sh --preview` | 本地实时预览（含草稿） |
| `./scripts/publish.sh -m "消息"` | 指定 commit 消息 |
| `./scripts/publish.sh --yes` | 跳过交互确认（CI 场景） |

### 4. 手动发布（可选，不用脚本时）

```bash
git add -A
git commit -m "post: 文章标题"
git push
# 等 1~3 分钟 Actions 部署完成
```

---

## 四、更新与维护

- **修改文章**：编辑对应 .md → `./scripts/publish.sh`
- **删除文章**：`git rm content/posts/xxx.md` → 发布
- **升级主题**：`git submodule update --remote themes/PaperMod` → 发布
- **改站点配置**：编辑 `hugo.toml`（标题/菜单/社交链接/搜索参数）→ 发布
- **改分类/标签**：文章 front matter 写 `categories: ["技术"]` / `tags: [...]` 即自动生成
  对应页面（导航「分类」→ `/categories/`，「标签」→ `/tags/`），文章页底部会显示可点击的
  分类与标签。新增分类不用改任何配置；页面标题/描述改 `content/categories/_index.md`。
- **搜索**：搜索页 `/search/` 依赖构建产物 `index.json`，由 `hugo.toml` 的
  `[outputs] home = ['HTML','RSS','JSON']` 开启（缺了它搜索框会一直是灰的）。
  相关性参数在 `[params.fuseOpts]`（threshold 越小越严格，当前 0.25）。
- **文章目录（侧栏）**：宽屏（视口 ≥1320px）时文章目录固定在正文右侧留白区，不随正文滚动；
  目录过长时侧栏内部滚动，标题行常显。窄屏保持主题默认（正文顶部可折叠目录）。
  - 样式：`assets/css/extended/toc-sidebar.css`（PaperMod 自动加载该目录，无需改主题）
  - 宽屏自动展开：`layouts/_partials/extend_footer.html` 里的一小段脚本（窄屏不展开；
    用户手动点过目录标题后不再干预）
  - 改断点/宽度：改 CSS 里 `@media (min-width: 1320px)` 与 `width: 220px` 两处
    （同时把脚本里的 `(min-width: 1320px)` 改成同一个值，否则展开时机与布局不一致）
  - 想要左侧：把 CSS 里 `left: calc(...)` 换成 `right: calc(50% + var(--main-width) / 2 + var(--gap))`
  - 想彻底关掉：删掉 `assets/css/extended/toc-sidebar.css`
- **界面文案**：中文文案在 `i18n/zh-cn.yaml`（主题的 `zh.yaml` 匹配不上 `zh-cn` 会回落英文）
- **加图片**：图片放 `assets/images/`，文中引用 `/images/xxx.png`
  · 为什么不放 static/：站点在 `/blogs/` 子路径下，只有 assets/ 里的资源会被项目级
    render-image 钩子（`layouts/_markup/render-image.html`）解析成带 `/blogs/` 前缀的 URL
  · 粘贴进来的图不用手动收拾：`python3 scripts/sync-images.py` 会把图片搬到
    assets/images/ 并把引用改写成 `/images/xxx.png`（`--check` 只看不改），
    `./scripts/publish.sh` 第 4 步也会自动跑一遍
- **草稿**：`draft: true` 不上线，`hugo server -D` 可预览

## 常见问题

| 问题 | 处理 |
|---|---|
| push 后站点没更新 | 仓库 Actions 页看日志；确认分支是 main、repo 是 public |
| 线上 404 | 确认 Pages 源是 GitHub Actions；repo 是否变过 private |
| 搜索没反应 / 搜不到 | `curl -I https://tjn9527.github.io/blogs/index.json` 应为 200；404 说明 `hugo.toml` 少了 `[outputs] home` 里的 `JSON` |
| 分类/标签页标题是英文 | 补 `content/categories/_index.md`、`content/tags/_index.md` 的 `title`；其他界面英文改 `i18n/zh-cn.yaml` |
| 提交不进贡献图 | git 提交邮箱需与 GitHub 账号邮箱一致 |
| 构建报 Hugo 版本错 | 本地与 workflow 的 HUGO_VERSION 保持一致（当前 0.165.0） |

更多细节见 **[PUBLISHING.md](./PUBLISHING.md)**（文章规范、定时发布、
故障排查全表）。

---

## License

内容与代码归作者所有，转载注明出处。
