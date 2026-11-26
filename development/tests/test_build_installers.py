"""Bilingual installer build contracts and counterexamples."""
import json
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'development'))
import build_installers


def walk(root):
    return {p.relative_to(root): p for p in root.rglob('*') if p.is_file()}


class SharedPayloadGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base/'source'
        self.english = self.base/'en'
        self.chinese = self.base/'zh-CN'
        for root in (self.source, self.english, self.chinese):
            root.mkdir()
            (root/'data.json').write_bytes(b'{"k": 1}')
            (root/'doc.md').write_bytes(b'# Doc\n')

    def test_stray_file_in_output_blocks(self):
        (self.english/'stray.pyc').write_bytes(b'bytecode')
        with self.assertRaisesRegex(ValueError, 'Unexpected files in language packages'):
            build_installers.validate_shared_payload(self.source, self.english, self.chinese)

    def test_missing_file_blocks(self):
        (self.chinese/'data.json').unlink()
        with self.assertRaisesRegex(ValueError, 'identical file paths'):
            build_installers.validate_shared_payload(self.source, self.english, self.chinese)

    def test_tampered_shared_file_blocks(self):
        (self.chinese/'data.json').write_bytes(b'{"k": 2}')
        with self.assertRaisesRegex(ValueError, 'Non-document payload differs'):
            build_installers.validate_shared_payload(self.source, self.english, self.chinese)

    def test_translated_markdown_may_differ(self):
        (self.chinese/'doc.md').write_bytes(b'# Doc (zh-CN)\n')
        checked = build_installers.validate_shared_payload(self.source, self.english, self.chinese)
        self.assertEqual(checked, 1)


class BuildContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)

    def test_output_inside_repository_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'fresh output directory'):
            build_installers.build(REPO/'development'/'installers-out', apply=False)

    def test_existing_output_directory_is_refused(self):
        out = self.base/'out'
        out.mkdir()
        with self.assertRaisesRegex(ValueError, 'fresh output directory'):
            build_installers.build(out, apply=False)

    def test_preview_creates_nothing(self):
        out = self.base/'preview'
        result = build_installers.build(out, apply=False)
        self.assertEqual(result['status'], 'PREVIEW')
        self.assertFalse(out.exists())
        self.assertEqual(result['languages'], ['en', 'zh-CN'])
        self.assertIn('verified', result['pairing_validation'])

    def test_apply_builds_parallel_language_packages(self):
        out = self.base/'out'
        result = build_installers.build(out, apply=True)
        self.assertEqual(result['status'], 'BUILT_NOT_INSTALLED')
        english = out/'en'/'kicad-pcb-ai-workflow'
        chinese = out/'zh-CN'/'kicad-pcb-ai-workflow'
        english_files, chinese_files = walk(english), walk(chinese)
        self.assertEqual(set(english_files), set(chinese_files))
        differing_shared = [
            relative.as_posix() for relative in english_files
            if relative.suffix != '.md' and english_files[relative].read_bytes() != chinese_files[relative].read_bytes()
        ]
        differing_markdown = [
            relative.as_posix() for relative in english_files
            if relative.suffix == '.md' and english_files[relative].read_bytes() != chinese_files[relative].read_bytes()
        ]
        self.assertEqual(differing_shared, [])
        self.assertGreater(len(differing_markdown), 0)
        for relative in list(english_files) + list(chinese_files):
            self.assertFalse('__pycache__' in relative.parts or relative.suffix == '.pyc', relative)
        self.assertTrue((out/'INSTALL.md').is_file())
        report = json.loads((out/'package-report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'BUILT_NOT_INSTALLED')
        self.assertEqual(set(report['packages']), {'en', 'zh-CN'})
        self.assertEqual(report['shared_non_markdown_files_verified'], result['shared_non_markdown_files'])
        self.assertFalse(report['production_authorized'])
        victim = sorted(english_files)[0]
        (chinese/victim).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'Non-document payload differs'):
            build_installers.validate_shared_payload(build_installers.CORE, english, chinese)


class TranslatedMappingTests(unittest.TestCase):
    def test_every_core_markdown_has_exactly_one_translation(self):
        translations = build_installers.translated_files()
        self.assertGreater(len(translations), 0)
        self.assertIn(pathlib.Path('SKILL.md'), translations)
        self.assertNotIn(pathlib.Path('SKILL.zh.md'), translations)


if __name__ == '__main__':
    unittest.main()
