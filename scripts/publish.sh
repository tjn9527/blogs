#!/usr/bin/env bash
# ============================================================================
# publish.sh — 博客文章检查与一键发布
#
# 流程：环境检查 → git 检查 → 文章 front matter 检查 → 本地构建验证
#       → 提交推送 → 等待 Actions 部署 → 验证线上地址
#
# 用法：
#   ./scripts/publish.sh                完整发布（交互确认）
#   ./scripts/publish.sh --dry-run      只检查，不提交不推送
#   ./scripts/publish.sh --preview      本地实时预览（hugo server -D）
#   ./scripts/publish.sh -m "msg"       指定 commit 消息
#   ./scripts/publish.sh --yes          跳过交互确认（脚本/CI 场景）
#
# 依赖：hugo（~/.local/bin 或 PATH）、git、gh（已登录）、curl
# ============================================================================
set -euo pipefail

# ---- 定位仓库根目录（脚本放在 scripts/ 下） -------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLOG_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BLOG_DIR"

# ---- 参数解析 -----------------------------------------------------------------
DRY_RUN=0
PREVIEW=0
ASSUME_YES=0
COMMIT_MSG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=1 ;;
    --preview)  PREVIEW=1 ;;
    --yes)      ASSUME_YES=1 ;;
    -m|--message) COMMIT_MSG="${2:-}"; shift ;;
    -h|--help)
      sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "✗ 未知参数: $1（-h 查看帮助）" >&2; exit 1 ;;
  esac
  shift
done

# ---- 工具函数 -----------------------------------------------------------------
PASS=0; WARN=0; FAIL=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; PASS=$((PASS+1)); }
warn() { printf '  \033[33m⚠\033[0m %s\n' "$1"; WARN=$((WARN+1)); }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
abort() { echo "✗ $1" >&2; exit 1; }

echo "===== 博客发布工具 ===== 目录: $BLOG_DIR"

# ---- 1. 环境检查 -----------------------------------------------------------------
echo ""
echo "[1/6] 环境检查"
export PATH="$HOME/.local/bin:$PATH"   # 非登录 shell 的 hugo 路径
if command -v hugo >/dev/null 2>&1; then
  ok "hugo: $(hugo version | grep -oP 'v\K[0-9.]+' | head -1)"
else
  fail "hugo 未安装（需要 ~/.local/bin/hugo 或加入 PATH）"
fi
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  ok "gh 已登录: $(gh api user -q .login 2>/dev/null)"
else
  fail "gh 未登录或未安装（发布推送后需要它验证部署）"
fi
command -v curl >/dev/null 2>&1 || warn "curl 未安装，跳过线上验证"

# ---- 2. Git 检查 -----------------------------------------------------------------
echo ""
echo "[2/6] Git 检查"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  abort "当前目录不在 git 仓库内"
fi
BRANCH="$(git branch --show-current)"
[[ "$BRANCH" == "main" ]] && ok "分支: $BRANCH" || warn "分支: $BRANCH（部署触发分支是 main）"

LOCAL_EMAIL="$(git config user.email || true)"
GH_EMAIL="$(gh api user -q .email 2>/dev/null || true)"
if [[ -z "$GH_EMAIL" ]]; then
  warn "gh 无法读取 GitHub 邮箱（可能未公开），请自行确认 git 邮箱正确"
elif [[ "$LOCAL_EMAIL" == "$GH_EMAIL" ]]; then
  ok "提交邮箱: $LOCAL_EMAIL"
else
  warn "提交邮箱 $LOCAL_EMAIL ≠ GitHub 邮箱 $GH_EMAIL（提交不会计入贡献图，建议: git config --global user.email \"$GH_EMAIL\"）"
fi

UNTRACKED=$(git status --porcelain | wc -l)
if [[ "$UNTRACKED" -eq 0 ]]; then
  echo "  · 工作区干净，无待发布内容"
else
  echo "  · 待发布变更 $UNTRACKED 项："
  git status --porcelain | sed 's/^/      /'
fi

# ---- 3. 文章 front matter 检查 ---------------------------------------------------------
echo ""
echo "[3/6] 文章元信息检查"
BAD=0
while IFS= read -r f; do
  rel="${f#./}"
  # 必须有以 --- 开头的 front matter
  if ! head -1 "$f" | grep -q '^---'; then
    fail "$rel: 缺少 front matter（文件第一行应为 ---）"; BAD=1; continue
  fi
  # 检查必填字段 title / date
  fm=$(sed -n '1,/^---$/p' "$f" | sed '1d;$d')
  echo "$fm" | grep -qE '^title:' || { fail "$rel: 缺少 title 字段"; BAD=1; }
  echo "$fm" | grep -qE '^date:'  || { fail "$rel: 缺少 date 字段";  BAD=1; }
  # 提示草稿
  if echo "$fm" | grep -qE '^draft:\s*true'; then
    warn "$rel: 是草稿（draft: true），发布后不会显示"
  fi
done < <(find content/posts -name '*.md' -type f)
[[ "$BAD" -eq 0 ]] && ok "全部 $(find content/posts -name '*.md' | wc -l) 篇文章元信息完整"

# ---- 4. 本地构建验证 --------------------------------------------------------------------
echo ""
echo "[4/6] 本地构建验证"
if ! hugo --minify --gc >/tmp/publish-hugo-build.log 2>&1; then
  fail "hugo 构建失败，日志如下（最后 15 行）："
  tail -15 /tmp/publish-hugo-build.log | sed 's/^/      /'
  exit 1
fi
ok "hugo --minify --gc 构建成功 ($(find public -name '*.html' | wc -l) 个 HTML)"

BASEURL=$(grep -oP "(?<=baseURL = ')[^']+" hugo.toml || true)
[[ -n "$BASEURL" ]] && ok "站点地址: $BASEURL"

# ---- 预览模式：本地起服务并结束 ------------------------------------------------------------
if [[ "$PREVIEW" -eq 1 ]]; then
  echo ""
  echo "启动本地预览（含草稿），浏览器打开 http://localhost:1313 ，Ctrl+C 退出"
  exec hugo server -D
fi

# ---- 汇总 --------------------------------------------------------------------------------
echo ""
echo "===== 检查汇总: $PASS 通过, $WARN 警告, $FAIL 失败 ====="
[[ "$FAIL" -gt 0 ]] && exit 1
[[ "$DRY_RUN" -eq 1 ]] && { echo "（--dry-run 模式，未做任何提交）"; exit 0; }
if [[ "$UNTRACKED" -eq 0 ]]; then
  echo "工作区无变更，无需发布。"
  exit 0
fi

# ---- 5. 提交与推送 ------------------------------------------------------------------------
echo ""
echo "[5/6] 提交并推送"
if [[ "$ASSUME_YES" -ne 1 ]]; then
  echo "即将提交以下变更："
  git add -A --dry-run | sed 's/^/    /'
  read -r -p "确认提交并推送？[y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || abort "已取消"
fi

git add -A
if [[ -z "$COMMIT_MSG" ]]; then
  # 自动生成 commit 消息：列出本次涉及的文章标题
  files=$(git diff --cached --name-only | grep '^content/' | sed 's#content/posts/##; s#\.md$##' || true)
  if [[ -n "$files" ]]; then
    COMMIT_MSG="post: $(echo "$files" | tr '\n' ',' | sed 's/,$//')"
  else
    COMMIT_MSG="site: 更新站点配置/资源"
  fi
fi
git commit -m "$COMMIT_MSG" >/dev/null
echo "  · 已提交: $COMMIT_MSG"
git push
echo "  · 已推送，等待 GitHub Actions 构建部署..."

# ---- 6. 等待部署并验证线上 --------------------------------------------------------------------
echo ""
echo "[6/6] 等待部署"
RUN_ID=$(gh run list --workflow hugo.yml --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)
if [[ -n "$RUN_ID" ]]; then
  gh run watch "$RUN_ID" --exit-status >/dev/null 2>&1 \
    && ok "Actions 部署成功" \
    || { fail "Actions 运行失败，查看: gh run view $RUN_ID"; exit 1; }
else
  warn "未能读取运行 ID，请手动查看: gh run list"
fi

if [[ -n "$BASEURL" ]]; then
  CODE=$(curl -sL -o /dev/null -w '%{http_code}' "$BASEURL" || true)
  [[ "$CODE" == "200" ]] && ok "线上验证: $BASEURL → HTTP 200" \
                       || fail "线上验证失败: HTTP $CODE（可能仍在部署，稍后访问）"
fi

echo ""
echo "✅ 发布完成: $BASEURL"
