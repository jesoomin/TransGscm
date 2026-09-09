# -*- coding: utf-8 -*-
"""멘토 리뷰 스크립트의 수치가 실제 산출물과 맞는지 대조한다."""
import io
import json
import os
from pathlib import Path

os.chdir(r"C:\Users\10982\project\TransGscm")

sc = json.load(open("tracking/scorecard-5screens.json", encoding="utf-8"))
eq = json.load(open("tracking/equivalence-5screens.json", encoding="utf-8"))
he = json.load(open("tracking/human-edit-5screens.json", encoding="utf-8"))
bm = json.load(open("tracking/benchmark-081-110.json", encoding="utf-8"))
d = sc["detail"]

script = io.open("docs/weekly/멘토리뷰-설명스크립트.md", encoding="utf-8").read()

axes = {r["axis"]: 0.0 for r in sc["rows"]}
for r in sc["rows"]:
    axes[r["axis"]] += r["score"]

checks = [
    ("종합 점수", f"{sc['normalized_100']}", "80.9"),
    ("합계 점수", f"{sc['earned']:.2f}", "80.89"),
    ("A축", f"{axes['A. 전환 성공률']:.2f}", "29.40"),
    ("B축", f"{axes['B. 사용자 체감']:.2f}", "19.82"),
    ("C축", f"{axes['C. 탐지 정확성']:.2f}", "16.67"),
    ("D축", f"{axes['D. 기능 동등성']:.2f}", "15.00"),
    ("F 계층", f"{eq['by_layer']['SERVICE']['matched']}/{eq['by_layer']['SERVICE']['cases']}", "48/48"),
    ("Api 페이로드", f"{eq['by_layer']['API']['payload_matched']}/{eq['by_layer']['API']['cases']}", "9/9"),
    ("Api 엄격", f"{eq['by_layer']['API']['matched']}/{eq['by_layer']['API']['cases']}", "0/9"),
    ("동등성 커버리지", f"{eq['screens_executed']}/{eq['screens_total']}", "3/5"),
    ("결정론 처리", f"{d['developer_experience']['deterministic_ratio']:.0%}", "46%"),
    ("리뷰 축소율", f"{d['developer_experience']['review_reduction']:.1%}", "87.6%"),
    ("사람 수정", f"{he['human_edit_ratio']:.2%}", "0.20%"),
    ("산출물", f"{d['conversion']['outputs_produced']}/{d['conversion']['outputs_expected']}", "25/25"),
    ("정적 검증", f"{d['conversion']['checks_passed']}/{d['conversion']['checks_total']}", "29/30"),
]

print(f"{'항목':<16}{'실제값':<12}{'스크립트 기재':<14}판정")
print("-" * 62)
bad = 0
for name, actual, in_script in checks:
    same = actual == in_script
    present = in_script in script
    ok = same and present
    if not ok:
        bad += 1
    note = "OK" if ok else ("값 불일치" if not same else "문서에 없음")
    print(f"{name:<16}{actual:<12}{in_script:<14}{note}")

# 결함 탐지 재현율
det = bm.get("error_detection", {})
rec = f"{det.get('detected', '?')}/{det.get('total', '?')}"
print(f"{'결함 탐지':<16}{rec:<12}{'10/10':<14}"
      f"{'OK' if rec == '10/10' and '10/10' in script else '확인 필요'}")

print("\n결론:", "스크립트 수치 전부 실측과 일치" if bad == 0 else f"{bad}건 불일치 — 수정 필요")
