#!/usr/bin/env python3
"""Build side-by-side standalone English and Simplified-Chinese Skills.

Preview unless --apply. Output must be a fresh directory outside this source repo;
existing directories are never replaced, and this tool never installs the Skill.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of source tree and copied packages

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "kicad-pcb-ai-workflow"
ZH_CORE = REPO / "i18n" / "zh-CN" / "kicad-pcb-ai-workflow"


def load_release_validator():
    path = REPO / "development" / "build_release.py"
    spec = importlib.util.spec_from_file_location("localized_build_release", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load standalone package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


def validate_pairing() -> str:
    verifier = REPO / "i18n" / "verify-pairing.py"
    result = subprocess.run(
        [sys.executable, str(verifier)],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise ValueError("Bilingual pairing validation failed: " + output)
    return output


def translated_files():
    if not ZH_CORE.is_dir():
        raise ValueError("Missing Chinese Skill translations: " + str(ZH_CORE))
    result = {}
    for source in sorted(CORE.rglob("*.md")):
        relative = source.relative_to(CORE)
        translated_name = relative.with_name(relative.stem + ".zh.md")
        translated = ZH_CORE / translated_name
        if not translated.is_file():
            raise ValueError("Missing Chinese translation for " + relative.as_posix())
        result[relative] = translated

    actual = {p.relative_to(ZH_CORE) for p in ZH_CORE.rglob("*.zh.md") if p.is_file()}
    expected = {relative.with_name(relative.stem + ".zh.md") for relative in result}
    if actual != expected:
        extra = sorted(p.as_posix() for p in actual - expected)
        raise ValueError("Unexpected Chinese Skill translation files: " + ", ".join(extra))
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files(root: Path):
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )


def validate_shared_payload(source: Path, english: Path, chinese: Path) -> int:
    source_map = {p.relative_to(source): p for p in files(source)}
    english_map = {p.relative_to(english): p for p in files(english)}
    chinese_map = {p.relative_to(chinese): p for p in files(chinese)}
    if set(source_map) != set(english_map) or set(source_map) != set(chinese_map):
        raise ValueError("Language packages do not contain identical file paths")
    strict_english = {p.relative_to(english) for p in english.rglob("*") if p.is_file()}
    strict_chinese = {p.relative_to(chinese) for p in chinese.rglob("*") if p.is_file()}
    if strict_english != set(source_map) or strict_chinese != set(source_map):
        extra = sorted(p.as_posix() for p in (strict_english | strict_chinese) - set(source_map))
        raise ValueError("Unexpected files in language packages: " + ", ".join(extra))
    checked = 0
    for relative, original in source_map.items():
        if relative.suffix.lower() == ".md":
            continue
        digest = sha256(original)
        if sha256(english_map[relative]) != digest or sha256(chinese_map[relative]) != digest:
            raise ValueError("Non-document payload differs between packages: " + relative.as_posix())
        checked += 1
    return checked


def render_install_guide() -> str:
    return """# Install the KiCad PCB AI Workflow Skill\n\nChoose exactly one complete folder and copy it into your Agent Skills directory:\n\n- `en/kicad-pcb-ai-workflow/` — English\n- `zh-CN/kicad-pcb-ai-workflow/` — 简体中文\n\nKeep the destination folder name `kicad-pcb-ai-workflow`. Install the whole folder; do not copy only `SKILL.md` and do not merge the language variants. The two variants share identical scripts, assets, and JSON data; only Markdown documentation differs.\n\nThis package build does not install KiCad, Konnect, Java, or Freerouting and does not change host configuration. Review the repository README and the Skill's dependency notes before use.\n"""


def build(destination, apply=False):
    out = Path(destination).expanduser().resolve()
    if out.exists() or out.is_relative_to(REPO) or REPO.is_relative_to(out):
        raise ValueError("Use a fresh output directory outside the source repository")
    if not out.parent.is_dir():
        raise ValueError("Output parent directory must already exist")

    pairing_output = validate_pairing()
    validate = load_release_validator()
    source_report = validate(CORE)
    translations = translated_files()
    if not translations:
        raise ValueError("No Chinese Skill translations were found")

    result = {
        "status": "PREVIEW",
        "output_dir": str(out),
        "languages": ["en", "zh-CN"],
        "translated_markdown_files": len(translations),
        "shared_non_markdown_files": sum(1 for p in files(CORE) if p.suffix.lower() != ".md"),
        "source_package": source_report,
        "pairing_validation": pairing_output,
        "production_authorized": False,
    }
    if not apply:
        return result

    out.mkdir(parents=False, exist_ok=False)
    try:
        english = out / "en" / "kicad-pcb-ai-workflow"
        chinese = out / "zh-CN" / "kicad-pcb-ai-workflow"
        english.parent.mkdir()
        chinese.parent.mkdir()
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
        shutil.copytree(CORE, english, ignore=ignore)
        shutil.copytree(CORE, chinese, ignore=ignore)

        for relative, translated in translations.items():
            target = chinese / relative
            target.write_bytes(translated.read_bytes())

        english_report = validate(english)
        chinese_report = validate(chinese)
        shared_count = validate_shared_payload(CORE, english, chinese)
        if english_report["files"] != chinese_report["files"]:
            raise ValueError("English and Chinese packages have different file counts")

        (out / "INSTALL.md").write_text(render_install_guide(), encoding="utf-8", newline="\n")
        result.update(
            status="BUILT_NOT_INSTALLED",
            packages={
                "en": {"path": "en/kicad-pcb-ai-workflow", **english_report},
                "zh-CN": {"path": "zh-CN/kicad-pcb-ai-workflow", **chinese_report},
            },
            shared_non_markdown_files_verified=shared_count,
            production_authorized=False,
        )
        (out / "package-report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return result
    except Exception:
        shutil.rmtree(out)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="fresh directory outside the source repository")
    parser.add_argument("--apply", action="store_true", help="create the two standalone language folders")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.output_dir, args.apply), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "production_authorized": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
