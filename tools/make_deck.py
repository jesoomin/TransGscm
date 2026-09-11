"""AI Master Project 최종 발표 장표(PPTX) 생성.

템플릿의 도형 위치·색·글꼴을 그대로 두고 텍스트만 채운다. 새 도형은 슬라이드 2의
아키텍처 다이어그램 영역에만 그린다(가이드가 "도형 도구로 직접 그리거나"를 허용).

수치는 전부 docs/weekly/00-종합산출물.md의 실측값이다.
"""
from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

SRC = Path(r"C:/Users/10982/.claude/uploads/205dd1d9-129d-4042-a027-d5acd577e068"
           r"/371bbd2c-AI_Master_Project____________.pptx")
import os
DST = Path(os.environ.get("DECK_OUT") or r"C:/Users/10982/project/TransGscm/docs/weekly/assets/최종발표장표.pptx")

NAVY = RGBColor(0x1F, 0x35, 0x64)
AMBER_T = RGBColor(0xB4, 0x62, 0x1A)
MINT = RGBColor(0x00, 0xA5, 0x91)
GREY = RGBColor(0x66, 0x66, 0x66)
DARK = RGBColor(0x33, 0x33, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF2, 0xF4, 0xF6)


def shp(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(f"{name} not found")


def gshp(group, name):
    for s in group.shapes:
        if s.name == name:
            return s
    raise KeyError(name)


A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def autofit(shape):
    """'넘치면 글자 크기 줄이기'를 켠다.

    템플릿 상자는 크기가 고정인데 한글은 Arial 메트릭보다 넓게 렌더링돼, 계산상 들어맞아도
    실제로는 상자를 넘길 수 있다. 넘친 텍스트가 잘려 보이지 않는 사고를 막는 안전장치다.
    """
    bp = shape.text_frame._txBody.find(A_NS + "bodyPr")
    if bp is None:
        return
    for tag in ("normAutofit", "spAutoFit", "noAutofit"):
        old = bp.find(A_NS + tag)
        if old is not None:
            bp.remove(old)
    bp.append(bp.makeelement(A_NS + "normAutofit", {}))
    shape.text_frame.word_wrap = True


def set_text(shape, lines):
    """lines: 문단 목록. 각 항목은 (text, bold, size_pt|None, color|None) 하나이거나,
    같은 문단 안에 여러 서식을 넣으려면 그런 튜플들의 리스트다(굵은 라벨 + 본문 인라인).
    첫 run 서식을 기준으로 삼는다."""
    tf = shape.text_frame
    base = None
    for p in tf.paragraphs:
        for r in p.runs:
            base = r
            break
        if base:
            break
    base_sz = base.font.size if base is not None and base.font.size else Pt(9)
    base_nm = base.font.name if base is not None and base.font.name else "Arial"

    # 첫 문단만 남기고 삭제
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)
    p0 = tf.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)

    for i, item in enumerate(lines):
        para = p0 if i == 0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.LEFT
        runs = item if isinstance(item, list) else [item]
        for text, bold, size, color in runs:
            run = para.add_run()
            run.text = text
            f = run.font
            f.name = base_nm
            f.size = Pt(size) if size else base_sz
            f.bold = bool(bold)
            f.color.rgb = color if color else GREY
    autofit(shape)


def box(slide, x, y, w, h, fill, line=None, radius=True):
    s = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Emu(x), Emu(y), Emu(w), Emu(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def label(shape, text, size, color, bold=False):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(36000)
    tf.margin_top = tf.margin_bottom = Emu(18000)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = "Arial"
    r.font.color.rgb = color


def arrow(slide, cx, y, h):
    a = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Emu(cx - 45720), Emu(y), Emu(91440), Emu(h))
    a.fill.solid()
    a.fill.fore_color.rgb = RGBColor(0xC5, 0xCE, 0xD8)
    a.line.fill.background()
    a.shadow.inherit = False
    return a


prs = Presentation(SRC)
s1, s2, s3, s4 = prs.slides[0], prs.slides[1], prs.slides[2], prs.slides[3]

# ---------------------------------------------------------------- 표지
set_text(shp(s1, "Text 4"), [("과제명   G-SCM 차세대 전환 Agent", True, 11, DARK)])
set_text(shp(s1, "Text 5"), [("멘   티   [성명], [사번]", False, 11, DARK)])
set_text(shp(s1, "Text 6"), [("멘   토   [성명]", False, 11, DARK)])

# ------------------------------------------------- 슬라이드 1 · 프로젝트 개요
# 서술형 문장 대신 라벨 + 짧은 구(句). 발표는 말로 채우고 장표는 근거만 남긴다.
set_text(shp(s2, "Text 10"), [
    ("화면-서비스 매핑(nctRid)이 명명 규칙과 불일치", True, 9.5, DARK),
    ("→ 서버 로직 1건 전환에 P·F·D·XSQL 4종 파일 수작업 추적", False, 9, GREY),
    ("", False, 3, GREY),
    [("규모  ", True, 9, MINT), ("1,416개 화면에서 동일 추적 반복", False, 9, GREY)],
    [("품질  ", True, 9, MINT), ("개발자별 응답·예외 처리 이원화", False, 9, GREY)],
    [("리스크  ", True, 9, MINT), ("원본에 결함 혼재 — 컴파일 불가·XML·SQL 오류", False, 9, GREY)],
    ("", False, 3, GREY),
    ("정상 원본을 전제한 도구는 첫 화면에서 멈춤", True, 9, DARK),
])

set_text(shp(s2, "Text 14"), [
    ("폴더 지정 → 8단계 자동 진행 → 사람 승인 후에만 반영 (Human-in-the-Loop)", True, 9.5, DARK),
    ("", False, 3, GREY),
    ("에이전트 구성", True, 9, MINT),
    ("Planner  계획 파일 고정 (LLM 미사용)", False, 8.5, GREY),
    ("Translator  규칙 46% / LLM 54% 분업", False, 8.5, GREY),
    ("Validator  변환기와 분리", False, 8.5, GREY),
    ("Repairer  검증 기반 자가 교정, 회차 상한 2", False, 8.5, GREY),
    ("Human-in-the-Loop  승인 게이트 — 승인 전 저장 0건", False, 8.5, GREY),
    ("기술 스택", True, 9, MINT),
    ("LangGraph StateGraph · MCP(Model Context Protocol)", False, 8.5, GREY),
    ("Azure OpenAI 호환 사내 LLM Gateway · Tree-of-Thoughts · Oracle", False, 8.5, GREY),
])

set_text(shp(s2, "Text 17"), [
    ("100%", True, 20, NAVY),
    ("원본 결함 탐지율", True, 8, DARK),
    ("30화면 정답키 · 오탐 0건", False, 7, GREY),
])
set_text(shp(s2, "Text 19"), [
    ("96.7%", True, 20, NAVY),
    ("정적 검증 통과율", True, 8, DARK),
    ("29/30건", False, 7, GREY),
])
set_text(shp(s2, "Text 21"), [
    ("0.20%", True, 20, MINT),
    ("사람 수정 라인 비율  ·  리뷰 대상 87.6% 축소", True, 8, DARK),
    ("생성 2,007줄 중 4줄 · AI 리뷰어 1차 기준 하한값", False, 7, GREY),
])
set_text(shp(s2, "Text 24"), [
    ("“규칙 기반 변환에 LLM을 쓰지 않아 호출 46% 절감,", True, 10.5, DARK),
    ("정적 검증 통과 코드의 실행 일치율 33%를", True, 10.5, DARK),
    ("직접 측정해 100%로 개선”", True, 10.5, DARK),
    ("", False, 4, GREY),
    ("전환 스코어카드 80.9 / 100  ·  측정 범위 확대로 88.2에서 하향", False, 8, MINT),
])

# ------------------------------------------------ 슬라이드 2 · 기술 아키텍처
diagram_host = shp(s3, "Text 8")
diagram_host._element.getparent().remove(diagram_host._element)

AMBER = RGBColor(0xB4, 0x62, 0x1A)
PALE = RGBColor(0xE8, 0xEC, 0xF0)
RAIL = RGBColor(0xC5, 0xCE, 0xD8)
BAND = RGBColor(0xF7, 0xF9, 0xFA)

# 컨테이너(템플릿 Shape 7) 안쪽. 바닥 한계(4,880,000 EMU) 기준으로 역산한다.
X0, W0 = 400000, 4350000
TOP = 720000


def tbox(slide, x, y, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT):
    t = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = "Arial"
    r.font.color.rgb = color
    return t


def label_lines(shape, lines, align=PP_ALIGN.CENTER):
    """lines: (text, size_pt, bold, color) 여러 줄을 한 도형 안에 세로로 넣는다."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(28000)
    tf.margin_top = tf.margin_bottom = Emu(14000)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, (text, size, bold, color) in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        r = para.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = "Arial"
        r.font.color.rgb = color


def chips(slide, x, y, w, h, items, fill, fg, size=7):
    n = len(items)
    gap = 36000
    cw = (w - gap * (n - 1)) // n
    for i, it in enumerate(items):
        c = box(slide, x + i * (cw + gap), y, cw, h, fill)
        label(c, it, size, fg)


y = TOP

# ── 입력 ────────────────────────────────────────────────────────────────
tbox(s3, X0, y, W0, 150000,
     "AS-IS   P · F · D BizUnit + XSQL   (구성 파일 5종)", 8, GREY, True)
y += 150000
arrow(s3, X0 + W0 // 2, y + 6000, 62000)
y += 74000

# ── ① 계획 — 순환 밖에 둔다 ─────────────────────────────────────────────
PLAN_H = 370000
pl = box(s3, X0, y, W0, PLAN_H, NAVY)
pl.line.color.rgb = MINT
pl.line.width = Pt(1.25)
label_lines(pl, [
    ("①  PLAN   계획 수립 — 무엇을 어떤 도구로 처리할지 먼저 확정", 9.5, True, WHITE),
    ("정적 분석 · LLM 미사용 · 파일로 고정해 이후 단계가 이 계획만 따른다",
     7.5, False, RGBColor(0xC9, 0xD6, 0xE8)),
])
y += PLAN_H
arrow(s3, X0 + W0 // 2, y + 6000, 62000)
y += 74000

# ── 추론 순환 (Reason – Act) ────────────────────────────────────────────
CYC_H = 1020000
cyc = box(s3, X0, y, W0, CYC_H, RGBColor(0xFA, 0xFB, 0xFC), line=RAIL)
tbox(s3, X0 + 100000, y + 48000, W0 - 200000, 150000,
     "추론 순환   REASON → ACT → OBSERVE → REFLECT", 8.5, NAVY, True)

CN_W, CN_H = 985000, 490000  # 부제가 2줄로 접히므로 0.54in 필요(9pt + 7pt×2)
CN_GAP = 42000
cx0 = X0 + (W0 - (CN_W * 4 + CN_GAP * 3)) // 2
cy0 = y + 225000
CYCLE = [
    ("REASON", "계획이 지목한 대상 판단", MINT),
    ("ACT", "도구 호출 · LLM 포팅", NAVY),
    ("OBSERVE", "규칙 기반 검증", MINT),
    ("REFLECT", "교정 판단 · 회차 상한 2", AMBER),
]
for i, (name, desc, col) in enumerate(CYCLE):
    bx = cx0 + i * (CN_W + CN_GAP)
    nb = box(s3, bx, cy0, CN_W, CN_H, col)
    label_lines(nb, [
        (name, 9, True, WHITE),
        (desc, 7, False, RGBColor(0xDE, 0xE8, 0xF0)),
    ])

# 가로 화살표는 arrow()가 세로 전용이라 직접 그린다
from pptx.enum.shapes import MSO_SHAPE as _MS
for i in range(3):
    ax = cx0 + (i + 1) * CN_W + i * CN_GAP + 6000
    ar = s3.shapes.add_shape(_MS.RIGHT_ARROW, Emu(ax), Emu(cy0 + CN_H // 2 - 34000),
                             Emu(CN_GAP - 12000), Emu(68000))
    ar.fill.solid()
    ar.fill.fore_color.rgb = RGBColor(0xB8, 0xC2, 0xCC)
    ar.line.fill.background()
    ar.shadow.inherit = False

# 되먹임 — REFLECT 에서 ACT 로 돌아간다. 순환이라는 게 이 선 하나로 읽힌다.
fb_y = cy0 + CN_H + 66000
fx_from = cx0 + 3 * (CN_W + CN_GAP) + CN_W // 2
fx_to = cx0 + 1 * (CN_W + CN_GAP) + CN_W // 2
AMD = RGBColor(0xC8, 0x96, 0x5A)
for seg in ((fx_from, cy0 + CN_H, fx_from, fb_y), (fx_from, fb_y, fx_to, fb_y)):
    ln = s3.shapes.add_shape(_MS.RECTANGLE, Emu(min(seg[0], seg[2])), Emu(min(seg[1], seg[3])),
                             Emu(max(abs(seg[2] - seg[0]), 26000)),
                             Emu(max(abs(seg[3] - seg[1]), 26000)))
    ln.fill.solid()
    ln.fill.fore_color.rgb = AMD
    ln.line.fill.background()
    ln.shadow.inherit = False
up = s3.shapes.add_shape(_MS.UP_ARROW, Emu(fx_to - 46000), Emu(cy0 + CN_H + 10000),
                         Emu(92000), Emu(56000))
up.fill.solid()
up.fill.fore_color.rgb = AMD
up.line.fill.background()
up.shadow.inherit = False
tbox(s3, cx0, fb_y + 30000, CN_W * 4 + CN_GAP * 3, 140000,
     "검증 실패 시에만 되돌아간다 — 통과하거나 예산을 소진하면 순환을 빠져나온다",
     7, GREY, False, PP_ALIGN.CENTER)
y += CYC_H

# 통상 ReAct와 갈리는 지점 — 이 한 줄이 이 장표의 논지다
tbox(s3, X0, y + 16000, W0, 150000,
     "관찰자가 모델이 아니라 규칙 기반 검증기다   —   자기 평가를 쓰지 않는다",
     8, MINT, True, PP_ALIGN.CENTER)
y += 180000
arrow(s3, X0 + W0 // 2, y + 6000, 62000)
y += 74000

# ── ACT 가 호출하는 도구 ────────────────────────────────────────────────
PAD, HDR, ROW_H, ROW_GAP = 100000, 150000, 250000, 38000
BAND_H = HDR + PAD + ROW_H * 2 + ROW_GAP
band = box(s3, X0, y, W0, BAND_H, BAND, line=RAIL)
tbox(s3, X0 + 92000, y + 46000, W0 - 184000,
     HDR, "ACT 가 호출하는 도구 — 계획이 지목한 대상만", 8, NAVY, True)

TOOLS = [
    ("② 규칙 변환기", MINT), ("② 코드 뼈대·DTO", MINT),
    ("③ LLM Gateway", NAVY), ("④ 정적 검증기", MINT),
    ("⑤ ToT 교정기", NAVY), ("⑥ 동작 일치", MINT),
    ("⑦ 교차 분석", MINT), ("⑧ 빌드 검증", MINT),
]
tx = X0 + PAD
tw = (W0 - PAD * 2 - 38000 * 3) // 4
ty0 = y + HDR + 34000
for i, (name, color) in enumerate(TOOLS):
    r, c = divmod(i, 4)
    tb = box(s3, tx + c * (tw + 38000), ty0 + r * (ROW_H + ROW_GAP), tw, ROW_H, color)
    label(tb, name, 7.5, WHITE, True)
y += BAND_H
arrow(s3, X0 + W0 // 2, y + 6000, 62000)
y += 74000

# ── 승인 게이트 ─────────────────────────────────────────────────────────
GATE_H = 250000
g = box(s3, X0, y, W0, GATE_H, AMBER)
label(g, "사람 승인 게이트 — 승인 전에는 산출물·DB에 아무것도 쓰지 않는다", 8.5, WHITE, True)
y += GATE_H
arrow(s3, X0 + W0 // 2, y + 6000, 62000)
y += 74000

# ── 산출물 ──────────────────────────────────────────────────────────────
tbox(s3, X0, y, W0, 150000,
     "TO-BE   Api · Service · Store · Dto · Mapper.xml   (Spring / MyBatis)",
     8, GREY, True)
y += 176000

# ── 범례 ────────────────────────────────────────────────────────────────
sw = 88000
LEG_PITCH = 1_180_000          # 범례 3칸을 왼쪽 절반 안에 균등 배치
lx = X0
for col, lab in ((MINT, "규칙 기반 (LLM 0회)"), (NAVY, "LLM 호출"), (AMBER, "분기 · 승인")):
    # 글자 길이로 간격을 계산하면 한글·영문 폭이 달라 어긋난다. 고정 피치로 나눈다.
    box(s3, lx, y + 18000, sw, sw, col)
    tbox(s3, lx + sw + 28000, y + 16000, LEG_PITCH - sw - 40000, 130000, lab, 6.5, GREY)
    lx += LEG_PITCH
tbox(s3, X0, y + 16000, W0, 130000,
     "MCP 읽기 전용 조회 4종 — 변환 실행은 노출하지 않는다",
     6.5, GREY, False, PP_ALIGN.RIGHT)

set_text(shp(s3, "Text 9"), [
    ("1,416회 반복되는 작업이다 — 매번 다른 경로로 가면 리뷰도 재현도 불가능하다.",
     True, 9, DARK),
    ("그래서 모델이 도구를 고르지 않는다. 계획을 먼저 파일로 확정하고, 그 계획이 도구 호출을 지휘한다.",
     False, 8.5, GREY),
])

set_text(shp(s3, "Text 14"), [("LangGraph StateGraph + 계획 파일 고정", True, 9, DARK)])
set_text(shp(s3, "Text 15"), [
    [("선택 이유  ", True, 8, MINT),
     ("ReAct 자율 탐색은 1,416회 반복에서 화면마다 경로가 갈림", False, 8, GREY)],
    [("핵심 활용  ", True, 8, MINT),
     ("계획을 파일로 확정 → 이후 단계는 지목된 대상만 호출, Send()로 병렬 분배",
      False, 8, GREY)],
    [("강점  ", True, 8, NAVY),
     ("계획이 도구 호출을 지휘 — 재현·리뷰·재실행 가능", True, 8, NAVY)],
])

set_text(shp(s3, "Text 20"), [("MCP (Model Context Protocol)", True, 9, DARK)])
set_text(shp(s3, "Text 21"), [
    [("선택 이유  ", True, 8, MINT),
     ("도구 동적 선택은 '자율 탐색 배제' 원칙과 충돌 → 표면 분리", False, 8, GREY)],
    [("핵심 활용  ", True, 8, MINT),
     ("조회 4종만 노출, 변환 실행 미노출. 실 클라이언트 stdio 연결 검증", False, 8, GREY)],
    [("강점  ", True, 8, NAVY),
     ("표준 프로토콜을 열되 승인 게이트는 우회 불가", True, 8, NAVY)],
])

set_text(shp(s3, "Text 26"), [("Tree-of-Thoughts + Validator-driven Self-Correction", True, 9, DARK)])
set_text(shp(s3, "Text 27"), [
    [("선택 이유  ", True, 8, MINT),
     ("통상 ToT는 모델이 자기 가지를 자평 → 규칙 기반 검증기로 대체", False, 8, GREY)],
    [("핵심 활용  ", True, 8, MINT),
     ("후보 병렬 생성 → 잔여 BLOCKER 수로 채점 (MatchFixAgent/ACToR)", False, 8, GREY)],
    [("강점  ", True, 8, NAVY),
     ("채점자가 LLM이 아니라 규칙 기반 검증기", True, 8, NAVY)],
])

# --------------------------------------------- 슬라이드 3 · 핵심 기술 과제
set_text(shp(s4, "Text 9"), [
    ("검증과 실행의 간극 — 정적 검증 100% 통과 코드가 실행에서는 동작 불일치",
     True, 9.5, DARK),
    ("AlphaTrans(FSE 2025) 동일 간극 보고 : 문법 96.40%  vs  동작 일치 25.14%",
     False, 9, GREY),
])

set_text(shp(s4, "Text 13"), [
    ("전제 재검토", True, 8.5, MINT),
    ("“실행 수단이 없다”가 오판 — 앱 기동이 아니라 메서드 호출 환경이면 됐다",
     False, 7.5, GREY),
    ("① 최소 실행 Harness", True, 8.5, DARK),
    ("데이터 계층을 양쪽 동일 고정값으로 → 차이는 포팅 차이만", False, 7.5, GREY),
    ("0행 / 1행 / 3행으로 분기 전수", False, 7.5, GREY),
    ("② 호출 대상 계약 JSON 주입", True, 8.5, DARK),
    ("실제 메서드명·반환 타입·결과 건수를 명시", False, 7.5, GREY),
    ("③ ToT 교정 — 채점자 분리", True, 8.5, DARK),
    ("후보 병렬 생성, 규칙 기반 검증기가 채점", False, 7.5, GREY),
    ("BLOCKER 10건 중 9건만 교정, 나머지는 사람에게", False, 7.5, GREY),
    ("④ 판단 근거를 로그로", True, 8.5, DARK),
    ("모델이 원본 버그 2건을 스스로 지적", False, 7.5, GREY),
    ("⑤ 자동화하지 않을 것을 확정", True, 8.5, DARK),
    ("원본 결함은 보존·표시, 미확인 패턴에 규칙 생성 금지", False, 7.5, GREY),
    ("", False, 3, GREY),
    ("2차 적용 — 개발 표준 내재화", True, 8.5, AMBER_T),
    ("네이밍·계층 책임·예외 규약을 암묵지에서 규칙으로", False, 7.5, GREY),
    ("전환 직후 LLM이 표준 기준으로 한 번 더 검토", False, 7.5, GREY),
    ("이관이 아니라 운영 품질까지 보장하는 소스로", False, 7.5, GREY),
])

grp = [s for s in s4.shapes if s.shape_type == 6][0]
set_text(gshp(grp, "Text 18"), [("33%→", True, 16, NAVY), ("100%", True, 16, MINT)])
set_text(gshp(grp, "Text 20"), [
    ("업무 로직(F) 실행 일치율", True, 9, DARK),
    ("27건 중 9건 → 원인(레코드셋 추출 누락) 수정 후 48/48", False, 7, GREY),
    ("※ 실행 가능한 3화면 기준 (2화면은 원본 컴파일 불가)", False, 6.5, MINT),
])
set_text(gshp(grp, "Text 22"), [("0/9→", True, 16, NAVY), ("9/9", True, 16, MINT)])
set_text(gshp(grp, "Text 24"), [
    ("화면 요청(Api) 페이로드 일치율", True, 9, DARK),
    ("“P는 순수 위임” = 표본 1건 가정 → 30화면 전수 확인으로 반증", False, 7, GREY),
    ("※ 메시지 키는 0/9 — 응답 규약 미확정, 지어내지 않음", False, 6.5, MINT),
])
set_text(gshp(grp, "Text 26"), [("5→", True, 16, NAVY), ("1건", True, 16, MINT)])
set_text(gshp(grp, "Text 28"), [
    ("화면당 LLM 포팅 호출", True, 9, DARK),
    ("성공 불가 대상 반복 호출 80% 제거 · 규칙 기반 회피 46% 포함", False, 7, GREY),
])

DST.parent.mkdir(parents=True, exist_ok=True)
prs.save(DST)
print("saved:", DST)
