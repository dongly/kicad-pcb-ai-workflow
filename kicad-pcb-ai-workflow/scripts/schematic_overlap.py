#!/usr/bin/env python3
"""Read-only schematic overlap and label-placement screen.

Graphics and text are checked separately because the evidence differs.
KiCad ERC does not report either class; 0/0 ERC says nothing about them.

  1 SHEET_FRAME   sheet boxes overlapping each other or leaving the paper   (file)
  2 OUT_OF_FRAME  items outside the paper                                     (file)
  3 TEXT_PAIR     overlapping text, incl. label/label, ref/value, label/pin (kicad-cli SVG)
  4 SYMBOL_PAIR   component outlines overlapping, wire crossing a component  (Konnect layout JSON)
  5 WIRE_TEXT     wire running through text                                   (file + SVG)
  6 LABEL         label not on a wire interior / text past the wire end      (file + SVG)

Blind spot: the SVG text record carries text only. Symbol outlines come only
from --layout (Konnect get_schematic_layout). Review page renders after this.
"""
import argparse
import json
import math
import re
import struct
import subprocess
import zlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from engineering_gate import local
from npi_common import children, child, value, xy
from schematic_io import blocking, sheets
from schematic_style import PAPER_MM
from schematic_svg_strokes import check_strokes, svg_strokes

LABEL_KINDS = ('label', 'global_label', 'hierarchical_label')
# KiCad stroke font advance per character as a fraction of text height. Only
# used when the SVG record for a label is missing; SVG textLength is exact.
CHAR_FACTOR = 0.8
TEXT_MIN = 0.15      # mm on both axes before a text pair counts as overlapped
WIRE_TEXT_MIN = 0.3  # mm of wire inside a text box
WIRE_SYMBOL_MIN = 0.5
PAIR_MIN = 0.15
SVGNS = '{http://www.w3.org/2000/svg}'


def _paper(tree):
    paper = child(tree, 'paper', [])
    name = paper[1] if len(paper) > 1 else None
    nominal = PAPER_MM.get(name)
    if nominal is None:
        return name, None
    return name, (nominal[1], nominal[0]) if 'portrait' in paper else nominal


def wire_segments(tree, buses=False):
    segments = []
    for wire in children(tree, 'wire') + (children(tree, 'bus') if buses else []):
        pts = [(float(v[1]), float(v[2])) for v in children(child(wire, 'pts', []), 'xy')]
        segments += list(zip(pts, pts[1:]))
    return segments


def sheet_rects(tree):
    result = []
    for sheet in children(tree, 'sheet'):
        props = {p[1]: p[2] for p in children(sheet, 'property') if len(p) > 2}
        x, y = xy(sheet)
        size = child(sheet, 'size')
        w, h = (float(size[1]), float(size[2])) if size else (0.0, 0.0)
        result.append((str(props.get('Sheetname', '')), (x, y, x + w, y + h)))
    return result


def runs(segments):
    """Merge collinear touching/overlapping segments into axis intervals."""
    horizontal, vertical = {}, {}
    for (x1, y1), (x2, y2) in segments:
        if abs(y1 - y2) < 1e-6:
            horizontal.setdefault(round(y1, 4), []).append((min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) < 1e-6:
            vertical.setdefault(round(x1, 4), []).append((min(y1, y2), max(y1, y2)))
    def merge(items):
        out = []
        for lo, hi in sorted(items):
            if out and lo <= out[-1][1] + 1e-6:
                out[-1][1] = max(out[-1][1], hi)
            else:
                out.append([lo, hi])
        return out
    return {k: merge(v) for k, v in horizontal.items()}, {k: merge(v) for k, v in vertical.items()}


def run_at(x, y, merged, tol=1e-3):
    """Return (lo, hi, axis) of the interval strictly containing (x, y)."""
    for axis, table, fixed, moving in ((0, merged[0], y, x), (1, merged[1], x, y)):
        for key, intervals in table.items():
            if abs(fixed - key) > tol:
                continue
            for lo, hi in intervals:
                if lo - tol <= moving <= hi + tol:
                    return lo, hi, axis
    return None


def labels(tree):
    result = []
    for kind in LABEL_KINDS:
        for label in children(tree, kind):
            at = child(label, 'at', [])
            x, y = xy(label)
            angle = float(at[3]) if len(at) > 3 else 0.0
            font = child(child(label, 'effects', []), 'font', [])
            size = child(font, 'size')
            height = float(size[1]) if size else 1.27
            effects = child(label, 'effects', [])
            justify = [str(j) for j in children(effects, 'justify')] if effects is not None else []
            justify = justify[0] if justify else []
            result.append({'kind': kind, 'text': str(label[1]) if len(label) > 1 else '', 'x': x, 'y': y,
                           'angle': angle % 360, 'height': height, 'justify_right': 'right' in justify, 'uuid': str(value(label, 'uuid'))})
    return result


# ---- SVG text records -------------------------------------------------------
def _rotate(point, angle, cx, cy):
    if not angle:
        return point
    a = math.radians(angle)
    dx, dy = point[0] - cx, point[1] - cy
    return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a))


def _text_box(x, y, length, size, anchor, angle, cx, cy):
    x0 = x - {'start': 0.0, 'middle': length / 2, 'end': length}[anchor]
    corners = [(x0, y - 0.8 * size), (x0 + length, y - 0.8 * size), (x0 + length, y + 0.25 * size), (x0, y + 0.25 * size)]
    corners = [_rotate(c, angle, cx, cy) for c in corners]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def svg_texts(path):
    """Every invisible <text> record of a kicad-cli SVG as an axis-aligned box in sheet mm."""
    root = ET.parse(str(path)).getroot()
    result = []
    def walk(node, angle, cx, cy):
        transform = node.get('transform', '')
        m = re.match(r'\s*rotate\(\s*(-?[\d.]+)(?:\s+(-?[\d.]+)\s+(-?[\d.]+))?', transform)
        if m:
            angle, cx, cy = float(m.group(1)), float(m.group(2) or 0), float(m.group(3) or 0)
        if node.tag == SVGNS + 'text' and node.get('opacity') == '0':
            result.append({'text': ''.join(node.itertext()), 'x': float(node.get('x')), 'y': float(node.get('y')),
                           'length': float(node.get('textLength', 0)), 'size': float(node.get('font-size', 0)),
                           'anchor': node.get('text-anchor', 'start'), 'angle': angle,
                           'box': _text_box(float(node.get('x')), float(node.get('y')), float(node.get('textLength', 0)),
                                            float(node.get('font-size', 0)), node.get('text-anchor', 'start'), angle, cx, cy)})
        for sub in node:
            walk(sub, angle, cx, cy)
    walk(root, 0.0, 0.0, 0.0)
    # kicad-cli writes some text (symbol fields) more than once with an
    # identical record. Same place, extent and angle is one drawn text.
    unique = {}
    for t in result:
        key = (round(t['x'], 4), round(t['y'], 4), round(t['length'], 4), t['anchor'], round(t['angle'], 3), t['text'])
        unique.setdefault(key, t)
    return list(unique.values())


def export_svg(cli, top, out):
    subprocess.run([cli, 'sch', 'export', 'svg', '--exclude-drawing-sheet', '--no-background-color', '-o', str(out), str(top)],
                   check=True, capture_output=True)


def svg_map(root, top_stem, trees, folder):
    """Map root-relative sheet path -> exported SVG path. Names follow KiCad: <stem>-<Sheetname>.svg."""
    found = {p.name: p for p in Path(folder).glob('*.svg')}
    result = {}
    for name, tree in trees.items():
        if Path(name).stem == top_stem and top_stem + '.svg' in found:
            result[name] = found[top_stem + '.svg']
        for sheet in children(tree, 'sheet'):
            props = {p[1]: p[2] for p in children(sheet, 'property') if len(p) > 2}
            sub = (local(root, name).parent / (props.get('Sheetfile') or props.get('Sheet file'))).resolve().relative_to(root).as_posix()
            target = top_stem + '-' + str(props.get('Sheetname', '')) + '.svg'
            if sub in trees and target in found:
                result[sub] = found[target]
    return result


# ---- geometry helpers -------------------------------------------------------
def _overlap(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _positive(box):
    return box[2] - box[0], box[3] - box[1]


def inside_length(a, b, box):
    """Length of segment a-b clipped to an axis-aligned box (Liang-Barsky)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - box[0]), (dx, box[2] - a[0]), (-dy, a[1] - box[1]), (dy, box[3] - a[1])):
        if p == 0:
            if q < 0:
                return 0.0
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return 0.0
    return math.hypot(dx, dy) * (t1 - t0)


def clip_rect(box, limit):
    return (max(box[0], limit[0]), max(box[1], limit[1]), min(box[2], limit[2]), min(box[3], limit[3]))


# ---- checks -----------------------------------------------------------------
def check_frames(tree, name, findings):
    _, paper = _paper(tree)
    rects = sheet_rects(tree)
    for i, (an, a) in enumerate(rects):
        if paper and (a[0] < 0 or a[1] < 0 or a[2] > paper[0] or a[3] > paper[1]):
            findings.append(('SHEET_FRAME', name, 'Sheet "%s" leaves the paper' % an, [round(v, 3) for v in a]))
        for bn, b in rects[i + 1:]:
            ov = _overlap(a, b)
            w, h = _positive(ov)
            if w > PAIR_MIN and h > PAIR_MIN:
                findings.append(('SHEET_FRAME', name, 'Sheet "%s" overlaps sheet "%s"' % (an, bn),
                                 {'overlap_mm': [round(v, 3) for v in ov]}))


def check_out_of_frame(tree, name, findings):
    paper_name, paper = _paper(tree)
    if paper is None:
        findings.append(('OUT_OF_FRAME', name, 'Unknown paper size "%s"; cannot check' % paper_name, None))
        return
    def out(x, y):
        return x < -1e-6 or y < -1e-6 or x > paper[0] + 1e-6 or y > paper[1] + 1e-6
    for kind in ('symbol',) + LABEL_KINDS + ('text', 'text_box', 'junction', 'no_connect'):
        for obj in children(tree, kind):
            if kind == 'symbol':
                ident = str(next((p[2] for p in children(obj, 'property') if len(p) > 2 and p[1] == 'Reference'), value(obj, 'uuid')))
            else:
                ident = str(obj[1]) if len(obj) > 1 else str(value(obj, 'uuid'))
            if out(*xy(obj)):
                findings.append(('OUT_OF_FRAME', name, '%s "%s" anchor outside paper' % (kind, ident), [round(v, 3) for v in xy(obj)]))
    for wire in children(tree, 'wire'):
        for v in children(child(wire, 'pts', []), 'xy'):
            if out(float(v[1]), float(v[2])):
                findings.append(('OUT_OF_FRAME', name, 'Wire endpoint outside paper', [float(v[1]), float(v[2])]))
                break


def check_text_pairs(texts, name, findings):
    items = sorted(texts, key=lambda t: t['box'][0])
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if b['box'][0] >= a['box'][2]:
                break
            ov = _overlap(a['box'], b['box'])
            w, h = _positive(ov)
            if w > TEXT_MIN and h > TEXT_MIN:
                findings.append(('TEXT_PAIR', name, '"%s" overlaps "%s"' % (a['text'].strip(), b['text'].strip()),
                                 {'overlap_mm': [round(v, 3) for v in ov], 'a': a['text'], 'b': b['text']}))


def check_wire_text(segments, texts, name, findings):
    for t in texts:
        if not t['text'].strip():
            continue
        box = (t['box'][0] + TEXT_MIN, t['box'][1] + TEXT_MIN, t['box'][2] - TEXT_MIN, t['box'][3] - TEXT_MIN)
        if box[0] >= box[2] or box[1] >= box[3]:
            continue
        best = max((inside_length(a, b, box) for a, b in segments), default=0.0)
        if best > WIRE_TEXT_MIN:
            findings.append(('WIRE_TEXT', name, 'Wire runs through text "%s"' % t['text'].strip(),
                             {'inside_mm': round(best, 3), 'box': [round(v, 3) for v in t['box']]}))


def _layout_components(blob, where):
    items = blob.get('components') if isinstance(blob, dict) else blob
    if not isinstance(items, list):
        raise ValueError('Konnect layout JSON without components list: ' + where)
    result = []
    for c in items:
        if not isinstance(c, dict) or 'reference' not in c:
            raise ValueError('Konnect layout component without reference: ' + where)
        if isinstance(c.get('bounds'), dict):
            b = c['bounds']
            box = (float(b['x_min']), float(b['y_min']), float(b['x_max']), float(b['y_max']))
        else:
            raw = c.get('bbox_mm') or c.get('bounds')
            box = tuple(float(v) for v in raw)
        result.append((str(c['reference']), box, str(c.get('lib_id', ''))))
    return result


def check_symbols(components, segments, name, findings):
    order = sorted(components, key=lambda c: c[1][0])
    for i, (ra, a, la) in enumerate(order):
        for rb, b, lb in order[i + 1:]:
            if b[0] >= a[2]:
                break
            ov = _overlap(a, b)
            w, h = _positive(ov)
            if w > PAIR_MIN and h > PAIR_MIN:
                findings.append(('SYMBOL_PAIR', name, '%s overlaps %s' % (ra, rb), {'overlap_mm': [round(v, 3) for v in ov]}))
    for ref, box, lib in components:
        inner = (box[0] + TEXT_MIN, box[1] + TEXT_MIN, box[2] - TEXT_MIN, box[3] - TEXT_MIN)
        if inner[0] >= inner[2] or inner[1] >= inner[3]:
            continue
        best = max((inside_length(p, q, inner) for p, q in segments), default=0.0)
        if best > WIRE_SYMBOL_MIN:
            findings.append(('SYMBOL_PAIR', name, 'Wire crosses %s (%s)' % (ref, lib), {'inside_mm': round(best, 3)}))


def check_labels(page_labels, segments, texts, name, findings, min_entry):
    merged = runs(segments)
    for lab in page_labels:
        where = '%s "%s" @(%g,%g)' % (lab['kind'], lab['text'], lab['x'], lab['y'])
        hit = run_at(lab['x'], lab['y'], merged)
        if hit is None:
            findings.append(('LABEL', name, where + ' is not on a wire (directly on a pin or floating)',
                             {'rule': 'LABEL.OFF_WIRE', 'uuid': lab['uuid']}))
            continue
        lo, hi, axis = hit
        # Exact text length from the SVG record when present, else a font estimate.
        record = next((t for t in texts if t['text'] == lab['text'] and math.hypot(t['x'] - lab['x'], t['y'] - lab['y']) < 3.0), None)
        length = record['length'] if record else len(lab['text']) * lab['height'] * CHAR_FACTOR
        if lab['kind'] == 'label':
            # Net labels: the wire must continue past the anchor on both sides.
            if min(abs(lab['x'] - lo) if axis == 0 else abs(lab['y'] - lo), abs(lab['x'] - hi) if axis == 0 else abs(lab['y'] - hi)) <= 1e-3:
                findings.append(('LABEL', name, where + ' sits at a wire end; move it into the wire',
                                 {'rule': 'LABEL.WIRE_END', 'uuid': lab['uuid']}))
            angle = int(round(lab['angle'])) % 360
            # Measured on kicad-cli SVG: the baseline runs right for 0/180 and
            # upward (toward smaller y) for 90/270; justify right makes the text
            # end at the anchor, so it extends the opposite way.
            if angle in (90, 270):
                axis, sign = 1, -1
            else:
                axis, sign = 0, 1
            if lab['justify_right']:
                sign = -sign
            pos = lab['x'] if axis == 0 else lab['y']
            ahead = (hi - pos) if sign == 1 else (pos - lo)
            if ahead + 1e-6 < length + 0.25:
                findings.append(('LABEL', name, where + ': text ends past the wire end (text %.2f mm, wire ahead %.2f mm)' % (length, ahead),
                                 {'rule': 'LABEL.TEXT_PAST_WIRE', 'uuid': lab['uuid']}))
        else:
            # Global/hierarchical labels connect at the anchor, so a wire may end
            # there; the body extends along the text direction, and the entry wire
            # must come from the opposite side with visible length.
            entry = {'0': (lab['x'] - lo, 0), '180': (hi - lab['x'], 0), '90': (hi - lab['y'], 1), '270': (lab['y'] - lo, 1)}
            key = str(int(round(lab['angle'])) % 360)
            if key in entry and axis == entry[key][1] and entry[key][0] + 1e-6 < min_entry:
                findings.append(('LABEL', name, where + ': entry wire shorter than %.2f mm before the label' % min_entry,
                                 {'rule': 'LABEL.ENTRY_SHORT', 'uuid': lab['uuid']}))


def write_png(path, bitmap):
    """Write a pypdfium2 bitmap as PNG without Pillow (stdlib zlib only)."""
    width, height = bitmap.width, bitmap.height
    channels, stride = bitmap.n_channels, bitmap.stride
    raw = bytes(bitmap.buffer)
    rows = bytearray()
    for y in range(height):
        row = raw[y * stride:y * stride + width * channels]
        if channels >= 3 and 'BGR' in str(bitmap.format):      # PDFium natives are BGR/BGRx
            row = bytearray(row)
            row[0::channels], row[2::channels] = row[2::channels], row[0::channels]
        if channels == 4:
            row = bytes(row[0::channels]) + bytes(row[1::channels]) + bytes(row[2::channels])   # drop alpha
            channels_row = 3
        else:
            channels_row = channels
        rows += b'\x00' + bytes(row)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    color = {1: 0, 3: 2}.get(channels_row)
    if color is None:
        raise ValueError('Unsupported PDFium bitmap format %s' % bitmap.format)
    (path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, color, 0, 0, 0))
                       + chunk(b'IDAT', zlib.compress(bytes(rows), 6)) + chunk(b'IEND', b''))


def render_png(pdf, out_dir, dpi):
    """Rasterize every page of a schematic PDF to PNG with pypdfium2."""
    try:
        import pypdfium2
    except ImportError as exc:
        raise RuntimeError('pypdfium2 is required for --png: python -m pip install pypdfium2') from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    stem = pdf.stem
    document = pypdfium2.PdfDocument(str(pdf))
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=dpi / 72.0)
            target = out_dir / ('%s-page%d.png' % (stem, index + 1))
            write_png(target, bitmap)
            written.append(target.name)
    finally:
        document.close()
    return written


def export_pdf(cli, top, folder):
    target = folder / (top.stem + '.pdf')
    subprocess.run([cli, 'sch', 'export', 'pdf', '-o', str(target), str(top)], check=True, capture_output=True)
    return target


def run(root, top, cli, layouts, min_entry, png_dir=None, dpi=200):
    root = Path(root).resolve()
    trees = sheets(root, top)
    findings, summary, inputs = [], {}, {}
    rendered = []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            export_svg(cli, local(root, top), Path(tmp))
            svgs = svg_map(root, Path(top).stem, trees, Path(tmp))
            if png_dir is not None:
                rendered = render_png(export_pdf(cli, local(root, top), Path(tmp)), png_dir, dpi)
        except (OSError, subprocess.CalledProcessError) as exc:
            svgs = {}
            findings.append(('SVG_EXPORT', top, 'kicad-cli SVG export failed: %s' % getattr(exc, 'stderr', exc), None))
        for name, tree in trees.items():
            segments = wire_segments(tree)
            page_labels = labels(tree)
            inputs[name] = len(segments)
            check_frames(tree, name, findings)
            check_out_of_frame(tree, name, findings)
            texts = svg_texts(svgs[name]) if name in svgs else []
            if name not in svgs and svgs:
                findings.append(('SVG_MISSING', name, 'No exported SVG matched this sheet; text checks skipped', None))
            check_text_pairs(texts, name, findings)
            # Exact ink test: glyph strokes against wires, outlines and other glyphs.
            check_strokes(svg_strokes(svgs[name], wire_segments(tree, buses=True),
                                     [(l['x'], l['y']) for l in page_labels if l['kind'] != 'label']), name, findings)
            check_wire_text(segments, texts, name, findings)
            check_labels(page_labels, wire_segments(tree, buses=True), texts, name, findings, min_entry)
            if name in layouts:
                check_symbols(_layout_components(json.loads(local(root, layouts[name]).read_text(encoding='utf-8-sig')), layouts[name]), segments, name, findings)
            summary[name] = {'wires': len(segments), 'labels': len(page_labels), 'svg_texts': len(texts),
                             'layout': 'checked' if name in layouts else 'not_provided'}
    counts = {}
    for section in sorted({f[0] for f in findings}):
        counts[section] = sum(1 for f in findings if f[0] == section)
    return {'status': 'OVERLAPS_FOUND' if findings else 'NO_OVERLAP_DETECTED',
            'scope': 'schematic_graphic_and_text_overlap_only', 'production_authorized': False,
            'counts': counts, 'pages': summary, 'findings': findings, 'png': rendered, 'png_dpi': dpi if rendered else None,
            'sections': ['SHEET_FRAME', 'OUT_OF_FRAME', 'TEXT_PAIR', 'SYMBOL_PAIR', 'WIRE_TEXT', 'LABEL', 'STROKE'],
            'manual_remaining': ['Symbol outlines need --layout (Konnect get_schematic_layout) per sheet',
                                 'Readability (crowding, confusing routing) is not judged by any script; look at the PNG of every page for that']}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('project'); p.add_argument('--schematic', required=True); p.add_argument('--kicad-cli', default='kicad-cli')
    p.add_argument('--layout', action='append', default=[], metavar='SHEET=JSON', help='Konnect get_schematic_layout result for SHEET (root-relative path)')
    p.add_argument('--min-entry', type=float, default=2.54, help='Required wire length entering a global/hierarchical label (mm)')
    p.add_argument('--output-dir', help='New directory for overlap-report.json (required for --png)')
    p.add_argument('--png', action='store_true', help='Also export a PDF with kicad-cli and rasterize every page to PNG in --output-dir (needs pypdfium2) for visual review')
    p.add_argument('--dpi', type=int, default=200, help='PNG resolution for --png (default 200)')
    a = p.parse_args()
    try:
        layouts = {}
        for item in a.layout:
            sheet, _, path = item.partition('=')
            if not sheet or not path:
                raise ValueError('--layout expects SHEET=JSON')
            layouts[sheet.replace('\\', '/')] = path
        if a.png and not a.output_dir:
            raise ValueError('--png requires --output-dir')
        out = None
        if a.output_dir:
            out = Path(a.output_dir)
            if out.exists():
                raise ValueError('New report directory required')
            out.mkdir(parents=True)
        r = run(a.project, a.schematic, a.kicad_cli, layouts, a.min_entry, out if a.png else None, a.dpi)
        if out:
            (out / 'overlap-report.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 2 if r['status'] == 'OVERLAPS_FOUND' else 0
    except Exception as e:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(e), 'production_authorized': False, 'findings': [blocking('INPUT.CONTRACT', e)]}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    import sys
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
