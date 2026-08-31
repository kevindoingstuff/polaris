"""Diagrams for a pull request. Python 3.8+, stdlib only; draw.io desktop is optional (PNG export).

  prdiagram.py changes <repo> <base> <head> [-o pr-changes.drawio] [--png]
                       [--groups pr-summary.json] [--collapse N]
      Prints the change graph (one block per commit, one line per file:
      Added / Changed / Removed / Renamed). With -o, also writes a diagram:
      commits on the left, changed files on the right boxed by directory.
      Large PR: --groups takes the summary spec below (the "groups" form); the
      left column becomes one box per theme and the printed graph becomes one
      <details> block per theme (Markdown, paste as is). Every commit in the
      range must be in exactly one group. --collapse N turns a directory with
      more than N changed files into one box with counts.

  prdiagram.py summary <spec.json> -o pr-summary.drawio [--png]
      "This PR: these changes" at a glance. PR title on top, commits left to
      right, each commit's main changes as chips coloured by their first word
      (Add green, Change orange, Fix teal, Remove red):
        {"title": "Limit each client to 100 requests per minute",
         "commits": [{"sha": "5c4f747", "subject": "feat(api): add token-bucket rate limiter",
                      "changes": ["Add rate limiter", "Add RATE_LIMIT setting"]}, ...]}
      Large PR (more than ~8 commits): one column per theme instead:
        {"title": "...", "groups": [{"title": "Rate limiter", "commits": ["5c4f747", "07c412a"],
                                     "changes": ["Add token-bucket limiter", ...]}, ...]}

  prdiagram.py design <spec.json> -o pr-design.drawio [--png]
      Before/after component diagram from a spec you write:
        {"before": {"nodes": [{"id": "api", "label": "API"}, ...],
                    "edges": [["api", "db"], ...]},
         "after":  {"nodes": [...], "edges": [...]}}
      Nodes match by id. Added = green, removed = red dashed, kept = grey,
      same id with a new label (a rename) = orange.

  --png  exports <out>.png beside the .drawio when draw.io desktop is found
         (drawio / draw.io on PATH, or the default Windows / macOS install).
         Not found, or the export fails: prints a notice and leaves the .drawio only.

  prdiagram.py attach <repo> <pr-number> <file>... [--branch pr-assets] [--remote origin]
      Puts the files into the PR body. GitHub has no API for the drag-and-drop
      upload, so the files are committed to an orphan branch (default pr-assets,
      created on first use, never merged) under pr-<number>/ and pushed. Prints one
      `![name](https://github.com/<owner>/<repo>/blob/<sha>/...?raw=true)` line per
      file to paste into the body (renders in private repos too). Uses a temporary
      index: the working tree and the current branch are untouched. Needs a
      github.com remote.

Exit status 0 on success; 2 with a one-line message on bad input (unknown git
range, malformed spec, missing -o, no github.com remote).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from xml.sax.saxutils import escape

WORD = {"A": "Added", "M": "Changed", "D": "Removed", "R": "Renamed"}
COL = {"A": ("#d5e8d4", "#82b366"), "M": ("#ffe6cc", "#d79b00"),
       "D": ("#f8cecc", "#b85450"), "R": ("#e1d5e7", "#9673a6"), "K": ("#f5f5f5", "#666666"),
       "F": ("#b1ddf0", "#10739e")}
NAMES = {"A": "added", "M": "changed", "D": "removed", "R": "renamed", "K": "unchanged", "F": "fixed"}
KIND = {"Add": "A", "Change": "M", "Fix": "F", "Remove": "D"}


def fail(msg):
    print(f"prdiagram: {msg}", file=sys.stderr)
    sys.exit(2)


def h(s):
    """Text for an html=1 label: HTML-escape it, then XML-attribute-escape the result."""
    return escape(escape(str(s)))


class Doc:
    def __init__(self):
        self.cells, self.n = [], 2

    def add(self, xml):
        self.cells.append(xml.replace("{id}", str(self.n)))
        self.n += 1
        return self.n - 1

    def box(self, label, x, y, w, h_, style, parent="1"):
        """`label` must already be escaped (use h() for user text)."""
        return self.add(f'<mxCell id="{{id}}" value="{label}" style="{style}" vertex="1" parent="{parent}">'
                        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h_}" as="geometry"/></mxCell>')

    def edge(self, src, tgt, style, label="", points=(), label_at_end=False, base="edgeStyle=orthogonalEdgeStyle;"):
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        geo = ('<mxGeometry relative="1" x="1" as="geometry"><mxPoint x="-70" y="-12" as="offset"/>' if label_at_end
               else '<mxGeometry relative="1" as="geometry">')
        arr = f'<Array as="points">{pts}</Array>' if pts else ""
        return self.add(f'<mxCell id="{{id}}" value="{label}" style="{base}html=1;rounded=1;endArrow=block;{style}" '
                        f'edge="1" parent="1" source="{src}" target="{tgt}">{geo}{arr}</mxGeometry></mxCell>')

    def write(self, path, name):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="drawio"><diagram name="{escape(name)}"><mxGraphModel><root>'
                    '<mxCell id="0"/><mxCell id="1" parent="0"/>\n' + "\n".join(self.cells) + "\n</root></mxGraphModel></diagram></mxfile>")


def legend(doc, x, y, keys):
    for k, st in enumerate(keys):
        fill, stroke = COL[st]
        doc.box(NAMES[st], x + k * 130, y, 110, 30, f"rounded=1;whiteSpace=wrap;html=1;fontSize=11;fillColor={fill};strokeColor={stroke};")


# ---------------------------------------------------------------- changes
def git_changes(repo, base, head):
    r = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", "log", "--reverse", "--no-merges", "-M",
                        "--name-status", "--format=--- %h %s", f"{base}..{head}"],
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode:
        fail(f"git log {base}..{head} failed: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'unknown error'}")
    commits, files = [], OrderedDict()
    for line in r.stdout.splitlines():
        if line.startswith("--- "):
            sha, _, msg = line[4:].partition(" ")
            commits.append({"sha": sha, "msg": msg, "changes": []})
        elif line.strip() and commits:
            parts = line.split("\t")
            st, path = parts[0][0], parts[-1]
            old = parts[1] if st == "R" and len(parts) == 3 else None
            if st == "C":
                st = "A"                      # a copy is a new file
            elif st not in WORD:
                st = "M"                      # T (type change), U, X ... shown as changed
            commits[-1]["changes"].append((st, path, old))
            f = files.setdefault(path, {"status": st, "old": old, "touches": []})
            if not (st == "M" and f["status"] in ("A", "R")):   # a new or renamed file that is then edited stays A / R
                f["status"] = st
            f["old"] = f["old"] or old
            f["touches"].append((len(commits) - 1, st))
    if not commits:
        fail(f"no commits in {base}..{head}")
    return commits, files


def fold(cur, st):
    """Combine two statuses of one file (or one directory) in order: a new or renamed file that is then edited stays A / R."""
    return cur if (st == "M" and cur in ("A", "R")) else st


def print_commits(commits):
    for c in commits:
        print(f"{c['sha']} {c['msg']}")
        for i, (st, path, old) in enumerate(c["changes"]):
            tee = "└─" if i == len(c["changes"]) - 1 else "├─"
            what = f"{old} → {path}" if st == "R" else path
            print(f"{tee} {WORD[st]:<8} {what}")


def print_grouped(commits, groups, gi):
    """Markdown: one <details> block per theme, the per-commit graph inside."""
    for k, g in enumerate(groups):
        idx = [i for i in range(len(commits)) if gi[i] == k]
        nfiles = len({p for i in idx for _, p, _ in commits[i]["changes"]})
        print(f"<details><summary><b>{g.get('title', f'Theme {k + 1}')}</b> — {len(idx)} commit{'s' if len(idx) != 1 else ''}, {nfiles} file{'s' if nfiles != 1 else ''}</summary>\n\n```")
        print_commits([commits[i] for i in idx])
        print("```\n</details>\n")


def resolve_groups(commits, spec):
    """Map commit index -> group index. Every commit in the range lands in exactly one group, or we fail with the list."""
    groups = spec.get("groups")
    if not isinstance(groups, list) or not groups:
        fail('the groups file needs a non-empty "groups" list ({"groups": [{"title", "commits": [shas], "changes": [...]}]})')
    gi = {}
    for k, g in enumerate(groups):
        for sha in g.get("commits") or []:
            sha = str(sha)
            hits = [i for i, c in enumerate(commits) if c["sha"].startswith(sha) or sha.startswith(c["sha"])]
            if not hits:
                fail(f'group "{g.get("title")}": commit {sha} is not in the range')
            for i in hits:
                if gi.get(i, k) != k:
                    fail(f"commit {commits[i]['sha']} is in two groups")
                gi[i] = k
    missing = [c["sha"] for i, c in enumerate(commits) if i not in gi]
    if missing:
        fail(f"commits in no group: {' '.join(missing)}")
    return groups, gi


def changes_diagram(commits, files, base, head, out, groups=None, gi=None, collapse=None):
    """Left: one box per commit, or per theme when groups are given. Right: changed files boxed by directory;
    a directory with more than `collapse` files becomes one box with counts."""
    doc = Doc()
    CX, CW, CH, CGAP = 40, 280, 70, 50
    DW, FH, FGAP, HDR, PAD = 320, 40, 12, 30, 12
    src_of = (lambda ci: gi[ci]) if groups else (lambda ci: ci)
    n_src = len(groups) if groups else len(commits)
    DX = CX + CW + 40 + n_src * 40 + 40                                 # the file column starts after the last lane

    # items: one per file, or one per collapsed directory; touches aggregated per source (commit or theme)
    items = OrderedDict()
    for p, f in files.items():
        d = p.rsplit("/", 1)[0] if "/" in p else "(root)"
        name = p.rsplit("/", 1)[-1]
        label = f"{f['old'].rsplit('/', 1)[-1]} → {name}" if f["status"] == "R" and f["old"] else name
        items[p] = {"dir": d, "label": label, "status": f["status"], "touches": OrderedDict(), "first": f["touches"][0][0]}
        for ci, st in f["touches"]:
            s = src_of(ci)
            items[p]["touches"][s] = fold(items[p]["touches"].get(s, st), st)
    if collapse:
        by_dir = OrderedDict()
        for p, it in items.items():
            by_dir.setdefault(it["dir"], []).append(it)
        for d, its in by_dir.items():
            if len(its) > collapse:
                counts = OrderedDict((k, sum(1 for it in its if it["status"] == k)) for k in "AMDR")
                touches = OrderedDict()
                for it in its:
                    for s, st in it["touches"].items():
                        touches[s] = fold(touches.get(s, st), st)
                for p in [p for p, it in items.items() if it["dir"] == d]:
                    del items[p]
                items[f"{d}/*"] = {"dir": d, "label": f"{len(its)} files · " + " · ".join(f"{n} {WORD[k].lower()}" for k, n in counts.items() if n),
                                   "status": "K", "touches": touches, "first": min(it["first"] for it in its)}

    # sources
    sid = {}
    for i in range(n_src):
        y = 60 + i * (CH + CGAP)
        if groups:
            g = groups[i]
            n = sum(1 for v in gi.values() if v == i)
            label = f"&lt;b&gt;{h(g.get('title', f'Theme {i + 1}'))}&lt;/b&gt;&#xa;{n} commit{'s' if n != 1 else ''}"
        else:
            label = f"&lt;b&gt;{h(commits[i]['sha'])}&lt;/b&gt;&#xa;{h(commits[i]['msg'])}"
        sid[i] = doc.box(label, CX, y, CW, CH, "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;align=left;spacingLeft=8;")
        if i:
            doc.edge(sid[i - 1], sid[i], "strokeColor=#6c8ebf;")
    doc.box(f"base: {h(base)}", CX, 20, CW, 30, "text;html=1;align=center;fontStyle=2;fontColor=#666666;")

    # directories, ordered by the first source that touches them
    dirs = OrderedDict()
    for key, it in items.items():
        dirs.setdefault(it["dir"], []).append(key)
    dirs = OrderedDict(sorted(dirs.items(), key=lambda kv: min(items[k]["first"] for k in kv[1])))

    def box_h(it):                                                     # a box grows with the sources that point at it
        return FH + max(0, len(it["touches"]) - 2) * 16

    fid, fy, fh, y = {}, {}, {}, 60
    for d, keys in dirs.items():
        hgt = HDR + PAD + sum(box_h(items[k]) + FGAP for k in keys)
        box = doc.box(h(d) + "/", DX, y, DW, hgt, f"swimlane;startSize={HDR};html=1;fontStyle=1;fillColor=#f5f5f5;strokeColor=#666666;pointerEvents=0;")
        yy = HDR + PAD // 2
        for key in keys:
            it = items[key]
            fill, stroke = COL[it["status"]]
            fh[key] = box_h(it)
            fy[key] = y + yy + fh[key] // 2
            fid[key] = doc.box(h(it["label"]), PAD, yy, DW - 2 * PAD, fh[key],
                               f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontFamily=Courier New;", parent=box)
            yy += fh[key] + FGAP
        y += hgt + 30

    for key, it in items.items():
        n = len(it["touches"])
        for k, (s, st) in enumerate(it["touches"].items()):
            _, stroke = COL[st]
            dash = "dashed=1;" if st == "D" else ""
            ey = 0.5 if n == 1 else 0.2 + 0.6 * k / (n - 1)  # several sources on one box: spread the entry points
            doc.edge(sid[s], fid[key], f"strokeColor={stroke};fontColor={stroke};fontStyle=1;{dash}exitX=1;exitY=0.5;entryX=0;entryY={ey};labelBackgroundColor=#ffffff;",
                     label=st, points=[(CX + CW + 40 + s * 40, round(fy[key] + (ey - 0.5) * fh[key]))], label_at_end=True)

    ly = max(y, 60 + n_src * (CH + CGAP)) + 10
    legend(doc, CX, ly, ["A", "M", "D", "R"] + (["K"] if collapse else []))
    what = f"{len(groups)} themes, " if groups else ""
    doc.box(f"PR {h(base)}..{h(head)} — {what}{len(commits)} commits, {len(files)} files", DX, 15, DW + 200, 30, "text;html=1;fontSize=16;fontStyle=1;")
    doc.write(out, "PR changes")


# ---------------------------------------------------------------- design
def ranks(nodes, edges):
    preds = {n: [a for a, b in edges if b == n and a != n] for n in nodes}
    memo = {}

    def rank(n, seen=()):
        if n in memo:
            return memo[n]
        if n in seen:
            return 0
        memo[n] = max([rank(p, seen + (n,)) + 1 for p in preds[n]], default=0)
        return memo[n]

    return {n: rank(n) for n in nodes}


def check_side(name, spec):
    nodes = spec.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        fail(f'"{name}" needs a non-empty "nodes" list')
    ids = []
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            fail(f'"{name}": every node needs an "id" (got {n!r})')
        ids.append(str(n["id"]))
    if len(set(ids)) != len(ids):
        fail(f'"{name}": duplicate node id')
    for e in spec.get("edges") or []:
        if not (isinstance(e, list) and len(e) == 2):
            fail(f'"{name}": every edge is [from, to] (got {e!r})')
        for end in e:
            if str(end) not in ids:
                fail(f'"{name}": edge {e!r} names unknown node "{end}"')


NW, NH, XS, YS, SHDR, SPAD = 150, 50, 190, 100, 34, 20   # design geometry: node, column pitch, rank pitch, header, padding


def plan_side(spec):
    """Rank the nodes (longest path), then order each rank by the barycenter of its neighbours (3 sweeps) so a
    node sits under its parents. Returns node positions relative to the side's container plus its size."""
    nodes = [str(n["id"]) for n in spec["nodes"]]
    labels = {str(n["id"]): str(n.get("label", n["id"])) for n in spec["nodes"]}
    edges = [(str(a), str(b)) for a, b in spec.get("edges") or []]
    rk = ranks(nodes, edges)
    rows = OrderedDict((r, [n for n in nodes if rk[n] == r]) for r in sorted(set(rk.values())))
    cols = max(len(r) for r in rows.values())
    preds = {n: [a for a, b in edges if b == n and a != n] for n in nodes}
    succs = {n: [b for a, b in edges if a == n and a != b] for n in nodes}

    def place(row):
        off = (cols - len(row)) * XS // 2
        return {n: off + c * XS for c, n in enumerate(row)}

    pos = {}
    for row in rows.values():
        pos.update(place(row))
    for sweep in range(3):
        nb = preds if sweep % 2 == 0 else succs
        for r, row in rows.items():
            def key(n):
                xs = [pos[m] for m in nb[n] if rk[m] != r]
                return sum(xs) / len(xs) if xs else pos[n]
            row.sort(key=key)
            pos.update(place(row))
    rel = {n: (SPAD + pos[n], SHDR + SPAD + rk[n] * YS) for n in nodes}          # top-left, container-relative
    w = SPAD * 2 + cols * XS - (XS - NW)
    hgt = SHDR + SPAD + len(rows) * YS - (YS - NH) + SPAD
    return {"nodes": nodes, "labels": labels, "edges": edges, "rk": rk, "rel": rel, "w": w, "h": hgt}


def draw_side(doc, title, plan, other, x0, y0, removed_side):
    """Draw one side at (x0, y0). Edges get explicit waypoints: the horizontal jog sits in the gap between ranks,
    a rank-skipping edge runs down a free gutter between columns, and parallel segments are offset a few px."""
    nodes, labels, edges, rk, rel = plan["nodes"], plan["labels"], plan["edges"], plan["rk"], plan["rel"]
    other_labels, other_edges = other["labels"], set(other["edges"])
    box = doc.box(title, x0, y0, plan["w"], plan["h"], f"swimlane;startSize={SHDR};html=1;fontStyle=1;fontSize=14;fillColor=#fafafa;strokeColor=#999999;pointerEvents=0;")
    ids, abs_ = {}, {}
    for n in nodes:
        rx, ry = rel[n]
        abs_[n] = (x0 + rx, y0 + ry)
        if n in other_labels:
            st = "M" if labels[n] != other_labels[n] else "K"
        else:
            st = "D" if removed_side else "A"
        fill, stroke = COL[st]
        dash = "dashed=1;" if st == "D" else ""
        ids[n] = doc.box(h(labels[n]), rx, ry, NW, NH, f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};{dash}", parent=box)

    def gap_y(r):                                                  # centre of the gap below rank r
        return y0 + SHDR + SPAD + r * YS + NH + (YS - NH) // 2

    gutters = sorted({abs_[n][0] - (XS - NW) // 2 for n in nodes} | {abs_[n][0] + NW + (XS - NW) // 2 for n in nodes})

    def free_gutter(gx, r_from, r_to):                             # no box of ranks r_from..r_to within 8px of x
        return all(not (abs_[m][0] - 8 < gx < abs_[m][0] + NW + 8) for m in nodes if r_from <= rk[m] <= r_to)

    used_gap, used_gut = {}, {}
    for a, b in edges:
        st = "K" if (a, b) in other_edges else ("D" if removed_side else "A")
        _, stroke = COL[st]
        style = f"strokeColor={stroke};strokeWidth={1 if st == 'K' else 2};{'dashed=1;' if st == 'D' else ''}"
        ra, rb = rk[a], rk[b]
        if rb <= ra:                                               # backward or same-rank edge: draw.io's router
            doc.edge(ids[a], ids[b], style)
            continue
        sx, tx = abs_[a][0] + NW // 2, abs_[b][0] + NW // 2
        k = used_gap[ra] = used_gap.get(ra, -1) + 1
        gy1 = gap_y(ra) + (k % 5 - 2) * 7                          # spread parallel jogs in one gap
        pts = []
        if rb == ra + 1:
            if sx != tx:
                pts = [(sx, gy1), (tx, gy1)]
        else:
            mid = (sx + tx) / 2
            free = [g for g in gutters if free_gutter(g, ra + 1, rb - 1)]
            gx = min(free, key=lambda g: abs(g - mid)) if free else int(mid)
            j = used_gut[gx] = used_gut.get(gx, -1) + 1
            gx += (j % 3 - 1) * 7
            k2 = used_gap[rb - 1] = used_gap.get(rb - 1, -1) + 1
            gy2 = gap_y(rb - 1) + (k2 % 5 - 2) * 7
            pts = [(sx, gy1), (gx, gy1), (gx, gy2), (tx, gy2)]
        doc.edge(ids[a], ids[b], style + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", points=pts, base="edgeStyle=none;")


def design_diagram(spec, out):
    for k in ("before", "after"):
        if not isinstance(spec.get(k), dict):
            fail(f'spec needs a "{k}" object')
        check_side(k, spec[k])
    doc = Doc()
    pb, pa = plan_side(spec["before"]), plan_side(spec["after"])
    stacked = pb["w"] + pa["w"] + 80 > 1300                        # too wide side by side: Before above After
    if stacked:
        xa, ya, W, H = 40, 60 + pb["h"] + 40, max(pb["w"], pa["w"]), pb["h"] + 40 + pa["h"]
    else:
        xa, ya, W, H = 40 + pb["w"] + 80, 60, pb["w"] + pa["w"] + 80, max(pb["h"], pa["h"])
    draw_side(doc, "Before", pb, pa, 40, 60, removed_side=True)
    draw_side(doc, "After", pa, pb, xa, ya, removed_side=False)
    doc.box(h(spec.get("title", "Design: before → after")), 40, 15, W, 30, "text;html=1;fontSize=16;fontStyle=1;")
    legend(doc, 40, 60 + H + 20, ["A", "M", "D", "K"])
    doc.write(out, "PR design")


# ---------------------------------------------------------------- summary
def summary_diagram(spec, out):
    """PR title on top, commits left to right, each commit's main changes as chips below it."""
    grouped = "groups" in spec
    commits = spec.get("groups") if grouped else spec.get("commits")
    if not isinstance(commits, list) or not commits:
        fail('spec needs a non-empty "commits" list (or "groups" for a large PR)')
    doc = Doc()
    CW, GAP, CH, CHIP, CGAP, X0, Y0 = 240, 40, 64, 34, 8, 40, 100
    total_w = max(len(commits) * CW + (len(commits) - 1) * GAP, 4 * 130 - 20)   # at least the legend's width
    doc.box(h(spec.get("title", "")), X0, 20, total_w, 50,
            "rounded=1;whiteSpace=wrap;html=1;fontSize=16;fontStyle=1;fillColor=#1f2430;fontColor=#ffffff;strokeColor=none;")
    prev, bottom = None, Y0 + CH
    for i, c in enumerate(commits):
        if not isinstance(c, dict):
            fail(f"every {'group' if grouped else 'commit'} is an object (got {c!r})")
        x = X0 + i * (CW + GAP)
        if grouped:
            shas = [str(s) for s in (c.get("commits") or [])]
            rng = shas[0] if len(shas) == 1 else f"{shas[0]}..{shas[-1]}" if shas else ""
            label = f"&lt;b&gt;{h(c.get('title', f'Theme {i + 1}'))}&lt;/b&gt;&#xa;{len(shas)} commit{'s' if len(shas) != 1 else ''} · {h(rng)}"
        else:
            label = f"&lt;b&gt;{h(c.get('sha', ''))}&lt;/b&gt;&#xa;{h(c.get('subject', ''))}"
        cid = doc.box(label, x, Y0, CW, CH,
                      "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;align=left;spacingLeft=8;fontSize=11;")
        if prev:
            doc.edge(prev, cid, "strokeColor=#6c8ebf;exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
        prev = cid
        chips = [str(ch) for ch in (c.get("changes") or []) if str(ch).strip()]
        y = Y0 + CH + 16
        for ch in chips:
            fill, stroke = COL[KIND.get(ch.split()[0], "M")]
            ch_h = CHIP if len(ch) <= 30 else CHIP + 16                    # a long chip wraps to two lines
            doc.box(h(ch), x, y, CW, ch_h, f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};align=left;spacingLeft=10;fontSize=12;")
            y += ch_h + CGAP
            bottom = max(bottom, y - CGAP)
    legend(doc, X0, bottom + 30, ["A", "M", "F", "D"])
    doc.write(out, "PR summary")


# ---------------------------------------------------------------- attach
def attach(repo, pr, files, branch="pr-assets", remote="origin"):
    def g(*args, env=None, ok=True):
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, encoding="utf-8", errors="replace", env=env)
        if ok and r.returncode:
            fail(f"git {args[0]} failed: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
        return r.stdout.strip()

    if not re.fullmatch(r"\d+", str(pr)):
        fail(f"pr-number must be digits (got {pr!r})")
    for f in files:
        if not os.path.isfile(f):
            fail(f"file not found: {f}")
    url = g("config", "--get", f"remote.{remote}.url")      # the configured URL, before any url.insteadOf rewrite
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if not m:
        fail(f"remote {remote} is not a github.com URL: {url}")
    owner, name = m.groups()

    g("fetch", "-q", remote, branch, ok=False)                                  # absent on first use
    parent = g("rev-parse", "--verify", "-q", f"refs/remotes/{remote}/{branch}", ok=False) or None
    fd, idx = tempfile.mkstemp(prefix="prdiagram-index-")
    os.close(fd)
    os.remove(idx)
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    try:
        if parent:
            g("read-tree", parent, env=env)
        for f in files:
            blob = g("hash-object", "-w", "--", os.path.abspath(f))
            g("update-index", "--add", "--cacheinfo", f"100644,{blob},pr-{pr}/{os.path.basename(f)}", env=env)
        tree = g("write-tree", env=env)
    finally:
        if os.path.exists(idx):
            os.remove(idx)
    commit = g("commit-tree", tree, "-m", f"pr-{pr}: diagrams", *(["-p", parent] if parent else []))
    g("push", "-q", remote, f"{commit}:refs/heads/{branch}")
    for f in files:
        base = os.path.basename(f)
        # blob?raw=true, not raw.githubusercontent.com: GitHub's image proxy fetches anonymously, so raw URLs 404 in a
        # private repo; github.com URLs are not proxied and the browser follows the redirect with the viewer's session.
        print(f"![{base.split('.')[0]}](https://github.com/{owner}/{name}/blob/{commit}/pr-{pr}/{base}?raw=true)")


# ---------------------------------------------------------------- export
def find_drawio():
    for c in ("drawio", "draw.io"):
        if shutil.which(c):
            return c
    for p in (r"C:\Program Files\draw.io\draw.io.exe", os.path.expandvars(r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe"),
              "/Applications/draw.io.app/Contents/MacOS/draw.io"):
        if os.path.exists(p):
            return p
    return None


def export_png(drawio_path):
    exe = find_drawio()
    if not exe:
        print(f"draw.io desktop not found; wrote {drawio_path} only", file=sys.stderr)
        return None
    png = drawio_path + ".png"
    try:
        subprocess.run([exe, "-x", "-f", "png", "-e", "-s", "2", "-b", "10", "-o", png, drawio_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        print(f"draw.io export failed ({type(e).__name__}); wrote {drawio_path} only", file=sys.stderr)
        return None
    if not os.path.exists(png):
        print(f"draw.io produced no PNG; wrote {drawio_path} only", file=sys.stderr)
        return None
    iend = b"IEND\xaeB`\x82"
    with open(png, "rb") as f:
        data = f.read()
    if data.endswith(b"\x00\x00\x00\x00") and not data.endswith(iend):  # draw.io -e drops the IEND type + CRC
        with open(png, "ab") as f:
            f.write(iend)
    return png


def load_spec(path):
    try:
        with open(path, encoding="utf-8-sig") as f:   # -sig: PowerShell's Out-File writes a BOM
            return json.load(f)
    except FileNotFoundError:
        fail(f"spec not found: {path}")
    except json.JSONDecodeError as e:
        fail(f"spec is not valid JSON: {path}: {e}")


def main(argv):
    if sys.version_info < (3, 8):
        fail("needs Python 3.8 or newer")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # box-drawing chars on a cp1252 console
    png = "--png" in argv
    argv = [a for a in argv if a != "--png"]
    opts = {"-o": None, "--branch": "pr-assets", "--remote": "origin", "--groups": None, "--collapse": None}
    for flag in list(opts):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                fail(f"{flag} needs a value")
            opts[flag] = argv[i + 1]
            del argv[i:i + 2]
    out = opts["-o"]
    cmd = argv[0]
    if cmd == "attach":
        if len(argv) < 4:
            fail("usage: attach <repo> <pr-number> <file>... [--branch pr-assets] [--remote origin]")
        attach(argv[1], argv[2], argv[3:], opts["--branch"], opts["--remote"])
        return
    if cmd == "changes":
        if len(argv) != 4:
            fail("usage: changes <repo> <base> <head> [-o out.drawio] [--png]")
        commits, files = git_changes(argv[1], argv[2], argv[3])
        groups = gi = None
        if opts["--groups"]:
            groups, gi = resolve_groups(commits, load_spec(opts["--groups"]))
        collapse = None
        if opts["--collapse"] is not None:
            if not re.fullmatch(r"\d+", opts["--collapse"]) or int(opts["--collapse"]) < 1:
                fail("--collapse needs a positive number of files")
            collapse = int(opts["--collapse"])
        if groups:
            print_grouped(commits, groups, gi)
        else:
            print_commits(commits)
        if out:
            changes_diagram(commits, files, argv[2], argv[3], out, groups, gi, collapse)
    elif cmd in ("design", "summary"):
        if len(argv) != 2 or not out:
            fail(f"usage: {cmd} <spec.json> -o out.drawio [--png]")
        (design_diagram if cmd == "design" else summary_diagram)(load_spec(argv[1]), out)
    else:
        fail(f"unknown command {cmd!r}; run with --help")
    if out:
        print(f"wrote {out}", file=sys.stderr)
        if png:
            p = export_png(out)
            if p:
                print(f"wrote {p}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
