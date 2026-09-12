"""조회 패널 도구 — 사용법 안내·화면 리포트·소스 열람.

여기서 지키려는 건 두 가지다.
  1. **읽기만 한다.** 쓰기·변환 실행 도구가 목록에 끼면 모델이 고를 수 있게 된다.
  2. **계획서가 기록한 파일만 읽는다.** 사용자가 준 경로를 그대로 열면 .env까지 닿는다.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents import query_tools  # noqa: E402


def test_usage_reference_matches_the_pipeline_it_describes() -> None:
    """단계 수·판정 종류가 코드와 어긋나면 안내가 거짓말이 된다."""
    pipeline = query_tools.USAGE["파이프라인"]
    for step in range(1, 9):
        assert f"\n  {step} " in pipeline, f"{step}단계 설명이 없다"
    assert "9 " not in pipeline, "9단계는 없다"

    verdicts = query_tools.USAGE["판정체계"]
    for v in ("PASS", "WARNING", "BLOCKER", "FAIL", "SKIPPED", "APPROVED"):
        assert v in verdicts, f"판정 {v}가 빠졌다"


def test_how_to_use_returns_a_single_topic_or_everything() -> None:
    one = query_tools.call("how_to_use", {"topic": "판정체계"})
    assert one["topic"] == "판정체계" and "BLOCKER" in one["text"]
    whole = query_tools.call("how_to_use", {})
    assert all(k in whole["text"] for k in query_tools.USAGE)


def test_tools_are_read_only() -> None:
    names = {t["name"] for t in query_tools.tools()}
    assert names == {"how_to_use", "screen_report", "read_screen_source"}
    banned = ("save", "write", "convert", "run_pipeline", "delete", "approve")
    assert not [n for n in names if any(b in n for b in banned)]


def test_unknown_tool_is_refused() -> None:
    with pytest.raises(ValueError):
        query_tools.call("save_everything", {})


def test_missing_screen_says_what_is_available() -> None:
    with pytest.raises(FileNotFoundError) as exc:
        query_tools.call("screen_report", {"screen_id": "ZZZ999"})
    assert "변환 계획이 없습니다" in str(exc.value)


def _a_real_screen() -> str | None:
    plans = sorted(query_tools.PLAN_DIR.glob("*-conversion-plan.json"))
    return plans[0].name.split("-")[0] if plans else None


@pytest.mark.skipif(_a_real_screen() is None, reason="변환 계획이 아직 없음")
def test_screen_report_reports_whether_the_original_compiles() -> None:
    out = query_tools.call("screen_report", {"screen_id": _a_real_screen()})
    assert "원본이_컴파일되지_않음" in out
    assert "구성_파일" in out and out["screen_id"] == _a_real_screen()


@pytest.mark.skipif(_a_real_screen() is None, reason="변환 계획이 아직 없음")
def test_source_read_lists_methods_then_returns_one_body_capped() -> None:
    screen = _a_real_screen()
    listing = query_tools.call("read_screen_source", {"screen_id": screen, "fragment": "F.java"})
    if "error" in listing:
        pytest.skip(listing["error"])
    assert listing["메서드"], "메서드 목록이 비었다"
    body = query_tools.call("read_screen_source", {
        "screen_id": screen, "fragment": "F.java", "method_name": listing["메서드"][0]})
    assert len(body["본문"]) <= query_tools.MAX_SOURCE_CHARS, "상한을 넘겨 실렸다"


@pytest.mark.skipif(_a_real_screen() is None, reason="변환 계획이 아직 없음")
def test_an_unknown_method_name_is_refused_rather_than_guessed() -> None:
    out = query_tools.call("read_screen_source", {
        "screen_id": _a_real_screen(), "fragment": "F.java", "method_name": "fNope"})
    assert "error" in out and "있는 메서드" in out["error"]


def test_source_paths_come_from_the_plan_not_the_caller() -> None:
    """호출자가 경로를 넘길 자리가 스펙에 없어야 한다(경로 탐색 차단)."""
    spec = next(t for t in query_tools.tools() if t["name"] == "read_screen_source")
    props = set(spec["inputSchema"]["properties"])
    assert props == {"screen_id", "fragment", "method_name"}
    assert "path" not in json.dumps(spec, ensure_ascii=False).lower()
