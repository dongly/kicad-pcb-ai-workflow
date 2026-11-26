# Schematic Composition: Title-Block Clearance, Power Symbols, and Adaptive Sheets

This is the machine-enforced extension of [topology-first rules](schematic-ai-layout-rules.md) and [schematic style](schematic-style.md). The current `schematic_style.py` checks **declared, current-file-bound geometry**, native power symbol usage, and the actual sheet hierarchy. It also provides a **read-only preflight page recommendation**. It is **not** a complete automatic symbol/label router, rendered text geometry extractor, title-block parser, or general-purpose KiCad layout optimizer. No check replaces native XML/ERC or the G1 human visual review.

## Mandatory order for newly authored schematics

1. Derive the intended component/pin/net graph independently from current device cards and the product interface contract. Check supply domain identity, NC and variants before placing symbols.
2. Plan functional modules and estimate rendered widths/heights, text, wiring corridors and title-block/notes reservations. Call the read-only page preflight (`--plan-input`). **It recommends hierarchical root plus functional child sheets by default** whenever there is more than one module (or density/link limits are exceeded); **single with module frames** is only returned for a one-module design or an explicit `prefer_hierarchy=false`. The decision is a recommendation, not a command to modify the schematic.
3. Before placing any symbols, reserve page border, title block and documentation regions from the **current KiCad worksheet**, not hard-coded screen pixel rectangles. For custom `.kicad_wks`, use actual worksheet geometry and a page render. A top-right coordinate in a screenshot is not a reliable KiCad millimeter coordinate.
4. Place by true pin topology and signal flow, then use short orthogonal local wires. **Every power and ground/return net is drawn with native KiCad `power:` library symbols — never with a global label (nor any other label).** Preserve `VIN_RAW` versus `VIN`, switched rails, PGND, AGND and separate power domains as distinct power symbols. Never equate a `PWR_FLAG` with a positive or ground net symbol. Use project-scoped sheet pins and hierarchical labels for **every** non-power inter-sheet interface. Do not use global labels as the default cross-sheet connector: they are allowed only for a genuinely board-wide net listed in `composition.labels.allow_global_labels`, and the gate reports `LABEL_POLICY.GLOBAL` for any other.
5. Save the authoritative `01_WORKING/` schematic, export the **actual** KiCad PDF/SVG and XML netlist, and create a source-bound object-bound manifest as below. All visible fields and annotation bounds must be included; preserve its native object UUID inventory. Bind manifest and view by SHA-256 to the current schematic revision.
6. Run `schematic_style.py` with an opted-in composition policy. Any detected title block or notes overlap, missing symbol, invalid frame, missing child page, stale evidence or unsafe geometry blocks completion. The output is a **measured geometry screen requiring visual review**, never a claim of automatic full rendered geometry acceptance.
6b. Run `python scripts/schematic_overlap.py /project --schematic root.kicad_sch` once over the whole hierarchy (add `--layout SHEET=layout.json` per sheet, filled from Konnect `get_schematic_layout`, to enable the symbol-pair section). Any finding blocks: KiCad ERC does not check text or graphic overlap. Overlap itself is fully scripted (`STROKE` tests exact ink contact from the SVG); the page images are for readability only.
7. Run the existing G1 `static_review.py` path, independent native netlist/ERC, source-backed AI review and genuine engineer approval. Failed topology returns to L0; cosmetic rearrangement may not change original nets.

## Read-only sheet planning

Create a project-local JSON request (example below) with KiCad paper type, current worksheet protected rectangles in millimeters, per-module *estimated* bounding sizes, and inter-module connection count:

```json
{
  "schema_version": 1,
  "paper": "A4",
  "portrait": false,
  "protected_regions": [{"id": "title", "bbox_mm": [220, 165, 292, 207]}],
  "modules": [
    {"id": "input", "estimated_box_mm": [55, 40]},
    {"id": "controller", "estimated_box_mm": [80, 60]},
    {"id": "output", "estimated_box_mm": [60, 45]}
  ],
  "cross_module_connections": 5,
  "max_single_sheet_cross_connections": 12,
  "max_occupancy": 0.72,
  "routing_text_allowance": 1.35
}
```

Run `python scripts/schematic_style.py /project --plan-input page-plan.json`. This command **never edits or creates a KiCad project**. `recommended_mode=hierarchical` (the default when `prefer_hierarchy` is true, the default, and there is more than one module) means a root overview and real child `.kicad_sch` files **within the same KiCad project**, linked through hierarchical labels and correctly scoped sheet pins — never through global labels. `recommended_mode=single` calls for one page with explicit functional frames and is expected only for a single-module design or a recorded `prefer_hierarchy=false`. There is no fixed "N components must be a new page" rule: density and cross-module link limits can still force a split even when hierarchy was opted out. The measured visual quality and hierarchy must still be verified on the actual rendered output.

## Composition policy and evidence manifest

`schematic-style.json` can opt into the new executable checks using this **project-specific** section:

```json
{
  "schema_version": 1,
  "pages": {},
  "composition": {
    "schema_version": 1,
    "required": true,
    "geometry": {
      "file": "03_REPORTS/g1-current/geometry.json",
      "sha256": "<sha256-of-exact-manifest>",
      "evidence_file": "03_REPORTS/g1-current/current-render.svg",
      "evidence_sha256": "<sha256-of-exact-current-render>",
      "locator": "Sheet 1 / entire current rendered page"
    },
    "power": {"rails": ["+24V", "+12V", "GND"], "allow_rail_labels": []},
    "labels": {
      "schema_version": 1,
      "prefer_hierarchy": true,
      "allow_global_labels": []
    },
    "partition": {
      "mode": "auto",
      "modules": [
        {"id": "input", "page": "01_WORKING/main.kicad_sch", "frame_uuid": "<actual-polyline-uuid>"},
        {"id": "core", "page": "01_WORKING/main.kicad_sch", "frame_uuid": "<actual-polyline-uuid>"}
      ],
      "max_occupancy": 0.75
    }
  }
}
```

**Power nets use power symbols only — never labels.** All paths are relative to the project root; the list of rails must be selected from the **actual** supply graph and must be complete (every supply and ground/return net, including PGND/AGND and switched rails). Do not blindly copy `+24V` or `+12V` if those are not real power rails. Every listed rail must appear as a native `power:` symbol and must **not** be wired with a label of any kind — local, hierarchical or **global**; `allow_rail_labels` must be empty and a non-empty list is rejected. A global label on a power net is reported as `POWER_SYMBOL_POLICY.LABEL` and blocks G1. All unlisted signal and SW nets retain their normal local/hierarchical label rules. `PWR_FLAG` must be added based on ERC power-driver semantics, not as a cosmetic replacement.

**Label scope (`composition.labels`):** `prefer_hierarchy=true` with an `allow_global_labels` list is the project's declaration that hierarchy is the default and global labels are exceptions. When the section is present the gate reports `LABEL_POLICY.GLOBAL` for every `global_label` whose net is not on the allow list; the check record also lists per-sheet `global_label`/`hierarchical_label` counts and the sheet-pin count so a reviewer can see whether cross-sheet interfaces were really built as ports. Allow-list entries must be genuinely board-wide nets (a net every sheet needs that is not a power symbol); do not list a net there just to avoid adding a sheet pin. A policy without the `labels` section keeps legacy behaviour and cannot claim the screen was run.

The file `geometry.json` must contain **all reachable schematic sheets**, each with a current KiCad file SHA, true sheet dimensions, a title-block protected rectangle, any additional reserved regions and a complete inventory of the source's visible object UUIDs. Example structure:

```json
{
  "schema_version": 1,
  "pages": {
    "01_WORKING/main.kicad_sch": {
      "schematic_sha256": "<sha256-of-current-schematic>",
      "sheet_mm": [297, 210],
      "complete_object_inventory": true,
      "visible_fields_included": true,
      "protected_regions": [
        {"id": "title", "kind": "title_block", "bbox_mm": [220, 165, 292, 207]},
        {"id": "notes", "kind": "notes", "bbox_mm": [5, 166, 120, 205]}
      ],
      "objects": [
        {"uuid": "<native-symbol-uuid>", "kind": "symbol", "bbox_mm": [35, 35, 68, 58]},
        {"uuid": "<native-wire-uuid>", "kind": "wire", "bbox_mm": [71, 42, 85, 44]},
        {"uuid": "<native-frame-uuid>", "kind": "polyline", "bbox_mm": [18, 16, 130, 102]}
      ]
    }
  }
}
```

The example object inventory is **deliberately incomplete** and cannot be used as an acceptance artifact. In an actual check it must match the UUIDs of every relevant object in the current schematic, including label, text, wire and frame instances; each symbol's reported bounding box must cover visible reference/value fields, not only the graphic body. These bounds are **measurements from an actual reviewed KiCad view**, not arbitrarily generated metadata. File hashes prove consistency of submitted evidence, **not** that a reported box was measured accurately. The rendered image/PDF still requires visual review.

`schematic_style.py` returns `TITLE_BLOCK_CLEAR`, `NOTES_REGION_CLEAR`, `SHEET_BORDER_CLEAR`, `POWER_SYMBOL_POLICY.MISSING`, `POWER_SYMBOL_POLICY.LABEL`, `LABEL_POLICY.GLOBAL`, `SHEET_PARTITION_POLICY.FRAME`, `SHEET_PARTITION_POLICY.MODE`, `SHEET_PARTITION_POLICY.CAPACITY`, or `COMPOSITION.*` findings when needed. Missing evidence is never turned into a PASS. The legacy policy lacking `composition` remains readable for existing projects, but reports `NOT_CONFIGURED_LEGACY_REVIEW_REQUIRED`. New projects must provide the composition section to claim these automated screens.

## What this upgrade does not implement

- No extraction of an arbitrary custom `.kicad_wks` title block into a verified polygon or complete native font bounding boxes. **An independent geometric manifest and view are currently required.** A missing/uncertain worksheet must block automatic visual acceptance.
- No automatic generation of hierarchical sheets, native symbols, placement coordinates or wires. Konnect remains the **sole active EDA writer**; all real writes require an accepted capability and current-project validation.
- No inference that a `power:` symbol means the electrical topology is correct. Check actual KiCad exported nets and ERC; review real power-domain and regulator relationships.
- No claim that successful layout screening means visually polished schematic or approved G1. A reviewer must inspect the page and relevant details.

## Verification and upgrade compatibility

The `schematic_style.audit()` entrypoint runs under the existing G1 `static_review.prepare()` path when a schematic style policy is bound. The static review packet freezes the composition policy, geometry manifest and rendered view with hashes in its evidence baseline. New project policies opt into full composition checks; old policies remain functional but cannot claim those checks were performed. This staged adoption avoids breaking older projects or weakening existing approval gates.

## Native geometry migration boundary

`geometry_mode=native_auto` now derives real KiCad symbol graphics/pins and current placed-instance geometry during pre-placement rather than requiring hand-authored per-component rectangles. Text extents are conservative, not font-exact; the G1 `schematic_style.py` audit still requires a separately reviewed rendered view/worksheet geometry manifest. Pre-placement screening alone does not grant G1 approval. See [native symbol geometry](schematic-native-geometry.md).


## Overlap and label-placement screen (`schematic_overlap.py`)

Read-only. Usage: `python scripts/schematic_overlap.py /project --schematic root.kicad_sch [--kicad-cli PATH] [--layout child.kicad_sch=layout.json ...] [--min-entry 2.54] [--output-dir DIR] [--png [--dpi 200]]`. Pass the top `.kicad_sch`, not the `.kicad_pro` (the project export can fail with "加载原理图失败"). Exit `0` = nothing found, `2` = findings or BLOCKED, never an approval. A JSON report (`overlap-report.json`) lists pages with wire/label/text counts.

Text and graphics are checked separately because their evidence differs.

| Section | Evidence | Finding |
|---|---|---|
| `SHEET_FRAME` | `.kicad_sch` sheet positions/sizes | `SHEET_FRAME.OVERLAP` sheet frames intersect; `SHEET_FRAME.OUTSIDE` a sheet leaves the page |
| `OUT_OF_FRAME` | `.kicad_sch` coordinates vs paper size | `OUT_OF_FRAME` symbol/label/text/junction/no-connect anchors and wire endpoints outside the paper |
| `TEXT_PAIR` | `kicad-cli sch export svg` invisible text records (x, y, textLength, font-size, anchor, rotate) | `TEXT_PAIR` two text boxes overlap (>0.15 mm on both axes): label on label, reference on value, label on pin name |
| `WIRE_TEXT` | SVG text boxes vs wire segments | `WIRE_TEXT` a wire runs through text (>0.3 mm inside the box) |
| `SYMBOL_PAIR` | `--layout` files (Konnect `get_schematic_layout` transformed bounds) | `SYMBOL_PAIR.OVERLAP` component bodies intersect; `SYMBOL_PAIR.WIRE` a wire crosses another symbol (>0.5 mm). Without `--layout` this section is reported as not run |
| `STROKE` | SVG vector paths: glyph polylines, wire paths, unfilled symbol outlines | `STROKE.TEXT_LINE` a wire or symbol outline stroke crosses a text's glyphs; `STROKE.TEXT_TEXT` two texts' glyphs touch; `STROKE.WIRE_SYMBOL` a wire passes through a symbol outline. A wire that ends on an outline is a pin connection and is left to ERC |
| `LABEL` | `.kicad_sch` labels/wires/buses plus SVG text length | `LABEL.OFF_WIRE` label not on a wire or bus (on a bare pin or floating); `LABEL.WIRE_END` net label at a wire end; `LABEL.TEXT_PAST_WIRE` net label text longer than the wire ahead of it; `LABEL.ENTRY_SHORT` hierarchical/global label whose entry wire is shorter than `--min-entry` |

Label text direction is taken from the SVG export: the baseline runs right for 0°/180° and upward for 90°/270°, and `justify right` makes the text end at the anchor. Hierarchical and global labels connect at their anchor, so `LABEL.WIRE_END` applies to net labels only.

`TEXT_PAIR` and `WIRE_TEXT` use text boxes, so they also report near misses (boxes overlap, glyphs do not); `STROKE` answers the exact question "does drawn ink touch drawn ink" and is the one to trust for wire-through-text. Filled areas (symbol body fill, junction dots) are not strokes and are not compared.

Remaining manual work: **readability**. Crowding, long detours and confusing routing are not judged by any script. **Visual fallback:** add `--png --output-dir NEW_DIR` (needs `python -m pip install pypdfium2`, Apache-2.0/BSD-3, no system dependency). The script exports the PDF with kicad-cli and rasterizes every page to `<stem>-page<N>.png` at `--dpi`; open each PNG for readability only. Eye review is unreliable for small text, so it never replaces the script sections.
