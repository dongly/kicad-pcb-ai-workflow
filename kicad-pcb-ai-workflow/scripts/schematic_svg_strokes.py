"""Exact stroke-level overlap screen for an exported KiCad schematic SVG.

`kicad-cli sch export svg` is pure vector output: every wire, symbol outline,
junction and glyph stroke is a path.  This module flattens those paths to line
segments and reports strokes that actually touch, which is what a person looks
for when reviewing a page render.  It sees text over wires AND text over symbol
outlines, so it does not need component bounds.

What it still cannot do: judge readability (crowding, confusing routing), and
it cannot name the component an outline belongs to (symbol outlines are not
labelled in the SVG), so findings carry a sheet coordinate instead.
"""
import math
import re
import xml.etree.ElementTree as ET

_NUMBER = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
_COMMAND = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)')
_ARC = 8       # segments per elliptical arc
_CELL = 2.0            # spatial hash cell in mm
_TOUCH = 0.02          # mm: endpoints this close count as touching
_ENDPOINT = 0.05       # mm: "the wire ends here" tolerance
_PORT = 0.35           # mm: a stroke starting this close to a label anchor is its outline


def _matrix(angle, cx, cy):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return (c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy)


def _apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _multiply(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
            a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def _parse_transform(text):
    """2x3 matrix for the translate/scale/rotate forms kicad-cli writes."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', text or ''):
        v = [float(n) for n in _NUMBER.findall(args)]
        if name == 'translate' and len(v) >= 2:
            t = (1.0, 0.0, 0.0, 1.0, v[0], v[1])
        elif name == 'scale' and len(v) >= 2:
            t = (v[0], 0.0, 0.0, v[1], 0.0, 0.0)
        elif name == 'rotate' and len(v) >= 3:
            t = _matrix(v[0], v[1], v[2])
        elif name == 'rotate' and len(v) == 1:
            t = _matrix(v[0], 0.0, 0.0)
        elif name == 'matrix' and len(v) == 6:
            t = tuple(v)
        else:
            continue
        m = _multiply(m, t)
    return m


def _arc(current, rx, ry, rotation, large, sweep, end, steps=_ARC):
    """Endpoints of an SVG elliptical arc (SVG F.6.5), as segments from current."""
    x0, y0 = current
    x1, y1 = end
    if (abs(x0 - x1) < 1e-12 and abs(y0 - y1) < 1e-12) or (rx == 0 and ry == 0):
        return [(end, end)]
    phi = math.radians(rotation)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x0 - x1) / 2, (y0 - y1) / 2
    x1p, y1p = cos_p * dx2 + sin_p * dy2, -sin_p * dx2 + cos_p * dy2
    rx, ry = abs(rx), abs(ry)
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2 if rx and ry else 1e30
    if lam > 1:
        rx, ry = math.sqrt(lam) * rx, math.sqrt(lam) * ry
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    coef = -coef if large == sweep else coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx, cy = cos_p * cxp - sin_p * cyp + (x0 + x1) / 2, sin_p * cxp + cos_p * cyp + (y0 + y1) / 2
    def angle(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    theta = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi
    pts = [(cx + rx * math.cos(theta + delta * i / steps) * cos_p - ry * math.sin(theta + delta * i / steps) * sin_p,
            cy + rx * math.cos(theta + delta * i / steps) * sin_p + ry * math.sin(theta + delta * i / steps) * cos_p)
           for i in range(1, steps)] + [end]
    return list(zip([current] + pts[:-1], pts))


def _bez(p0, p1, p2, p3, steps=8):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def path_segments(d, m):
    """Flatten one SVG path (M L H V C S Q T Z, absolute and relative) to segments."""
    segments, start, cur, ctrl = [], None, None, None
    for cmd, body in _COMMAND.findall(d or ''):
        rel = cmd.islower()
        k = cmd.lower()
        if k == 'z':
            if cur is not None and start is not None and cur != start:
                segments.append((_apply(m, *cur), _apply(m, *start)))
            cur, ctrl = start, None
            continue
        n = [float(v) for v in _NUMBER.findall(body)]
        first, i = True, 0
        while i < len(n):
            ox, oy = cur if cur is not None else (0.0, 0.0)
            def pt(dx, dy):
                return (ox + dx, oy + dy) if rel else (dx, dy)
            if k == 'm' and first:
                cur, start, ctrl = pt(n[i], n[i + 1]), None, None
            elif k in ('m', 'l'):
                nxt = pt(n[i], n[i + 1])
                segments.append((_apply(m, *cur), _apply(m, *nxt)))
                cur, ctrl = nxt, None
            elif k == 'h':
                nxt = (ox + n[i], oy) if rel else (n[i], oy)
                segments.append((_apply(m, *cur), _apply(m, *nxt)))
                cur, ctrl = nxt, None
                i += 1
                first = False
                continue
            elif k == 'v':
                nxt = (ox, oy + n[i]) if rel else (ox, n[i])
                segments.append((_apply(m, *cur), _apply(m, *nxt)))
                cur, ctrl = nxt, None
                i += 1
                first = False
                continue
            elif k in ('c', 's'):
                if k == 'c':
                    p1 = pt(n[i], n[i + 1])
                    i += 2
                else:
                    p1 = (2 * ox - ctrl[0], 2 * oy - ctrl[1]) if ctrl else cur
                p2 = pt(n[i], n[i + 1])
                p3 = pt(n[i + 2], n[i + 3])
                pts = _bez(cur, p1, p2, p3)
                segments += [(_apply(m, *a), _apply(m, *b)) for a, b in zip([cur] + pts[:-1], pts)]
                cur, ctrl = p3, p2
                i += 2
            elif k in ('q', 't'):
                if k == 'q':
                    p1 = pt(n[i], n[i + 1])
                    i += 2
                else:
                    p1 = (2 * ox - ctrl[0], 2 * oy - ctrl[1]) if ctrl else cur
                p3 = pt(n[i], n[i + 1])
                pts = _bez(cur, p1, p3, p3)
                segments += [(_apply(m, *a), _apply(m, *b)) for a, b in zip([cur] + pts[:-1], pts)]
                cur, ctrl = p3, p1
            elif k == 'a':
                end = pt(n[i + 5], n[i + 6])
                segments += [(_apply(m, *a), _apply(m, *b)) for a, b in _arc(cur, n[i], n[i + 1], n[i + 2], n[i + 3], n[i + 4], end)]
                cur, ctrl = end, None
                i += 6
            i += 2
            first = False
    return [s for s in segments if math.hypot(s[1][0] - s[0][0], s[1][1] - s[0][1]) > 1e-6]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _point_on(p, a, b, eps):
    ab = math.hypot(b[0] - a[0], b[1] - a[1])
    if ab < 1e-9:
        return math.hypot(p[0] - a[0], p[1] - a[1]) <= eps
    t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (ab * ab)))
    return math.hypot(p[0] - a[0] - t * (b[0] - a[0]), p[1] - a[1] - t * (b[1] - a[1])) <= eps


def touch(a, b, c, d, eps=_TOUCH):
    """A common point of segments ab and cd if they touch, else None."""
    d1, d2, d3, d4 = _cross(c, d, a), _cross(c, d, b), _cross(a, b, c), _cross(a, b, d)
    tiny = 1e-6 * max(1.0, math.hypot(c[0] - d[0], c[1] - d[1]), math.hypot(a[0] - b[0], a[1] - b[1]))
    d1, d2, d3, d4 = [v if abs(v) > tiny else 0.0 for v in (d1, d2, d3, d4)]   # kill float noise
    if d1 and d2 and d3 and d4 and (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0):
        t = d3 / (d3 - d4)
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    for p, s0, s1 in ((a, c, d), (b, c, d), (c, a, b), (d, a, b)):
        if _point_on(p, s0, s1, eps):
            return p
    return None


def _prop(style, key):
    m = re.search(r'(?:^|;)\s*%s\s*:\s*([^;]+)' % key, style or '')
    return m.group(1).strip() if m else ''


def _shape_segments(node, m, shape):
    def num(name):
        try:
            return float(node.get(name, 0))
        except ValueError:
            return 0.0
    closed = False
    if shape == 'rect':
        x, y, w, h = num('x'), num('y'), num('width'), num('height')
        pts, closed = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True
    elif shape == 'line':
        pts = [(num('x1'), num('y1')), (num('x2'), num('y2'))]
    elif shape in ('circle', 'ellipse'):
        cx, cy = num('cx'), num('cy')
        rx = num('rx') or num('r')
        ry = num('ry') or num('r')
        pts, closed = [(cx + rx * math.cos(2 * math.pi * i / 72), cy + ry * math.sin(2 * math.pi * i / 72)) for i in range(72)], True
    else:
        nums = [float(v) for v in _NUMBER.findall(node.get('points') or '')]
        pts, closed = list(zip(nums[0::2], nums[1::2])), shape == 'polygon'
    pts = [_apply(m, *p) for p in pts]
    if closed and pts:
        pts = pts + [pts[0]]
    return list(zip(pts, pts[1:]))


def _key_point(p):
    return (round(p[0], 2), round(p[1], 2))


def svg_strokes(path, wires=(), ports=()):
    """Flatten one exported SVG page to strokes.

    wires: wire/bus segments of the same sheet from the .kicad_sch.  A stroke
    whose endpoints match one is kind 'wire'; a non-text stroke belonging to the
    pointed outline of a global/hierarchical label is kind 'port'; any other
    non-text stroke is kind 'symbol'.  Text glyph strokes are kind 'text'.
    Returns [{'kind','text','a','b','key'}] where 'key' names the drawn object.
    """
    ports = [(float(x), float(y)) for x, y in ports or ()]
    wire_set = set()
    for wa, wb in wires or ():
        wire_set.add((_key_point(wa), _key_point(wb)))
        wire_set.add((_key_point(wb), _key_point(wa)))
    strokes, stack, anchor, seen, counter = [], [], None, set(), 0
    for event, node in ET.iterparse(str(path), events=('start', 'end')):
        tag = node.tag.rsplit('}', 1)[-1]
        if event == 'start':
            if tag == 'g':
                style = _prop(node.get('style'), 'fill')
                stack.append({'m': _parse_transform(node.get('transform')),
                              'text': node.get('class') == 'stroked-text',
                              'group_fill': style not in ('', 'none'),
                              })
            elif tag == 'text':
                anchor = (float(node.get('x', 0)), float(node.get('y', 0)), (node.text or '').strip())
            continue
        if tag == 'g':
            if stack:
                stack.pop()
            continue
        if tag not in ('path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon'):
            continue
        m = stack[-1]['m'] if stack else (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        own = node.get('style', '')
        filled = _prop(own, 'fill') not in ('', 'none') or (stack and stack[-1]['group_fill'])
        if filled:
            continue                       # filled area: its edge is drawn again as an outline
        segs = path_segments(node.get('d', ''), m) if tag == 'path' else _shape_segments(node, m, tag)
        counter += 1
        if stack and stack[-1]['text']:
            key = ('text', anchor[2] if anchor else '', round(anchor[0], 3) if anchor else 0.0, round(anchor[1], 3) if anchor else 0.0)
            if key in seen:
                continue                     # kicad-cli writes some field texts twice
            seen.add(key)
            strokes += [{'kind': 'text', 'text': key[1], 'a': a, 'b': b, 'key': key} for a, b in segs]
        else:
            if not segs:
                continue
            is_port = any(math.hypot(px - q[0], py - q[1]) <= _PORT for px, py in ports for a, b in segs for q in (a, b))
            for a, b in segs:
                if (_key_point(a), _key_point(b)) in seen:
                    continue                     # same outline drawn twice (sheet body + frame)
                seen.add((_key_point(a), _key_point(b)))
                kind = 'wire' if ((_key_point(a), _key_point(b)) in wire_set or (_key_point(b), _key_point(a)) in wire_set) \
                    else 'port' if is_port else 'symbol'
                strokes.append({'kind': kind, 'text': '', 'a': a, 'b': b, 'key': ('line', counter)})
    return strokes


def _cells(a, b):
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    for cx in range(int(math.floor(x0 / _CELL)), int(math.floor(x1 / _CELL)) + 1):
        for cy in range(int(math.floor(y0 / _CELL)), int(math.floor(y1 / _CELL)) + 1):
            yield cx, cy


def _near(p, q, eps=_ENDPOINT):
    return math.hypot(p[0] - q[0], p[1] - q[1]) <= eps


def _index(items, grid):
    for i, s in enumerate(items):
        for cell in _cells(s['a'], s['b']):
            grid.setdefault(cell, []).append(i)


def check_strokes(strokes, name, findings, cluster=1.0):
    """Report strokes that touch: one finding per text (per rule) and per place a wire crosses an outline.

    A wire that merely ends on an outline is not reported: that is how a pin
    connection looks in the SVG (pin line, bubble or arrow drawn as outline),
    and the file-level pin positions are not available here.
    """
    grid, texts = {}, [s for s in strokes if s['kind'] == 'text' and s['text'].strip()]
    line_items = [s for s in strokes if s['kind'] != 'text']
    _index(line_items, grid)
    tgrid = {}
    _index(texts, tgrid)

    def cells_of(s):
        return {(cx + dx, cy + dy) for cx, cy in _cells(s['a'], s['b']) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}

    # --- text against wires and symbol outlines ---------------------------------
    seen_text = {}
    for g in texts:
        for cell in cells_of(g):
            for i in grid.get(cell, ()):
                line = line_items[i]
                p = touch(g['a'], g['b'], line['a'], line['b'])
                if p is None:
                    continue
                seen_text.setdefault((g['key'], line['kind']), p)
    for (key, kind), p in sorted(seen_text.items(), key=lambda kv: (kv[0][0][1], kv[1])):
        findings.append(('STROKE', name, 'text "%s" is crossed by a %s stroke at (%.2f, %.2f)' % (key[1], kind, p[0], p[1]),
                         {'rule': 'STROKE.TEXT_LINE', 'text': key[1], 'by': kind, 'at': [round(p[0], 2), round(p[1], 2)]}))

    # --- glyph against glyph -----------------------------------------------------
    seen_pair = set()
    for g in texts:
        for cell in cells_of(g):
            for j in tgrid.get(cell, ()):
                other = texts[j]
                if other['key'] <= g['key']:
                    continue
                p = touch(g['a'], g['b'], other['a'], other['b'])
                if p is not None and (g['key'], other['key']) not in seen_pair:
                    seen_pair.add((g['key'], other['key']))
                    findings.append(('STROKE', name, 'text "%s" touches text "%s" at (%.2f, %.2f)' % (g['text'], other['text'], p[0], p[1]),
                                     {'rule': 'STROKE.TEXT_TEXT', 'a': g['text'], 'b': other['text'], 'at': [round(p[0], 2), round(p[1], 2)]}))

    # --- wire against symbol outline ---------------------------------------------
    reported = set()
    for w in (s for s in line_items if s['kind'] == 'wire'):
        for cell in _cells(w['a'], w['b']):
            for i in grid.get(cell, ()):
                line = line_items[i]
                if line['kind'] != 'symbol':
                    continue
                p = touch(w['a'], w['b'], line['a'], line['b'])
                if p is None:
                    continue
                ends_wire = _near(p, w['a']) or _near(p, w['b'])
                if ends_wire:
                    continue                     # wire ends on a pin bubble/arrow or pin end: a connection, ERC's job
                ident = (round(p[0] / cluster), round(p[1] / cluster))
                if ident in reported:
                    continue
                reported.add(ident)
                findings.append(('STROKE', name, 'wire crosses a symbol outline at (%.2f, %.2f)' % p,
                                 {'rule': 'STROKE.WIRE_SYMBOL', 'mode': 'crossing', 'at': [round(p[0], 2), round(p[1], 2)]}))
