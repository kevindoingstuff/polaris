"""Diagrams for module docs. Python 3.8+, stdlib only; draw.io desktop is optional (PNG export).

  docsdiagram.py system     <spec.json> -o <out.drawio> [--highlight <id>] [--png]
      The whole system: one box per module plus the external systems, layered by
      dependency. --highlight <id> marks one module (yellow, bold, thick border)
      and thickens every edge that touches it.
        {"title": "shopling",
         "nodes": [{"id": "api", "label": "API"}, {"id": "db", "label": "Postgres", "external": true}],
         "edges": [["api", "db"], {"from": "api", "to": "auth", "label": "verify token", "kind": "call"}]}
      "external": true draws a dashed box. An edge is [from, to] or
      {"from", "to", "label"?, "kind"?}; kind is call (solid, the default),
      data (dashed), or event (dotted, open arrow).

  docsdiagram.py components <spec.json> -o <out.drawio> [--png]
      The parts inside one module. Same spec shape and layout as system.

  docsdiagram.py flow       <spec.json> -o <out.drawio> [--png]
      One order-dominated component or pipeline: stages left to right, branches
      and merges as extra edges. Same spec shape as system.

  docsdiagram.py sequence   <spec.json> -o <out.drawio> [--png]
      One flow: participants left to right, messages top to bottom.
        {"title": "POST /orders",
         "participants": [{"id": "client", "label": "Client"}, {"id": "api", "label": "API"}],
         "messages": [{"from": "client", "to": "api", "label": "POST /orders", "activate": true},
                      {"from": "api", "to": "client", "label": "201 Created", "kind": "return"}]}
      kind is call (solid, the default), return (dashed, open arrow), or async
      (open arrow). "activate": true draws a bar on the receiver's lifeline
      until its next return (or the last message).

  --png  exports <out>.png beside the .drawio when draw.io desktop is found
         (drawio / draw.io on PATH, or the default Windows / macOS install).
         Not found, or the export fails: prints a notice and leaves the .drawio only.

Exit status 0 on success; 2 with a one-line message on bad input (unknown
command, missing -o, malformed spec, unknown id, unknown kind).
"""
import json
import os
import shutil
import subprocess
import sys
from collections import OrderedDict
from xml.sax.saxutils import escape

COL = {"K": ("#f5f5f5", "#666666"), "H": ("#fff2cc", "#d6b656")}
NAMES = {"K": "module", "H": "this module"}
EDGE_KIND = {"call": "", "data": "dashed=1;", "event": "dashed=1;dashPattern=1 3;endArrow=open;"}
MSG_KIND = {"call": "", "return": "dashed=1;endArrow=open;", "async": "endArrow=open;"}


def fail(msg):
    print(f"docsdiagram: {msg}", file=sys.stderr)
    sys.exit(2)


def h(s):
    """Text for an html=1 label: HTML-escape it, then XML-attribute-escape the result."""
    return escape(escape(str(s)))


ID = "\x01id\x01"   # cell-id placeholder; a literal "{id}" in a label must survive


class Doc:
    def __init__(self):
        self.cells, self.n = [], 2

    def add(self, xml):
        self.cells.append(xml.replace(ID, str(self.n)))
        self.n += 1
        return self.n - 1

    def box(self, label, x, y, w, h_, style, parent="1"):
        """`label` must already be escaped (use h() for user text)."""
        return self.add(f'<mxCell id="{ID}" value="{label}" style="{style}" vertex="1" parent="{parent}">'
                        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h_}" as="geometry"/></mxCell>')

    def edge(self, src, tgt, style, label="", points=(), base="edgeStyle=orthogonalEdgeStyle;"):
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        arr = f'<Array as="points">{pts}</Array>' if pts else ""
        return self.add(f'<mxCell id="{ID}" value="{label}" style="{base}html=1;rounded=1;endArrow=block;{style}" '
                        f'edge="1" parent="1" source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')

    def write(self, path, name):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="drawio"><diagram name="{escape(name)}"><mxGraphModel><root>'
                    '<mxCell id="0"/><mxCell id="1" parent="0"/>\n' + "\n".join(self.cells) + "\n</root></mxGraphModel></diagram></mxfile>")


def legend(doc, x, y, keys):
    for k, st in enumerate(keys):
        fill, stroke = COL[st]
        doc.box(NAMES[st], x + k * 130, y, 110, 30, f"rounded=1;whiteSpace=wrap;html=1;fontSize=11;fillColor={fill};strokeColor={stroke};")


# ---------------------------------------------------------------- graph (system, components)
NW, NH, XS, YS, SHDR, SPAD = 150, 50, 210, 150, 34, 24   # node, column pitch, rank pitch, header, padding
LABEL_H, CHAR_W, LANE = 16, 6.4, 22


def norm_edge(e):
    if isinstance(e, list) and len(e) == 2:
        return str(e[0]), str(e[1]), "", "call"
    if isinstance(e, dict) and "from" in e and "to" in e:
        return str(e["from"]), str(e["to"]), str(e.get("label", "")), str(e.get("kind", "call"))
    fail(f'every edge is [from, to] or {{"from", "to", "label", "kind"}} (got {e!r})')


def check_graph(spec):
    """Returns the edges as (from, to, label, kind)."""
    nodes = spec.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        fail('spec needs a non-empty "nodes" list')
    ids = []
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            fail(f'every node needs an "id" (got {n!r})')
        ids.append(str(n["id"]))
    if len(set(ids)) != len(ids):
        fail("duplicate node id")
    edges = [norm_edge(e) for e in spec.get("edges") or []]
    for a, b, _, kind in edges:
        for end in (a, b):
            if end not in ids:
                fail(f'edge {a} -> {b} names unknown node "{end}"')
        if kind not in EDGE_KIND:
            fail(f'edge {a} -> {b}: unknown kind "{kind}" (call, data, event)')
    return edges


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


def plan_graph(spec, pairs):
    """Rank the nodes (longest path), then order each rank by the barycenter of its neighbours (3 sweeps) so a
    node sits under its parents. Returns node positions relative to the container plus its size."""
    nodes = [str(n["id"]) for n in spec["nodes"]]
    labels = {str(n["id"]): str(n.get("label", n["id"])) for n in spec["nodes"]}
    rk = ranks(nodes, pairs)
    rows = OrderedDict((r, [n for n in nodes if rk[n] == r]) for r in sorted(set(rk.values())))
    cols = max(len(r) for r in rows.values())
    preds = {n: [a for a, b in pairs if b == n and a != n] for n in nodes}
    succs = {n: [b for a, b in pairs if a == n and a != b] for n in nodes}

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
    return {"nodes": nodes, "labels": labels, "rk": rk, "rel": rel, "w": w, "h": hgt}


def draw_graph(doc, title, plan, edges, x0, y0, highlight, external):
    """Draw the graph at (x0, y0); returns its height. Forward edges get their own exit and entry ports along the
    boxes, their own lane in the gap below their rank (the gap grows with the lane count), and a free gutter
    between columns when they skip ranks. Labels are white text boxes on the edge's own segments, slid along the
    segment until they touch no box and no other label; a label wider than its segment sits beside the line."""
    nodes, labels, rk, rel = plan["nodes"], plan["labels"], plan["rk"], plan["rel"]
    ax_ = {n: x0 + rel[n][0] for n in nodes}                      # box left x; y comes after the lane count is known
    nranks = max(rk.values()) + 1

    # ports: spread a box's forward out-edges along its bottom (by target x) and in-edges along its top (by source x)
    fwd = [i for i, (a, b, _, _) in enumerate(edges) if rk[b] > rk[a]]
    outs, ins = {}, {}
    for i in fwd:
        outs.setdefault(edges[i][0], []).append(i)
        ins.setdefault(edges[i][1], []).append(i)
    port_out, port_in = {}, {}
    for lst in outs.values():
        lst.sort(key=lambda i: ax_[edges[i][1]])
        for k, i in enumerate(lst):
            port_out[i] = (k + 1) / (len(lst) + 1)
    for lst in ins.values():
        lst.sort(key=lambda i: ax_[edges[i][0]])
        for k, i in enumerate(lst):
            port_in[i] = (k + 1) / (len(lst) + 1)
    sx = {i: round(ax_[edges[i][0]] + NW * port_out[i]) for i in fwd}
    tx = {i: round(ax_[edges[i][1]] + NW * port_in[i]) for i in fwd}

    # gutters for rank-skipping edges: between columns, clear of every box in the ranks crossed
    gutters = sorted({ax_[n] - (XS - NW) // 2 for n in nodes} | {ax_[n] + NW + (XS - NW) // 2 for n in nodes})

    def free_gutter(g, r_from, r_to):
        return all(not (ax_[m] - 10 < g < ax_[m] + NW + 10) for m in nodes if r_from <= rk[m] <= r_to)

    gx, used_gut = {}, {}
    for i in fwd:
        ra, rb = rk[edges[i][0]], rk[edges[i][1]]
        if rb > ra + 1:
            mid = (sx[i] + tx[i]) / 2
            free = [g for g in gutters if free_gutter(g, ra + 1, rb - 1)]
            g = min(free, key=lambda g: abs(g - mid)) if free else int(mid)
            j = used_gut[g] = used_gut.get(g, -1) + 1
            gx[i] = g + (j % 5 - 2) * 12

    # lanes: every jog in a gap gets its own y, ordered by where it starts; a busy gap grows to fit
    jogs = {}
    for i in fwd:
        ra, rb = rk[edges[i][0]], rk[edges[i][1]]
        if rb == ra + 1:
            if sx[i] != tx[i]:
                jogs.setdefault(ra, []).append((sx[i], i, 0))
        else:
            jogs.setdefault(ra, []).append((sx[i], i, 0))
            jogs.setdefault(rb - 1, []).append((gx[i], i, 1))
    gap_h = {r: max(YS - NH, LANE * (len(jogs.get(r, [])) + 1)) for r in range(nranks)}
    ry = {}
    y = y0 + SHDR + SPAD
    for r in range(nranks):
        ry[r] = y
        y += NH + gap_h[r]
    height = y - gap_h[nranks - 1] + SPAD - y0
    lane = {}
    for r, lst in jogs.items():
        lst.sort()
        for k, (_, i, part) in enumerate(lst):
            lane[(i, part)] = ry[r] + NH + round(gap_h[r] * (k + 1) / (len(lst) + 1))

    box = doc.box(title, x0, y0, plan["w"], height, f"swimlane;startSize={SHDR};html=1;fontStyle=1;fontSize=14;fillColor=#fafafa;strokeColor=#999999;pointerEvents=0;")
    ids, abs_ = {}, {}
    for n in nodes:
        abs_[n] = (ax_[n], ry[rk[n]])
        fill, stroke = COL["H" if n == highlight else "K"]
        extra = "strokeWidth=3;fontStyle=1;" if n == highlight else ""
        extra += "dashed=1;" if n in external else ""
        ids[n] = doc.box(h(labels[n]), rel[n][0], ry[rk[n]] - y0, NW, NH, f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};{extra}", parent=box)
    rects = [(abs_[n][0], abs_[n][1], abs_[n][0] + NW, abs_[n][1] + NH) for n in nodes]

    placed, pending, lines = [], [], []                            # label rects placed; (label, segments) to place; all segments
    for i, (a, b, label, kind) in enumerate(edges):
        touch = highlight in (a, b)
        style = f"strokeColor={'#d6b656' if touch else '#666666'};strokeWidth={2 if touch else 1};{EDGE_KIND[kind]}"
        if i not in fwd:                                           # backward or same-rank edge: draw.io's router
            doc.edge(ids[a], ids[b], style + "labelBackgroundColor=#ffffff;fontSize=11;", label=h(label))
            continue
        ra, rb = rk[a], rk[b]
        sy, ty = abs_[a][1] + NH, abs_[b][1]
        if rb == ra + 1:
            if sx[i] == tx[i]:
                pts, segs = [], [((sx[i], sy), (sx[i], ty))]
            else:
                ly = lane[(i, 0)]
                pts = [(sx[i], ly), (tx[i], ly)]
                segs = [((sx[i], ly), (tx[i], ly)), ((sx[i], sy), (sx[i], ly)), ((tx[i], ly), (tx[i], ty))]
        else:
            ly1, ly2, g = lane[(i, 0)], lane[(i, 1)], gx[i]
            pts = [(sx[i], ly1), (g, ly1), (g, ly2), (tx[i], ly2)]
            segs = [((g, ly1), (g, ly2)), ((sx[i], ly1), (g, ly1)), ((g, ly2), (tx[i], ly2)), ((sx[i], sy), (sx[i], ly1)), ((tx[i], ly2), (tx[i], ty))]
        doc.edge(ids[a], ids[b], style + f"exitX={port_out[i]:.3f};exitY=1;entryX={port_in[i]:.3f};entryY=0;", points=pts, base="edgeStyle=none;")
        lines.extend(segs)
        if label:
            pending.append((label, segs))

    def clear(rect, own):
        x1, y1, x2, y2 = rect
        if not all(x2 <= a or x1 >= c or y2 <= b or y1 >= d for a, b, c, d in rects + placed):
            return False
        for (ax, ay), (bx, by) in lines:                           # no other edge's line through the label
            if ((ax, ay), (bx, by)) in own:
                continue
            if min(ax, bx) - 3 < x2 and max(ax, bx) + 3 > x1 and min(ay, by) - 3 < y2 and max(ay, by) + 3 > y1:
                return False
        return True

    for label, segs in pending:                                    # longest segment first, slide along it in 20px steps
        w = round(len(label) * CHAR_W) + 10
        segs = sorted(segs, key=lambda sg: -(abs(sg[1][0] - sg[0][0]) + abs(sg[1][1] - sg[0][1])))
        spot = None
        for (ax, ay), (bx, by) in segs:
            cx, cy = (ax + bx) / 2, (ay + by) / 2
            horizontal = ay == by
            span = abs(bx - ax) if horizontal else abs(by - ay)
            if horizontal and w > span - 24:                       # would blank the segment: sit above it instead
                cy -= LABEL_H / 2 + 2
            if not horizontal:                                     # beside a vertical run, to its right
                cx += w / 2 + 4
            for d in [0] + [sgn * k for k in range(1, int(span // 40) + 1) for sgn in (-20, 20)]:
                x, y = (cx + d, cy) if horizontal else (cx, cy + d)
                rect = (round(x - w / 2), round(y - LABEL_H / 2), round(x + w / 2), round(y + LABEL_H / 2))
                if clear(rect, segs):
                    spot = rect
                    break
            if spot:
                break
        if not spot:
            (ax, ay), (bx, by) = segs[0]
            cx, cy = (ax + bx) / 2, (ay + by) / 2
            spot = (round(cx - w / 2), round(cy - LABEL_H / 2), round(cx + w / 2), round(cy + LABEL_H / 2))
        placed.append(spot)
        doc.box(h(label), spot[0], spot[1], w, LABEL_H,
                "text;html=1;fontSize=11;align=center;verticalAlign=middle;fillColor=#ffffff;strokeColor=none;fontColor=#333333;spacing=0;spacingTop=-2;")
    return height


def graph_diagram(spec, out, highlight, name):
    # ponytail: one layered layout for system and components; fine to ~15 nodes, split the spec past that.
    edges = check_graph(spec)
    ids = [str(n["id"]) for n in spec["nodes"]]
    if highlight is not None and highlight not in ids:
        fail(f'--highlight: unknown node "{highlight}"')
    external = {str(n["id"]) for n in spec["nodes"] if n.get("external")}
    doc = Doc()
    plan = plan_graph(spec, [(a, b) for a, b, _, _ in edges])
    height = draw_graph(doc, h(spec.get("title", name)), plan, edges, 40, 20, highlight, external)
    ly = 20 + height + 20
    if highlight is not None:
        legend(doc, 40, ly, ["H", "K"])
        ly += 40
    if any(kind != "call" for _, _, _, kind in edges):
        doc.box("solid = call, dashed = data, dotted = event", 40, ly, 320, 24, "text;html=1;fontSize=11;fontColor=#666666;")
    doc.write(out, name)


# ---------------------------------------------------------------- sequence
PW, PB_W, PY, RH, Y1 = 200, 150, 70, 44, 150   # column pitch, participant width, header y, row pitch, first row y


def sequence_diagram(spec, out):
    parts = spec.get("participants") or []
    msgs = spec.get("messages") or []
    if not isinstance(parts, list) or not parts:
        fail('spec needs a non-empty "participants" list')
    if not isinstance(msgs, list) or not msgs:
        fail('spec needs a non-empty "messages" list')
    ids = []
    for p in parts:
        if not isinstance(p, dict) or "id" not in p:
            fail(f'every participant needs an "id" (got {p!r})')
        ids.append(str(p["id"]))
    if len(set(ids)) != len(ids):
        fail("duplicate participant id")
    rows = []
    for m in msgs:
        if not isinstance(m, dict) or "from" not in m or "to" not in m:
            fail(f'every message needs "from" and "to" (got {m!r})')
        a, b, kind = str(m["from"]), str(m["to"]), str(m.get("kind", "call"))
        for end in (a, b):
            if end not in ids:
                fail(f'message "{m.get("label", "")}" names unknown participant "{end}"')
        if kind not in MSG_KIND:
            fail(f'message "{m.get("label", "")}": unknown kind "{kind}" (call, return, async)')
        rows.append((a, b, str(m.get("label", "")), kind, bool(m.get("activate"))))

    doc = Doc()
    n = len(rows)
    height = 80 + n * RH + 20
    x = {}
    for i, p in enumerate(parts):
        pid = str(p["id"])
        px = 40 + i * PW
        x[pid] = px + PB_W // 2
        doc.box(h(p.get("label", pid)), px, PY, PB_W, height,
                "shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;collapsible=0;"
                "recursiveResize=0;outlineConnect=0;size=40;fillColor=#dae8fc;strokeColor=#6c8ebf;")
    doc.box(h(spec.get("title", "Sequence")), 40, 15, max(600, len(parts) * PW), 30, "text;html=1;fontSize=16;fontStyle=1;")

    def row_y(i):
        return Y1 + i * RH

    for i, (a, b, label, kind, act) in enumerate(rows):            # activation bars first so the arrows draw on top
        if not act:
            continue
        end = next((j for j in range(i + 1, n) if rows[j][0] == b and rows[j][3] == "return"), n - 1)
        doc.box("", x[b] - 5, row_y(i), 10, row_y(end) - row_y(i) + 4,
                "html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#ffffff;strokeColor=#6c8ebf;")
    for i, (a, b, label, kind, act) in enumerate(rows):
        y = row_y(i)
        anchor = "strokeColor=none;fillColor=none;"
        src = doc.box("", x[a] - 1, y - 1, 2, 2, anchor)
        if a == b:                                                 # self message: out, down, back
            tgt = doc.box("", x[b] - 1, y + 19, 2, 2, anchor)
            pts = [(x[a] + 60, y), (x[a] + 60, y + 20)]
        else:
            tgt = doc.box("", x[b] - 1, y - 1, 2, 2, anchor)
            pts = []
        doc.edge(src, tgt, f"strokeColor=#333333;verticalAlign=bottom;fontSize=11;{MSG_KIND[kind]}", label=h(label), points=pts, base="edgeStyle=none;")
    doc.write(out, "Sequence")


# ---------------------------------------------------------------- flow (left-to-right stages)
FW, FH, FXS, FYS = 150, 50, 220, 90


def flow_diagram(spec, out):
    # ponytail: draw.io's own orthogonal router handles flow-scale edge counts; the lane router above is for maps.
    edges = check_graph(spec)
    nodes = [str(n["id"]) for n in spec["nodes"]]
    labels = {str(n["id"]): str(n.get("label", n["id"])) for n in spec["nodes"]}
    external = {str(n["id"]) for n in spec["nodes"] if n.get("external")}
    rk = ranks(nodes, [(a, b) for a, b, _, _ in edges])
    cols = OrderedDict((r, [n for n in nodes if rk[n] == r]) for r in sorted(set(rk.values())))
    doc = Doc()
    doc.box(h(spec.get("title", "Flow")), 40, 15, 600, 30, "text;html=1;fontSize=16;fontStyle=1;")
    ids = {}
    for r, col in cols.items():
        for i, n in enumerate(col):
            fill, stroke = COL["K"]
            dash = "dashed=1;" if n in external else ""
            ids[n] = doc.box(h(labels[n]), 40 + r * FXS, 60 + i * FYS, FW, FH,
                             f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};{dash}")
    for a, b, label, kind in edges:
        doc.edge(ids[a], ids[b], f"strokeColor=#666666;labelBackgroundColor=#ffffff;fontSize=11;{EDGE_KIND[kind]}", label=h(label))
    if any(kind != "call" for _, _, _, kind in edges):
        ly = 60 + max(len(c) for c in cols.values()) * FYS + 10
        doc.box("solid = call, dashed = data, dotted = event", 40, ly, 320, 24, "text;html=1;fontSize=11;fontColor=#666666;")
    doc.write(out, "Flow")


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
            spec = json.load(f)
    except FileNotFoundError:
        fail(f"spec not found: {path}")
    except json.JSONDecodeError as e:
        fail(f"spec is not valid JSON: {path}: {e}")
    if not isinstance(spec, dict):
        fail(f"spec must be a JSON object: {path}")
    return spec


def main(argv):
    if sys.version_info < (3, 8):
        fail("needs Python 3.8 or newer")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    png = "--png" in argv
    argv = [a for a in argv if a != "--png"]
    opts = {"-o": None, "--highlight": None}
    for flag in list(opts):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                fail(f"{flag} needs a value")
            opts[flag] = argv[i + 1]
            del argv[i:i + 2]
    if not argv:
        fail("missing command; run with --help")
    out, cmd = opts["-o"], argv[0]
    if cmd not in ("system", "components", "sequence", "flow"):
        fail(f"unknown command {cmd!r}; run with --help")
    if len(argv) != 2 or not out:
        fail(f"usage: {cmd} <spec.json> -o out.drawio{' [--highlight <id>]' if cmd == 'system' else ''} [--png]")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    spec = load_spec(argv[1])
    if cmd == "sequence":
        sequence_diagram(spec, out)
    elif cmd == "flow":
        flow_diagram(spec, out)
    else:
        graph_diagram(spec, out, opts["--highlight"] if cmd == "system" else None, "System" if cmd == "system" else "Components")
    print(f"wrote {out}", file=sys.stderr)
    if png:
        p = export_png(out)
        if p:
            print(f"wrote {p}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
