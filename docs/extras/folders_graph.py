#!/usr/bin/env python3
"""Generate an Obsidian-style graph of the repo's Markdown files.

Usage:  python3 folders_graph.py [repo_dir] [--mode folders|tags|both] > graph.dot
        neato -Tsvg graph.dot -o graph.svg

File nodes are labelled with the front-matter title: (falls back to the file name).
Tags are read from YAML front matter (tags: [a, b] / tags: a, b / a "- a" list)
and from inline #tags in the text (code blocks and inline code are ignored).
"""
import argparse
import os
import re

ap = argparse.ArgumentParser()
ap.add_argument("repo", nargs="?", default=".")
ap.add_argument("--mode", choices=["folders", "tags", "both"], default="folders")
ap.add_argument("--hide-untagged", action="store_true",
                help="in tags mode, drop files that have no tags")
ap.add_argument("--spacing", type=float, default=0.8,
                help="edge length in inches; raise it to spread the graph out")
args = ap.parse_args()

ROOT = os.path.abspath(args.repo)
SKIP = {".git", "node_modules", "build", "install", "log", ".venv", "__pycache__"}

ROOT_COLOR, DIR_COLOR, FILE_COLOR = "#7f6df2", "#a99cf5", "#9a9a9a"
TAG_COLOR, TEXT_COLOR = "#5fb98f", "#8a8a8a"

INLINE_TAG = re.compile(r"(?:^|(?<=\s))#([A-Za-z0-9_\-/]*[A-Za-z_\-/][A-Za-z0-9_\-/]*)")


def node_id(rel):
    return "root" if rel in ("", ".") else re.sub(r"\W", "_", rel)


def read_meta(path):
    """Return (title or None, set of tags) for a Markdown file."""
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None, set()
    tags, title = set(), None

    # YAML front matter
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if fm:
        body = text[fm.end():]
        lines = fm.group(1).splitlines()
        for line in lines:
            t = re.match(r"^title\s*:\s*(.+)$", line.strip(), re.I)
            if t:
                title = t.group(1).strip().strip("'\"") or None
        for i, line in enumerate(lines):
            m = re.match(r"^(tags?|keywords)\s*:\s*(.*)$", line.strip(), re.I)
            if not m:
                continue
            value = m.group(2).strip()
            if value:  # tags: [a, b]  or  tags: a, b
                tags.update(t.strip(" '\"#") for t in re.split(r"[,\s]+", value.strip("[]")))
            else:      # tags:\n  - a\n  - b
                for nxt in lines[i + 1:]:
                    item = re.match(r"^\s*-\s*(.+)$", nxt)
                    if not item:
                        break
                    tags.add(item.group(1).strip(" '\"#"))
    else:
        body = text

    # inline #tags, skipping fenced code and `inline code`
    body = re.sub(r"```.*?```|~~~.*?~~~", "", body, flags=re.S)
    body = re.sub(r"`[^`\n]*`", "", body)
    # if the file ends with a "# Tags" section, read tags only from there
    sections = re.split(r"(?im)^#{1,6}\s+tags\s*$", body)
    if len(sections) > 1:
        body = sections[-1]
    tags.update(INLINE_TAG.findall(body))

    # drop hex colours like #e3f2fd that look like tags
    hexcolor = re.compile(r"^(?=.*\d)[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?$")
    return title, {t.lower() for t in tags if t and not hexcolor.match(t)}


nodes, edges = {}, set()

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = sorted(d for d in dirnames if d not in SKIP and not d.startswith("."))
    for f in sorted(filenames):
        if not f.lower().endswith(".md"):
            continue
        full = os.path.join(dirpath, f)
        rel = os.path.relpath(full, ROOT)
        fid = node_id(rel)
        title, tags = read_meta(full)
        if args.mode == "folders":
            tags = set()

        if args.mode == "tags" and args.hide_untagged and not tags:
            continue
        nodes[fid] = ("file", title or os.path.splitext(f)[0])

        for t in tags:
            tid = "tag__" + re.sub(r"\W", "_", t)
            nodes[tid] = ("tag", "#" + t)
            edges.add((tid, fid))

        if args.mode in ("folders", "both"):
            child, parent = rel, os.path.dirname(rel)
            while True:
                pid = node_id(parent)
                kind = "root" if pid == "root" else "dir"
                label = os.path.basename(ROOT) if kind == "root" else os.path.basename(parent)
                nodes[pid] = (kind, label)
                edges.add((pid, node_id(child)))
                if pid == "root":
                    break
                child, parent = parent, os.path.dirname(parent)

style = {
    "root": (ROOT_COLOR, 0.42, 13),
    "dir":  (DIR_COLOR, 0.28, 11),
    "tag":  (TAG_COLOR, 0.24, 11),
    "file": (FILE_COLOR, 0.17, 11),
}


def esc(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def html_label(label, size, fs):
    """Text below the dot: an empty cell above balances the text cell below,
    so the label box stays centred on the node and the text clears the circle."""
    gap = round(size * 72 / 2) + 2            # circle radius in points, plus a little
    text = round(fs * 1.25)
    safe = (label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
            f'<TR><TD HEIGHT="{gap + text}"> </TD></TR>'
            f'<TR><TD HEIGHT="{gap}"> </TD></TR>'
            f'<TR><TD HEIGHT="{text}">{safe}</TD></TR></TABLE>>')


# fixedsize=shape: the circle is drawn at its own size and edges stop at the
# circle, but neato counts the whole label when pushing nodes apart.
print("graph G {")
print('  layout=neato; overlap=prism; overlap_scaling=0; sep="+3"; splines=false; outputorder=edgesfirst;')
print('  pack=6; pad=0.4; bgcolor="transparent";')
print('  node [shape=circle, style=filled, penwidth=0, fixedsize=shape,')
print(f'        fontname="Helvetica,sans-Serif", fontcolor="{TEXT_COLOR}"];')
print(f'  edge [color="{TEXT_COLOR}80", penwidth=1.1, len={args.spacing}];')
for nid, (kind, label) in sorted(nodes.items()):
    color, size, fs = style[kind]
    print(f'  "{nid}" [label={html_label(label, size, fs)}, fillcolor="{color}", '
          f'width={size}, height={size}, fontsize={fs}];')
for a, b in sorted(edges):
    print(f'  "{a}" -- "{b}";')
print("}")
