#!/usr/bin/env python3
"""Check which sections of the project map are stale.

Usage: python3 -I map-drift.py [repo_root]

Reads docs/PROJECT_MAP.md (and docs/map/*.md), takes the map commit from its header,
and for every "## " section checks the backticked paths it mentions:
  BROKEN  - a mentioned path no longer exists
  STALE   - a mentioned file/dir changed since the map commit (incl. uncommitted changes)
  OK      - nothing mentioned changed
Also lists new top-level directories (depth <= 2) that the map does not mention.
Read-only: never modifies anything.
"""
import fnmatch
import glob
import os
import re
import subprocess
import sys

PATH_RE = re.compile(r"`([^`\s]+)`")
COMMIT_RE = re.compile(r"`([0-9a-f]{7,40})`")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".build", "Pods", "venv", ".venv", "__pycache__", ".next", "DerivedData"}


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def looks_like_path(tok, root):
    """Return a repo-relative path for a backticked token, or None if it is not a path.

    Tokens with "/" are treated as paths. Tokens without "/" (e.g. `CLAUDE.md` vs `Next.js`)
    count only if they exist at the repo root, so library names don't show up as BROKEN.
    """
    tok = tok.strip()
    if tok.startswith(("http://", "https://", "-", "$", "@", "<")) or "=" in tok:
        return None
    tok = re.sub(r":[\w\-]+(?:[:\-]\d+)*$", "", tok)  # strip :42, :func, :10-20
    if tok.startswith("./"):
        tok = tok[2:]
    tok = tok.rstrip("/")
    if not tok or not re.fullmatch(r"[\w.\-/*\[\]()+]+", tok):
        return None
    if "/" in tok:
        return tok
    if re.search(r"\.[A-Za-z0-9]{1,6}$", tok) and os.path.exists(os.path.join(root, tok)):
        return tok
    return None


def parse_sections(text):
    sections, title, buf = [], "(шапка)", []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            sections.append((title, "\n".join(buf)))
            title, buf = line[3:].strip(), []
        else:
            buf.append(line)
    sections.append((title, "\n".join(buf)))
    return sections


def exists(root, p):
    full = os.path.join(root, p)
    if any(c in p for c in "*?["):
        return bool(glob.glob(full, recursive=True))
    return os.path.exists(full)


def touched(p, changed):
    hits = []
    for f in changed:
        if f == p or f.startswith(p + "/") or (any(c in p for c in "*?[") and fnmatch.fnmatch(f, p)):
            hits.append(f)
    return hits


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    top = git(root, "rev-parse", "--show-toplevel")
    if top:
        root = top.strip()
    main_map = os.path.join(root, "docs", "PROJECT_MAP.md")
    if not os.path.isfile(main_map):
        print("Карта не найдена: docs/PROJECT_MAP.md. Запусти /verdict:audit map.")
        return 1
    maps = [main_map] + sorted(glob.glob(os.path.join(root, "docs", "map", "*.md")))

    with open(main_map, encoding="utf-8") as fh:
        head = "".join(fh.readlines()[:8])
    m = COMMIT_RE.search(head)
    commit = m.group(1) if m else None
    changed, added = set(), set()
    if commit and git(root, "cat-file", "-e", commit + "^{commit}") is not None:
        out = git(root, "diff", "--name-status", "--no-renames", commit) or ""
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                changed.add(parts[-1])
                if parts[0].startswith("A"):
                    added.add(parts[-1])
        for line in (git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines():
            changed.add(line)
            added.add(line)
        n = (git(root, "rev-list", "--count", commit + "..HEAD") or "?").strip()
        print(f"Коммит карты: {commit}, коммитов после него: {n}, изменённых файлов: {len(changed)}")
    else:
        print("Коммит карты не найден в шапке или в истории: проверяю только существование путей.")

    all_mentioned = set()
    totals = {"OK": 0, "STALE": 0, "BROKEN": 0}
    for mp in maps:
        rel = os.path.relpath(mp, root)
        with open(mp, encoding="utf-8") as fh:
            text = fh.read()
        print(f"\n# {rel}")
        for title, body in parse_sections(text):
            paths = {p for p in (looks_like_path(t, root) for t in PATH_RE.findall(body)) if p}
            if not paths:
                continue
            all_mentioned |= paths
            broken = sorted(p for p in paths if not exists(root, p))
            stale = sorted({f for p in paths for f in touched(p, changed)})
            status = "BROKEN" if broken else "STALE" if stale else "OK"
            totals[status] += 1
            print(f"[{status}] {title}")
            for p in broken:
                print(f"    нет пути: {p}")
            for f in stale[:15]:
                print(f"    изменён: {f}")
            if len(stale) > 15:
                print(f"    ... и ещё {len(stale) - 15}")

    new_dirs = set()
    for f in added:
        parts = f.split("/")
        if len(parts) < 2 or any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        for depth in (1, 2):
            if len(parts) > depth:
                new_dirs.add("/".join(parts[:depth]))
    unmentioned = sorted(
        d for d in new_dirs
        if d != "docs" and not d.startswith("docs/")
        and not any(m == d or m.startswith(d + "/") or d.startswith(m + "/") for m in all_mentioned)
    )
    if unmentioned:
        print("\nНовые папки, которых нет в карте:")
        for d in unmentioned:
            print(f"    {d}/")

    print(f"\nИтого разделов: OK {totals['OK']}, STALE {totals['STALE']}, BROKEN {totals['BROKEN']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
