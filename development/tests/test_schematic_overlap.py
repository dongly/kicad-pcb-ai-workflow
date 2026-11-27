import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / 'kicad-pcb-ai-workflow'
sys.path.insert(0, str(ROOT / 'scripts'))

from schematic_overlap import check_symbols, layout_coverage, _layout_status, run


class SchematicOverlapTest(unittest.TestCase):
    def test_power_symbol_over_component_has_specific_finding(self):
        findings = []
        check_symbols([
            ('#PWR01', (0.0, 0.0, 8.0, 8.0), 'power:+3V3'),
            ('R1', (6.0, 4.0, 11.0, 10.0), 'Device:R'),
        ], [], 'root.kicad_sch', findings)
        finding = next(f for f in findings if f[3].get('rule') == 'POWER_SYMBOL.OVERLAP')
        self.assertIn('#PWR01', finding[2])
        self.assertIn('R1', finding[2])
        self.assertEqual(finding[3]['overlap_mm'], [6.0, 4.0, 8.0, 8.0])

    def test_component_component_overlap_is_detected(self):
        findings = []
        check_symbols([
            ('R1', (0.0, 0.0, 8.0, 8.0), 'Device:R'),
            ('C1', (6.0, 4.0, 11.0, 10.0), 'Device:C'),
        ], [], 'root.kicad_sch', findings)
        self.assertTrue(any(f[3].get('rule') == 'SYMBOL.OVERLAP' for f in findings))

    def test_power_reference_fallback_when_lib_id_missing(self):
        findings = []
        check_symbols([
            ('#PWR01', (0.0, 0.0, 8.0, 8.0), ''),
            ('C1', (7.0, 5.0, 12.0, 10.0), 'Device:C'),
        ], [], 'root.kicad_sch', findings)
        self.assertTrue(any(f[3].get('rule') == 'POWER_SYMBOL.OVERLAP' for f in findings))

    def test_nonoverlapping_power_symbol_is_clear(self):
        findings = []
        check_symbols([
            ('#PWR01', (0.0, 0.0, 8.0, 8.0), 'power:+3V3'),
            ('R1', (9.0, 0.0, 15.0, 6.0), 'Device:R'),
        ], [], 'root.kicad_sch', findings)
        self.assertEqual(findings, [])

    def test_missing_sheet_layout_cannot_report_clear(self):
        coverage = layout_coverage(['root.kicad_sch', 'child.kicad_sch'], [])
        self.assertFalse(coverage['complete'])
        self.assertEqual(coverage['missing_sheets'], ['child.kicad_sch', 'root.kicad_sch'])
        self.assertEqual(_layout_status([], coverage), 'INCOMPLETE')

    def test_complete_layout_without_findings_can_report_no_overlap(self):
        coverage = layout_coverage(['root.kicad_sch'], ['root.kicad_sch'])
        self.assertTrue(coverage['complete'])
        self.assertEqual(_layout_status([], coverage), 'NO_OVERLAP_DETECTED')

    def test_unexpected_layout_entry_keeps_report_incomplete(self):
        coverage = layout_coverage(['root.kicad_sch'], ['root.kicad_sch', 'typo.kicad_sch'])
        self.assertEqual(coverage['unexpected_sheets'], ['typo.kicad_sch'])
        self.assertEqual(_layout_status([], coverage), 'INCOMPLETE')

    def test_run_reports_incomplete_without_layouts(self):
        with (
            patch('schematic_overlap.sheets', return_value={'root.kicad_sch': {}}),
            patch('schematic_overlap.export_svg'),
            patch('schematic_overlap.svg_map', return_value={'root.kicad_sch': 'root.svg'}),
            patch('schematic_overlap.svg_texts', return_value=[]),
            patch('schematic_overlap.wire_segments', return_value=[]),
            patch('schematic_overlap.labels', return_value=[]),
            patch('schematic_overlap.check_frames'),
            patch('schematic_overlap.check_out_of_frame'),
            patch('schematic_overlap.check_text_pairs'),
            patch('schematic_overlap.svg_strokes', return_value=[]),
            patch('schematic_overlap.check_strokes'),
            patch('schematic_overlap.check_wire_text'),
            patch('schematic_overlap.check_labels'),
        ):
            report = run(Path.cwd(), Path('root.kicad_sch'), 'kicad-cli', {}, 2.54)

        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['layout_coverage']['missing_sheets'], ['root.kicad_sch'])
        self.assertEqual(report['pages']['root.kicad_sch']['layout'], 'not_provided')


if __name__ == '__main__':
    unittest.main()
