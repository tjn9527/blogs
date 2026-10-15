#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-images.py — 博客图片引用整理

把文章里"不规范的图片引用"整理成 Hugo 能正确渲染的形式：
  1. 找到引用指向的图片文件（可能在 Obsidian 库的 attachments/、仓库里、文章旁边等）
  2. 把图片搬到 assets/images/（移动或复制，见下面的安全性规则）
  3. 把 Markdown 引用改写成 ![](/images/<文件名>.png)
       - Obsidian 嵌入语法 ![[xxx.png]] → Hugo 完全不认，必须改写
       - 编辑器粘贴生成的相对路径（../assets/images/xxx.png）→ 在 /blogs/ 子路径下会 404
       - 指向 static/ 的 /images/xxx.png → 也会 404（必须放 assets/）

安全性规则
  - 源文件在仓库外（例如 Obsidian 库 attachments/）且被其它笔记引用 → 复制，不删除原件
  - 源文件在仓库外且没有别的引用 → 移动
  - 源文件在仓库内 → 移动（保持仓库整洁）
  - 找不到源文件 → 只警告，不改动
  - 目标重名且内容不同 → 自动加 -2、-3 后缀
  - 已经规范的 /images/xxx.png 且文件确实在 assets/images/ → 跳过

用法
  python3 scripts/sync-images.py            整理（默认，会真实改动文件）
  python3 scripts/sync-images.py --check    只检查不改动；有待整理项时退出码 1
  python3 scripts/sync-images.py --verbose  打印解析细节
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote

# ---------------------------------------------------------------- 路径与常量

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
CONTENT = REPO / "content"
ASSETS_IMAGES = REPO / "assets" / "images"

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}

# 仓库内不参与搜索的目录
SKIP_DIRS = {".git", "public", "resources", "themes", "node_modules", ".hugo_build.lock"}

# 粘贴产生的无意义文件名前缀，整理时裁掉
NOISE_PREFIX = re.compile(r"^(?:pasted[-_ ]?image|pasted|screen[-_ ]?shot|screenshot|image|截图|image[-_ ]?copy)[-_ ]*", re.I)

# 图片引用三种写法
RE_WIKILINK = re.compile(r"!\[\[([^\]\|]+?)(?:\|([^\]]*))?\]\]")
RE_MDLINK = re.compile(r"!\[([^\]]*)\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)")
RE_IMGTAG = re.compile(r"(<img\b[^>]*?\bsrc=)([\"'])([^\"']+)\2", re.I)

# 已经"干净"的文件名（不需要重命名）：字母数字、中文、点、下划线、连字符
RE_SAFE_NAME = re.compile(r"^[A-Za-z0-9\u4e00-\u9fff._-]+$")

VERBOSE = False


def log(msg: str) -> None:
    print(msg)


def vlog(msg: str) -> None:
    if VERBOSE:
        print(f"    · {msg}")


# ---------------------------------------------------------------- 小工具


def is_external(dest: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", dest)) or dest.startswith("//")


def sanitize(stem: str) -> str:
    """文件名主体 → 安全 slug（保留中文）"""
    stem = NOISE_PREFIX.sub("", stem.strip())
    stem = re.sub(r"[^\w\u4e00-\u9fff]+", "-", stem, flags=re.UNICODE)
    stem = re.sub(r"-{2,}", "-", stem).strip("-").lower()
    return stem or "image"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_vault_attachments() -> Path | None:
    """定位 Obsidian 库的 attachments/（可用 BLOG_VAULT_ATTACHMENTS 覆盖）"""
    env = os.environ.get("BLOG_VAULT_ATTACHMENTS")
    candidates = [Path(env)] if env else []
    candidates += [REPO.parent / "Career" / "attachments", REPO.parent.parent / "Career" / "attachments"]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    return None


def walk_files(root: Path, exts: set[str] | None = None, skip: set[str] | None = None):
    skip = (skip or set()) | SKIP_DIRS
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            p = Path(dirpath) / fn
            if exts is None or p.suffix.lower() in exts:
                yield p


class Resolver:
    """把引用字符串解析到真实图片文件"""

    def __init__(self, vault_attachments: Path | None):
        self.vault = REPO.parent          # Obsidian 库根目录（Career/）
        self.vault_attachments = vault_attachments
        self._by_name: dict[str, list[Path]] | None = None  # 文件名 → 候选路径

    def _build_index(self) -> dict[str, list[Path]]:
        index: dict[str, list[Path]] = {}
        roots = [REPO]
        if self.vault.is_dir() and self.vault != REPO:
            roots.append(self.vault)
        for root in roots:
            for p in walk_files(root, exts=IMAGE_EXT):
                index.setdefault(p.name.lower(), []).append(p)
        return index

    def index(self) -> dict[str, list[Path]]:
        if self._by_name is None:
            self._by_name = self._build_index()
        return self._by_name

    def resolve(self, dest: str, post: Path) -> Path | None:
        """返回图片的真实路径；解析不出来返回 None"""
        raw = dest.strip().lstrip("<").rstrip(">")
        if not raw or is_external(raw):
            return None
        # 编辑器可能写成 URL 编码形式（Pasted%20image%20x.png）
        if "%" in raw:
            raw = unquote(raw)
        # 写有 alt 的裸路径（Obsidian 有时带 <...>）也一并去掉
        raw = raw.lstrip("<").rstrip(">")
        name = Path(raw).name
        if Path(name).suffix.lower() not in IMAGE_EXT:
            return None

        # 1. 直接可解析的相对/绝对路径
        direct = [
            post.parent / raw,                  # 文章旁边（相对文章）
            REPO / raw.lstrip("/"),             # 仓库根
            self.vault / raw.lstrip("/"),       # 库根
        ]
        if self.vault_attachments:
            direct += [
                self.vault_attachments / name,  # 库 attachments/
                self.vault_attachments / raw,
            ]
        for cand in direct:
            try:
                if cand.is_file() and cand.suffix.lower() in IMAGE_EXT:
                    vlog(f"命中路径: {cand}")
                    return cand.resolve()
            except OSError:
                pass

        # 2. 按文件名在全库/全仓搜索（编辑器粘贴常写错前缀）
        hits = self.index().get(name.lower(), [])
        if hits:
            # 优先 assets/images、其次库 attachments、最后其它
            def rank(p: Path) -> tuple:
                return (
                    0 if p.parent == ASSETS_IMAGES else 1,
                    0 if self.vault_attachments and p.parent == self.vault_attachments else 1,
                    len(p.parts),
                )

            best = sorted(hits, key=rank)[0]
            vlog(f"按文件名命中: {best}")
            return best.resolve()
        return None


def referenced_elsewhere(name: str, post: Path, vault: Path | None) -> bool:
    """除当前文章外，是否还有别的文件引用同一个文件名"""
    pat = re.compile(re.escape(name), re.I)
    roots = [REPO]
    if vault and vault.is_dir() and vault != REPO:
        roots.append(vault)
    for root in roots:
        for p in walk_files(root, exts={".md"}, skip=SKIP_DIRS):
            if p == post:
                continue
            try:
                if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                    vlog(f"其它引用者: {p}")
                    return True
            except OSError:
                pass
    return False


# ---------------------------------------------------------------- 主逻辑


class Action:
    def __init__(self, post: Path, raw_ref: str, source: Path | None, target: Path | None, kind: str, note: str = ""):
        self.post = post
        self.raw_ref = raw_ref
        self.source = source
        self.target = target
        self.kind = kind  # move | copy | rename | missing
        self.note = note


def post_slug(post: Path) -> str:
    """文章 slug：page bundle（index.md）用目录名，普通文件用文件名"""
    if post.stem.lower() in {"index", "_index"}:
        return sanitize(post.parent.name)
    return sanitize(post.stem)


def plan_target(post: Path, source: Path, resolver: Resolver) -> Path:
    """决定图片在 assets/images/ 里的目标文件名"""
    # 已经在位且文件名干净（无空格等会破坏 Markdown/URL 的字符）→ 保留原名，只改引用写法
    if source.parent == ASSETS_IMAGES and RE_SAFE_NAME.match(source.name):
        return source
    slug = post_slug(post)
    stem = sanitize(source.stem)
    if not stem.startswith(slug):
        stem = f"{slug}-{stem}" if stem else slug
    target = ASSETS_IMAGES / f"{stem}{source.suffix.lower()}"
    n = 2
    while target.exists() and source.exists() and md5(target) != md5(source):
        target = ASSETS_IMAGES / f"{stem}-{n}{source.suffix.lower()}"
        n += 1
    return target


def collect(post: Path, resolver: Resolver) -> list[tuple[str, str]]:
    """返回 [(匹配到的原始文本, 引用目标)]"""
    text = post.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for m in RE_WIKILINK.finditer(text):
        out.append((m.group(0), m.group(1).strip()))
    for m in RE_MDLINK.finditer(text):
        out.append((m.group(0), m.group(2).strip()))
    for m in RE_IMGTAG.finditer(text):
        out.append((m.group(0), m.group(3).strip()))
    return out


def process(post: Path, resolver: Resolver, fix: bool) -> list[Action]:
    text = post.read_text(encoding="utf-8")
    actions: list[Action] = []

    def handle(raw_ref: str) -> str | None:
        """返回替换后的引用文本；None 表示不改动"""
        if is_external(raw_ref):
            return None
        basename = Path(raw_ref.strip().lstrip("<").rstrip(">")).name
        source = resolver.resolve(raw_ref, post)
        if source is None:
            if Path(basename).suffix.lower() in IMAGE_EXT:
                actions.append(Action(post, raw_ref, None, None, "missing"))
            return None

        target = plan_target(post, source, resolver)
        canonical = f"/images/{target.name}"

        # 已在 assets/images 且名字没变 → 只需把路径改规范（如果还不是规范写法）
        if source == target:
            if raw_ref.strip() == canonical:
                return None
            actions.append(Action(post, raw_ref, source, target, "rename"))
            return canonical

        outside_repo = REPO not in source.parents
        copy = False
        if outside_repo and referenced_elsewhere(source.name, post, resolver.vault):
            copy = True  # 别的笔记还要用 → 保留原件
        kind = "copy" if copy else "move"
        actions.append(Action(post, raw_ref, source, target, kind))
        return canonical

    # 逐种写法替换（先算规划，再统一替换）
    replacements: list[tuple[str, str]] = []

    for m in RE_WIKILINK.finditer(text):
        raw_ref = m.group(1).strip()
        new = handle(raw_ref)
        if new is None and raw_ref.strip() == "":
            continue
        alt = (m.group(2) or "").strip()
        if new:
            alt_text = alt or sanitize(Path(raw_ref).stem) or "image"
            replacements.append((m.group(0), f"![{alt_text}]({new})"))

    for m in RE_MDLINK.finditer(text):
        raw_ref = m.group(2).strip()
        new = handle(raw_ref)
        if new:
            replacements.append((m.group(0), f"![{m.group(1)}]({new})"))

    for m in RE_IMGTAG.finditer(text):
        raw_ref = m.group(3).strip()
        new = handle(raw_ref)
        if new:
            replacements.append((m.group(0), f'{m.group(1)}"{new}"'))

    for old, new in replacements:
        text = text.replace(old, new, 1)

    if fix and replacements:
        ASSETS_IMAGES.mkdir(parents=True, exist_ok=True)
        done: set[tuple[str, str]] = set()
        for a in actions:
            if a.kind not in {"move", "copy"} or not a.source or not a.target:
                continue
            key = (str(a.source), str(a.target))
            if key in done:
                continue
            done.add(key)
            if not a.source.exists():
                a.note = "源文件已不存在（同一文件被多处引用，已处理过）"
                continue
            same = a.target.exists() and a.source != a.target and md5(a.target) == md5(a.source)
            if same:
                if a.kind == "move":
                    a.source.unlink()
                    a.note = "目标已有相同内容，删除源文件"
                else:
                    a.note = "目标已有相同内容，跳过复制"
            elif a.kind == "move":
                shutil.move(str(a.source), str(a.target))
            else:
                shutil.copy2(str(a.source), str(a.target))
        post.write_text(text, encoding="utf-8")

    return actions


def main() -> int:
    global VERBOSE
    ap = argparse.ArgumentParser(description="整理博客文章里的图片引用（自动归位到 assets/images/）")
    ap.add_argument("--check", action="store_true", help="只检查，不改动文件；有待整理项时退出码 1")
    ap.add_argument("--verbose", action="store_true", help="打印解析细节")
    args = ap.parse_args()
    VERBOSE = args.verbose

    vault_attachments = find_vault_attachments()
    resolver = Resolver(vault_attachments)
    vlog(f"仓库: {REPO}")
    vlog(f"库 attachments: {vault_attachments or '未找到'}")

    if not CONTENT.is_dir():
        log(f"✗ 找不到 {CONTENT}")
        return 2

    posts = sorted(p for p in CONTENT.rglob("*.md"))
    total = {"move": 0, "copy": 0, "rename": 0, "missing": 0}
    touched: list[Path] = []

    for post in posts:
        actions = process(post, resolver, fix=not args.check)
        if not actions:
            continue
        rel = post.relative_to(REPO)
        for a in actions:
            total[a.kind] += 1
            if a.kind == "missing":
                log(f"  ⚠ {rel}: 找不到图片 {a.raw_ref}")
                continue
            verb = {"move": "移动", "copy": "复制", "rename": "改写"}[a.kind]
            src = a.source.relative_to(REPO) if a.source and REPO in a.source.parents else (
                f"{a.source.parent.name}/{a.source.name}" if a.source else "?")
            dst = f"assets/images/{a.target.name}" if a.target else "?"
            tail = f"  ({a.note})" if a.note else ""
            log(f"  {verb}: {src} → {dst}{tail}")
        if any(a.kind in {"move", "copy", "rename"} for a in actions):
            touched.append(post)

    log("")
    summary = (f"整理项: 移动 {total['move']}，复制 {total['copy']}，改写 {total['rename']}"
               f"，找不到 {total['missing']}")
    if args.check:
        pending = total["move"] + total["copy"] + total["rename"]
        if pending:
            log(f"⚠ {summary}")
            log("  · 执行 python3 scripts/sync-images.py 可自动整理（发布脚本也会自动跑）")
            return 1
        log(f"✓ 图片引用全部正常（{summary}）")
        return 0

    if not touched and not total["missing"]:
        log("✓ 无需整理，图片引用都规范")
        return 0
    log(f"✓ 已整理 {len(touched)} 篇文章（{summary}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
