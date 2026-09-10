"""워크플로우 및 오케스트레이션 다이어그램 PNG 생성.

읽는 사람이 한 장에서 알아야 할 것
  1. 계획(Step 1)이 도구 선택(Step 2)을 확정한다 — 모델이 고르지 않는다
  2. 규칙 경로와 LLM 경로가 색으로 갈린다
  3. 순환은 자가 교정 한 곳뿐이고 상한이 있다
  4. 저장은 그래프 밖, 사람 승인 뒤에만
"""
from PIL import Image, ImageDraw, ImageFont

S = 2                      # 2배 해상도로 그린 뒤 축소 → 글자 경계가 깨끗해진다
W, H = 1500 * S, 1080 * S

NAVY = (31, 53, 100)
MINT = (0, 145, 125)
AMBER = (170, 92, 26)
INK = (26, 34, 32)
INK2 = (95, 109, 105)
LINE = (206, 214, 211)
PALE = (238, 242, 240)
BG = (250, 251, 250)
WHITE = (255, 255, 255)
VIOLET = (108, 78, 158)

F = 'C:/Windows/Fonts/malgun.ttf'
FB = 'C:/Windows/Fonts/malgunbd.ttf'
FM = 'C:/Windows/Fonts/consola.ttf'


def f(size, bold=False, mono=False):
    return ImageFont.truetype(FM if mono else (FB if bold else F), size * S)


img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)


def text(x, y, s, size=13, bold=False, color=INK, anchor='la', mono=False):
    d.text((x * S, y * S), s, font=f(size, bold, mono), fill=color, anchor=anchor)


def rrect(x, y, w, h, fill, outline=None, r=8, width=1):
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                        fill=fill, outline=outline, width=width * S)


def arrow(x1, y1, x2, y2, color=(150, 162, 158), w=2, head=7):
    d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=color, width=w * S)
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    for sgn in (1, -1):
        b = a + sgn * 2.6
        d.line([x2 * S, y2 * S,
                (x2 + head * math.cos(b)) * S, (y2 + head * math.sin(b)) * S],
               fill=color, width=w * S)


def box(x, y, w, h, title, lines, fill, fg, sub_fg, tsize=14, lsize=11.5):
    rrect(x, y, w, h, fill)
    text(x + 14, y + 12, title, tsize, True, fg)
    yy = y + 12 + tsize + 8
    for ln in lines:
        text(x + 14, yy, ln, lsize, False, sub_fg)
        yy += lsize + 6


# ────────────────────────────────────────────────── 머리말
text(48, 40, '워크플로우 및 오케스트레이션', 26, True, INK)
text(48, 76, 'Workflow & Logic  ·  G-SCM 차세대 전환 Agent', 13, False, INK2)
d.line([48 * S, 108 * S, (W - 48 * S), 108 * S], fill=LINE, width=2 * S)

# ────────────────────────────────────────────────── 2.1 처리 로직
text(48, 128, '2.1  처리 로직', 17, True, NAVY)

BX, BW, BH, BY = 48, 460, 224, 162
GAP = 26

box(BX, BY, BW, BH, 'Step 1 — Input Analysis',
    ['정적 분석으로 입력을 해부한다',
     '· 화면별 구성 파일 5종 식별',
     '· P→F→D 호출 관계도 + SQL 매핑 구축',
     '· 메서드별 처리 경로 판정',
     '   단순 위임 → 규칙 / 계산·분기 → LLM',
     '· 원본 결함 사전 검출',
     '· 판정을 계획 파일로 고정',
     '',
     'LLM 미사용'],
    MINT, WHITE, (208, 236, 230), 14, 11)

box(BX + BW + GAP, BY, BW, BH, 'Step 2 — Tool Selection',
    ['계획이 도구를 지정한다',
     '· 분기 기준은 Step 1의 판정 결과',
     '· 실행 시점에 다시 판단하지 않는다',
     '· 규칙 경로 / LLM 경로 / 검증 경로',
     '· 검증 실패 시에만 자가 교정으로 회귀',
     '',
     '실측 — 포팅 대상 46건 중 21건(46%)이',
     '규칙 경로로 빠져 LLM 호출 자체를 회피',
     '',
     '모델이 도구를 스스로 고르지 않는다'],
    NAVY, WHITE, (200, 213, 235), 14, 11)

box(BX + (BW + GAP) * 2, BY, BW, BH, 'Step 3 — Execution & Response',
    ['결과를 합치고 판정한다',
     '· 병렬 결과를 표시 지점에 결합',
     '   (반복 실행 안전)',
     '· PASS / WARNING / BLOCKER 판정',
     '· BLOCKER 1건이라도 있으면 저장 불가',
     '· 화면별 인수인계 문서 생성',
     '   (재판정 없이 재배치)',
     '',
     '최종 반영은 사람 승인 후에만'],
    MINT, WHITE, (208, 236, 230), 14, 11)

for i in range(2):
    cx = BX + BW + (BW + GAP) * i + 4
    arrow(cx, BY + BH / 2, cx + GAP - 8, BY + BH / 2, (150, 162, 158), 3, 9)

# ────────────────────────────────────────────────── 2.2 상태 관리
GY = BY + BH + 46
text(48, GY, '2.2  상태 관리  —  LangGraph Node / Edge', 17, True, NAVY)
text(W / S - 48, GY + 5, '대화 턴이 아니라 “실행 1회”가 상태의 단위다', 11.5, False, INK2, 'ra')

FY = GY + 38
FLOW_W = 1000
FLOW_H = 384
rrect(48, FY, FLOW_W, FLOW_H, WHITE, LINE, 10, 1)

NW, NH, NG = 176, 46, 12
LX = 74


def node(x, y, name, desc, col, w=NW):
    rrect(x, y, w, NH, col)
    text(x + w / 2, y + 12, name, 11.5, True, WHITE, 'ma', mono=True)
    text(x + w / 2, y + 28, desc, 10, False, (218, 230, 240), 'ma')


def elbow(x1, y1, x2, y2, color=(150, 162, 158), w=2):
    """세로 → 가로 → 세로 꺾임 연결. 대각선이 교차하면 읽히지 않는다."""
    mid = (y1 + y2) / 2
    d.line([x1 * S, y1 * S, x1 * S, mid * S], fill=color, width=w * S)
    d.line([x1 * S, mid * S, x2 * S, mid * S], fill=color, width=w * S)
    d.line([x2 * S, mid * S, x2 * S, (y2 - 6) * S], fill=color, width=w * S)
    arrow(x2, y2 - 8, x2, y2 - 1, color, w, 7)


# 1행 — 계획 → 규칙 변환 → 배분
R1 = FY + 26
node(LX, R1, 'plan_all', '계획 수립·고정', MINT)
node(LX + NW + NG, R1, 'convert_all', '규칙 기반 변환', MINT)
node(LX + (NW + NG) * 2, R1, 'dispatch_ports_all', '계획이 지목한 대상만 배분', NAVY)
for i in range(2):
    x = LX + NW + (NW + NG) * i
    arrow(x + 2, R1 + NH / 2, x + NG - 2, R1 + NH / 2, (150, 162, 158), 3, 6)

# 2행 — 병렬 분기 띠 (교차 없이 위아래로만 연결)
R2 = R1 + NH + 34
BAND_X, BAND_W = LX, (NW + NG) * 2 + NW
rrect(BAND_X, R2, BAND_W, 58, (243, 240, 250))
text(BAND_X + 16, R2 + 9, 'Send() 병렬 배분  —  메서드 단위 분기', 10.5, True, VIOLET)
for i in range(5):
    px = BAND_X + 16 + i * 88
    rrect(px, R2 + 27, 78, 22, (231, 224, 244))
    text(px + 39, R2 + 31, 'port', 9.5, True, VIOLET, 'ma', mono=True)
text(BAND_X + 16 + 5 * 88 + 10, R2 + 31, '…  실측 25건', 10, False, VIOLET)
cx_disp = LX + (NW + NG) * 2 + NW / 2
d.line([cx_disp * S, (R1 + NH) * S, cx_disp * S, (R2 - 8) * S], fill=(176, 158, 210), width=3 * S)
arrow(cx_disp, R2 - 10, cx_disp, R2 - 2, (176, 158, 210), 3, 7)

# 3행 — 결합 → 검증 → 게이트
R3 = R2 + 58 + 34
node(LX, R3, 'splice_all', '결과 합치기', NAVY)
node(LX + NW + NG, R3, 'validate_all', '정적 검증', MINT)
node(LX + (NW + NG) * 2, R3, 'repair_gate', '조건부 분기', AMBER, 200)
elbow(BAND_X + BAND_W / 2, R2 + 58, LX + NW / 2, R3, (176, 158, 210), 3)
for i in range(2):
    x = LX + NW + (NW + NG) * i
    arrow(x + 2, R3 + NH / 2, x + NG - 2, R3 + NH / 2, (150, 162, 158), 3, 6)
text(LX + (NW + NG) * 2 + 210, R3 + 8, '회차 상한 2', 11, True, AMBER)

# 자가 교정 순환 — 왼쪽 여백으로 돌려보낸다.
# 통과 경로와 같은 공간을 쓰면 선이 겹쳐 어느 쪽이 순환인지 읽히지 않는다.
LOOP_Y = R3 + NH + 24
gx_loop = LX + (NW + NG) * 2 + 46
RAIL = 60
AM = (190, 140, 90)
d.line([gx_loop * S, (R3 + NH) * S, gx_loop * S, LOOP_Y * S], fill=AM, width=3 * S)
d.line([gx_loop * S, LOOP_Y * S, RAIL * S, LOOP_Y * S], fill=AM, width=3 * S)
d.line([RAIL * S, LOOP_Y * S, RAIL * S, (R3 + NH / 2) * S], fill=AM, width=3 * S)
arrow(RAIL, R3 + NH / 2, LX - 2, R3 + NH / 2, AM, 3, 7)
text(LX + 12, LOOP_Y + 9,
     '수리 대상 있음 + 예산 남음  →  후보 N개 생성  →  검증기가 채점  →  재검증',
     10.5, False, AMBER)

# 4행 — 통과 경로. 게이트 바로 아래로 내려 순환선과 만나지 않게 한다.
R4 = LOOP_Y + 42
node(LX + (NW + NG) * 2, R4, 'equivalence_check_all', '동작 일치', MINT)
node(LX + (NW + NG) * 2 + NW + NG + 12, R4, 'scan_all', '품질·취약점 검사', MINT)
gx_pass = LX + (NW + NG) * 2 + 150
d.line([gx_pass * S, (R3 + NH) * S, gx_pass * S, (R4 - 10) * S], fill=(150, 162, 158), width=2 * S)
arrow(gx_pass, R4 - 12, gx_pass, R4 - 2, (150, 162, 158), 2, 7)
x_eq = LX + (NW + NG) * 2 + NW
arrow(x_eq + 2, R4 + NH / 2, x_eq + NG + 10, R4 + NH / 2, (150, 162, 158), 3, 6)
text(gx_pass + 14, R3 + NH + 12, '통과 또는 예산 소진', 10.5, False, INK2)

# ────────────────────────────────────────────────── 상태 필드 패널
PX = 48 + FLOW_W + 26
PW = W / S - PX - 48
rrect(PX, FY, PW, FLOW_H, PALE)
text(PX + 18, FY + 16, '상태 (State) 주요 필드', 13, True, NAVY)
fields = [
    ('plans', '화면별 변환 계획'),
    ('skel_method_calls', '호출 관계도 — 계약의 원천'),
    ('skel_issues', '생성 시점 이슈'),
    ('port_results', '병렬 포팅 결과 (누적)'),
    ('validation_results', '검증 결과'),
    ('repair_round', '자가 교정 회차 (상한 2)'),
    ('equivalence_result', '동작 일치 결과'),
]
yy = FY + 48
for k, v in fields:
    text(PX + 18, yy, k, 10.5, True, INK, mono=True)
    text(PX + 18, yy + 15, v, 10, False, INK2)
    yy += 36

text(PX + 18, FY + FLOW_H - 46, '저장 상태는 여기 없다', 10.5, True, AMBER)
text(PX + 18, FY + FLOW_H - 28, '승인 게이트를 지난 뒤 별도 경로로 기록된다', 10, False, INK2)

# ────────────────────────────────────────────────── 승인 게이트
AY = FY + FLOW_H + 26
rrect(48, AY, W / S - 96, 52, AMBER)
text(W / (2 * S), AY + 17, '사람 승인 게이트  —  저장은 그래프 밖에서, 승인 후에만',
     15, True, WHITE, 'ma')

# ────────────────────────────────────────────────── 범례
LY = AY + 72
sw = 15
lx = 48
for col, label in ((MINT, '규칙 기반 (LLM 호출 0회)'), (NAVY, 'LLM 호출'),
                   (AMBER, '분기 · 승인'), (VIOLET, '병렬 분기')):
    rrect(lx, LY, sw, sw, col)
    text(lx + sw + 8, LY + 1, label, 11, False, INK2)
    lx += sw + 16 + len(label) * 8.4
text(W / S - 48, LY + 1,
     '순환은 repair_gate 한 곳뿐이고 상한이 있다 — 자유 탐색 루프를 만들지 않는다',
     11, True, NAVY, 'ra')

out = r'C:/Users/10982/project/TransGscm/docs/weekly/assets/workflow-orchestration.png'
img.resize((W // S, H // S), Image.LANCZOS).save(out, 'PNG')
print('saved:', out)
