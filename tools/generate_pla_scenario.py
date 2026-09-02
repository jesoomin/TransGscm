"""PLA047 원본을 기반으로 U-PLA001~U-PLA050 가상 레거시 입력 세트를 만든다.

실제 변환기를 일괄 실행하지 않는다. 이 스크립트의 산출물은 화면별 검토를 위한 AS-IS 입력
시나리오이며, 각 화면은 chatui에서 하나씩 변환해야 한다.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_TEMPLATE_NAMES = (
    "PPLA047.java", "PPLA047.bizunit", "FPLA047.java", "FPLA047.bizunit",
    "DPLA047.java", "DPLA047.bizunit", "DPLA047.xsql",
)


def _read_templates(template_dir: Path) -> dict[str, str]:
    missing = [name for name in REQUIRED_TEMPLATE_NAMES if not (template_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"PLA047 템플릿 파일이 없습니다: {', '.join(missing)}")
    return {
        name: (template_dir / name).read_text(encoding="utf-8", errors="replace")
        for name in REQUIRED_TEMPLATE_NAMES
    }


def _replace_screen_tokens(text: str, number: int) -> str:
    """화면 코드와 P BizUnit의 nctRid만 결정론적으로 바꾼다.

    SQL/업무 로직은 원본 그대로 둬야 가상 시나리오에서 Mapper SQL 중복 탐지가 재현된다.
    """
    source_code = "PLA047"
    target_code = f"PLA{number:03d}"
    text = text.replace(source_code, target_code)
    return re.sub(r"RPLA047(\\d{2})", rf"R{target_code}\\1", text)


def generate(template_dir: Path, output_root: Path) -> Path:
    templates = _read_templates(template_dir)
    biz_dir = output_root / "dev-rp-online" / "src" / "java" / "gscm" / "r" / "pm" / "pla" / "plab" / "biz"
    db_dir = output_root / "dev-rp-online" / "src" / "java" / "gscm" / "r" / "pm" / "pla" / "plab" / "db"
    biz_dir.mkdir(parents=True, exist_ok=True)
    db_dir.mkdir(parents=True, exist_ok=True)

    screens: list[dict[str, object]] = []
    for number in range(1, 51):
        code = f"PLA{number:03d}"
        files: list[str] = []
        for template_name, template_text in templates.items():
            output_name = template_name.replace("PLA047", code)
            destination = db_dir / output_name if output_name.endswith(".xsql") else biz_dir / output_name
            destination.write_text(_replace_screen_tokens(template_text, number), encoding="utf-8")
            files.append(str(destination.relative_to(output_root)).replace("\\", "/"))
        screens.append({
            "screen": f"U-{code}",
            "nctRid": [f"R{code}01", f"R{code}02", f"R{code}03"],
            "source_files": files,
            "overlap_expectation": {
                "service": "원본 F 로직을 동일 포팅하면 후보가 될 수 있음",
                "store": "원본 D 접근 패턴을 동일 포팅하면 후보가 될 수 있음",
                "mapper_sql": "원본 XSQL을 그대로 복제했으므로 statement 본문은 화면 간 동일"
            },
        })

    manifest = {
        "scenario": "U-PLA001~U-PLA050 synthetic legacy source set",
        "template": "PLA047 user-provided source files",
        "conversion_policy": "각 화면을 chatui에서 개별 변환·검토한다. 일괄 변환하지 않는다.",
        "screens": screens,
    }
    manifest_path = output_root / "scenario-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-dir", type=Path, required=True, help="PLA047 7개 원본 파일 폴더")
    parser.add_argument("--output-root", type=Path, required=True, help="생성할 scenario 루트")
    args = parser.parse_args()
    manifest = generate(args.template_dir, args.output_root)
    print(f"생성 완료: {manifest}")


if __name__ == "__main__":
    main()
