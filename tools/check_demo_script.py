# -*- coding: utf-8 -*-
"""시연 자료가 인용한 로그 수치를 실제 실행 로그와 대조한다.

영상에는 콘솔이 그대로 찍히므로, 대본이 로그와 다르면 그 자리에서 드러난다.
실제로 한 번 어긋난 적이 있어(BLOCKER 개수·줄 번호) 그 재발을 막으려고 만들었다.

실행: python tools/check_demo_script.py
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "tracking" / "demo-run-5screens.log"
DOCS = [
    ROOT / "docs" / "weekly" / "assets" / "submission-worksheet.html",
    ROOT / "docs" / "weekly" / "assets" / "presentation-kit.html",
    ROOT / "docs" / "weekly" / "시연영상-스크립트.md",
]


def _one(pattern: str, text: str, label: str) -> str:
    """로그에서 값 하나를 뽑는다. 못 찾으면 그 사실을 드러낸다(추측하지 않는다)."""
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"로그에서 '{label}'를 찾지 못했다 — 로그 형식이 바뀌었는지 확인할 것")
    return m.group(1)


def main() -> int:
    if not LOG.exists():
        print(f"로그 없음: {LOG}")
        return 1
    log = LOG.read_text(encoding="utf-8", errors="replace")

    # 로그가 말하는 사실 — 이게 기준이다
    facts = {
        "정적 검증 BLOCKER": _one(r"검증 결과 — BLOCKER (\d+)건", log, "최초 검증 BLOCKER"),
        "수리 대상": _one(r"수리 대상 (\d+)건 확정", log, "수리 대상"),
        "잔여 BLOCKER": _one(r"잔여 BLOCKER\s+(\d+)건", log, "잔여 BLOCKER"),
        "LLM 포팅 호출": _one(r"LLM 포팅 호출\s+(\d+)건", log, "LLM 호출"),
        "규칙 회피": _one(r"규칙 기반으로 회피 (\d+)건", log, "규칙 회피"),
        "규칙 처리 비중": _one(r"규칙 처리 비중 (\d+)%", log, "규칙 비중"),
        "생성 파일": _one(r"생성 파일\s+(\d+)종", log, "생성 파일"),
    }
    store_line = _one(r"UNRESOLVED_STORE_CALL @ (\S+)", log, "Store 호출 결함 위치")
    xml_line = _one(r"XML_PARSE_ERROR @ (\S+)", log, "XML 결함 위치")
    equiv = _one(r"업무 로직\(F\) (\d+/\d+)", log, "F 계층 일치")
    api = _one(r"화면 요청\(Api\) (\d+/\d+)", log, "Api 계층 일치")

    print("로그가 말하는 사실")
    print("-" * 58)
    for k, v in facts.items():
        print(f"  {k:<18} {v}")
    print(f"  {'Store 결함 위치':<18} {store_line}")
    print(f"  {'XML 결함 위치':<18} {xml_line}")
    print(f"  {'동작 일치':<18} F {equiv} · Api {api}")

    # 문서가 인용한 값이 로그와 맞는지 — 인용이 있는 문서만 검사한다
    checks = [
        (f"BLOCKER {facts['정적 검증 BLOCKER']}건", "검증 BLOCKER 개수"),
        (f"수리 대상 {facts['수리 대상']}건", "수리 대상 개수"),
        (store_line, "Store 결함 줄 번호"),
        (xml_line, "XML 결함 줄 번호"),
    ]
    stale = re.compile(r"BLOCKER 10건|수리 대상 9건|10건 중 9건|:82\b|Pla096Mapper\.xml:80")

    print("\n문서 대조")
    print("-" * 58)
    bad = 0
    for doc in DOCS:
        if not doc.exists():
            print(f"  {doc.name:<34} 파일 없음")
            bad += 1
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        hits = [label for value, label in checks if value in text]
        old = stale.findall(text)
        mark = "OK" if not old else "구값 잔존"
        if old:
            bad += 1
        print(f"  {doc.name:<34} 인용 {len(hits)}/{len(checks)} · {mark}"
              + (f" {sorted(set(old))}" if old else ""))

    print("\n결론:", "시연 자료와 로그가 일치" if bad == 0 else f"{bad}건 확인 필요")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
