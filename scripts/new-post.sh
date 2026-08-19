#!/usr/bin/env bash
# ============================================================================
# new-post.sh — 新文章创建助手（交互式，无需了解 Hugo front matter 语法）
#
# 用法：
#   ./scripts/new-post.sh           交互式问答创建
#   ./scripts/new-post.sh "标题"    直接给标题，其余仍交互
#   ./scripts/new-post.sh -y "标题" 全部用默认值快速创建（标签/分类留空，非草稿）
#
# 只生成 Markdown 文件；发布请运行 ./scripts/publish.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLOG_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BLOG_DIR"

ASSUME_DEFAULT=0
POS_TITLE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y) ASSUME_DEFAULT=1 ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) POS_TITLE="$1" ;;
  esac
  shift
done

echo "===== 新文章创建助手 ====="
echo "（只生成 Markdown 文件，发布请用 ./scripts/publish.sh）"
echo ""

# 1. 标题 ----------------------------------------------------------------------
TITLE="$POS_TITLE"
while [[ -z "$TITLE" ]]; do
  read -r -p "1/5 文章标题（必填）: " TITLE
done
TITLE_SAFE=$(echo "$TITLE" | sed 's/"/\\"/g')   # 转义双引号，防破坏 YAML

# 2. 文件名（slug）--------------------------------------------------------------
DEFAULT_SLUG=$(echo "$TITLE" | python3 -c "
import sys, re
s = sys.stdin.read().strip().lower()
s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
print(s or 'post')
")
if [[ "$ASSUME_DEFAULT" -eq 1 ]]; then
  SLUG="$DEFAULT_SLUG"
else
  read -r -p "2/5 文件名（英文小写连字符；中文标题请手动输入，回车用「$DEFAULT_SLUG」）: " SLUG
  SLUG="${SLUG:-$DEFAULT_SLUG}"
fi
if [[ -f "content/posts/$SLUG.md" ]]; then
  echo "✗ content/posts/$SLUG.md 已存在，换个文件名" >&2
  exit 1
fi

# 3. 标签 ----------------------------------------------------------------------
if [[ "$ASSUME_DEFAULT" -eq 1 ]]; then
  TAGS="[]"
else
  read -r -p "3/5 标签（逗号分隔，如 Python,后端；可留空）: " TAGS_INPUT
  TAGS=$(echo "$TAGS_INPUT" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
         | sed '/^$/d' | sed 's/.*/"&"/' | paste -sd, -)
  TAGS="[${TAGS:-}]"
fi

# 4. 分类 ----------------------------------------------------------------------
if [[ "$ASSUME_DEFAULT" -eq 1 ]]; then
  CATS="[]"
else
  read -r -p "4/5 分类（如 技术；可留空）: " CAT_INPUT
  CATS=$(echo "$CAT_INPUT" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
         | sed '/^$/d' | sed 's/.*/"&"/' | paste -sd, -)
  CATS="[${CATS:-}]"
fi

# 5. 草稿 ----------------------------------------------------------------------
DRAFT="false"
if [[ "$ASSUME_DEFAULT" -ne 1 ]]; then
  read -r -p "5/5 存为草稿（draft: true，发布后不上线）？[y/N] " DRAFT_INPUT
  [[ "$DRAFT_INPUT" =~ ^[Yy]$ ]] && DRAFT="true"
fi

# 生成文件 ----------------------------------------------------------------------
DATE=$(date +%F)
FILE="content/posts/$SLUG.md"
cat > "$FILE" <<EOF
---
title: "$TITLE_SAFE"
date: $DATE
tags: $TAGS
categories: $CATS
draft: $DRAFT
---

在这里开始写正文（Markdown 语法）。
EOF

echo ""
echo "✅ 已创建: $FILE"
echo "  · 标题: $TITLE"
echo "  · 标签: $TAGS  分类: $CATS  草稿: $DRAFT"
echo ""
echo "下一步："
echo "  · 编辑正文: 用编辑器打开 $FILE"
echo "  · 本地预览: ./scripts/publish.sh --preview"
echo "  · 写好后发布: ./scripts/publish.sh"
if command -v code >/dev/null 2>&1; then
  read -r -p "  现在用 VS Code 打开？[y/N] " OPEN || OPEN=""
  [[ "$OPEN" =~ ^[Yy]$ ]] && code "$FILE" || true
fi
