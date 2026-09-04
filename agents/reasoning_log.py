"""파이프라인의 추론 과정을 콘솔에 구조화해서 출력한다.

**왜 필요한가**: `agents/workflow_graph.py`의 LangGraph 파이프라인은 노드마다 실제로 판단을 내린다 -
어떤 메서드를 LLM에 보낼지(규칙 기반으로 되는 건 안 보낸다), 어떤 의존 계약을 프롬프트에 주입할지,
검증 실패를 수리 루프로 되돌릴지 예산을 소진했으니 포기할지. 그런데 이 판단들이 지금까지는
`progress_cb`를 통해 Streamlit UI로만 흘러가서, 터미널에는 아무것도 남지 않았다(이 모듈을 만들기
전 `workflow_graph.py`의 logging/print 호출은 0건이었다). 즉 **추론은 하고 있는데 보이지 않는
상태**였다.

**설계 원칙 — 없는 추론을 지어내지 않는다.**
이 모듈은 로그 문구를 만들어내는 게 아니라 이미 코드가 내린 결정을 그대로 받아 적는다. 호출부는
전부 실제 분기 지점에 붙어 있고, 인자는 그 시점의 실제 값이다. "Planning: 5-step plan generated"
같은 문장을 실제로 5단계 계획을 세우지 않은 곳에 쓰지 않는다.

**사용법**
    from agents.reasoning_log import log
    log.enable()                      # 기본은 꺼짐 - Streamlit 경로는 영향 없음
    log.stage(1, 7, "PLAN", "변환 계획 수립 (LLM 미사용)")
    log.decide("PLA047.fXxx", "LLM 포팅", "계산·분기 존재")
    log.end_stage("계획 파일 3건 고정")

환경변수 `GSCM_REASONING_LOG=1`로도 켤 수 있다(CLI 진입점이 이걸 본다).
"""

from __future__ import annotations

import os
import sys
import threading
import time

# ANSI 색상 - 파이프로 넘길 때(리다이렉션)는 자동으로 끈다. Windows 터미널은 최근 버전이 ANSI를
# 기본 지원하지만, 안 되는 환경도 있어서 GSCM_LOG_COLOR=0으로 강제로 끌 수 있게 뒀다.
def _color_enabled() -> bool:
    if os.environ.get("GSCM_LOG_COLOR") == "0":
        return False
    if os.environ.get("GSCM_LOG_COLOR") == "1":
        return True
    return sys.stdout.isatty()


class _C:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"


# 이벤트 종류별 라벨과 색. 라벨은 고정 폭(8칸)이라 로그가 세로로 정렬돼 영상에서 읽기 쉽다.
_KINDS = {
    "PLAN":     (_C.CYAN,    "PLAN"),      # 계획 수립
    "OBSERVE":  (_C.DIM,     "OBSERVE"),   # 정적 분석으로 관찰한 사실
    "DECIDE":   (_C.MAGENTA, "DECIDE"),    # 분기 판단 (라우팅)
    "CONTEXT":  (_C.BLUE,    "CONTEXT"),   # 프롬프트에 주입한 의존 계약
    "TOOL":     (_C.YELLOW,  "TOOL"),      # 도구 호출 (변환기/검증기/LLM/DB)
    "VALIDATE": (_C.CYAN,    "VALIDATE"),  # 검증 결과
    "REFLECT":  (_C.MAGENTA, "REFLECT"),   # 자기 수정 게이트 판단
    "REPAIR":   (_C.YELLOW,  "REPAIR"),    # 수리 재시도
    "PASS":     (_C.GREEN,   "PASS"),
    "BLOCK":    (_C.RED,     "BLOCK"),
    "RESULT":   (_C.BOLD,    "RESULT"),
}


class ReasoningLog:
    def __init__(self) -> None:
        self._on = os.environ.get("GSCM_REASONING_LOG") == "1"
        self._t0: float | None = None
        self._in_stage = False
        self._color = _color_enabled()
        self._counts: dict[str, int] = {}
        # LangGraph의 Send 병렬 브랜치가 동시에 로그를 쓰면 한 이벤트의 본문과 근거 줄이 서로
        # 끼어들어 뒤섞인다(실제로 발생 - 시연 영상에서 로그가 깨져 보인다). 이벤트 하나를
        # 원자적으로 내보내려고 락을 건다.
        self._lock = threading.Lock()

    # ---- 제어 -------------------------------------------------------------
    def enable(self) -> None:
        self._on = True
        self._color = _color_enabled()

    def disable(self) -> None:
        self._on = False

    @property
    def enabled(self) -> bool:
        return self._on

    def _paint(self, text: str, color: str) -> str:
        return f"{color}{text}{_C.RESET}" if self._color else text

    def _elapsed(self) -> str:
        if self._t0 is None:
            self._t0 = time.time()
        return f"{time.time() - self._t0:5.1f}s"

    def _emit(self, *lines: str) -> None:
        """여러 줄을 한 번에(락 안에서) 내보낸다 - 병렬 브랜치가 이벤트 중간에 끼어들지 못하게."""
        with self._lock:
            sys.stdout.write("".join(l + "\n" for l in lines))
            sys.stdout.flush()

    # ---- 헤더 -------------------------------------------------------------
    def banner(self, title: str, subtitle: str = "") -> None:
        if not self._on:
            return
        self._t0 = time.time()
        bar = "=" * 78
        self._emit("")
        self._emit(self._paint(bar, _C.CYAN))
        self._emit(self._paint(f"  {title}", _C.BOLD))
        if subtitle:
            self._emit(self._paint(f"  {subtitle}", _C.DIM))
        self._emit(self._paint(bar, _C.CYAN))
        self._emit("")

    # ---- 단계 -------------------------------------------------------------
    def stage(self, no: int, total: int, kind: str, title: str) -> None:
        """단계 시작. 영상에서 '지금 몇 단계인지'가 항상 보이도록 번호를 붙인다."""
        if not self._on:
            return
        if self._in_stage:
            self._emit(self._paint("        └─", _C.DIM))
        self._in_stage = True
        head = self._paint(f"STAGE {no}/{total}", _C.BOLD)
        label = self._paint(kind, _KINDS.get(kind, (_C.CYAN, kind))[0])
        self._emit(f"[{self._elapsed()}] ┌─ {head}  {label}  {title}")

    def end_stage(self, summary: str = "") -> None:
        if not self._on or not self._in_stage:
            return
        self._in_stage = False
        if summary:
            self._emit(f"[{self._elapsed()}] └─ {self._paint(summary, _C.GREEN)}")
        else:
            self._emit(self._paint("        └─", _C.DIM))

    # ---- 이벤트 -----------------------------------------------------------
    def event(self, kind: str, message: str, reason: str = "") -> None:
        """단계 안의 이벤트 1건. `reason`이 있으면 다음 줄에 들여써서 근거를 보여준다 -
        '무엇을 했나'만이 아니라 '왜 그렇게 판단했나'가 보이게 하는 게 이 로그의 목적이다."""
        if not self._on:
            return
        self._counts[kind] = self._counts.get(kind, 0) + 1
        color, label = _KINDS.get(kind, (_C.RESET, kind))
        tag = self._paint(f"{label:<8}", color)
        prefix = "│ " if self._in_stage else "  "
        head = f"[{self._elapsed()}] {prefix} {tag} {message}"
        if reason:
            pad = " " * 9 + prefix + " " + " " * 9
            self._emit(head, self._paint(f"{pad}↳ {reason}", _C.DIM))
        else:
            self._emit(head)

    # 자주 쓰는 축약형 ------------------------------------------------------
    def plan(self, message: str, reason: str = "") -> None:
        self.event("PLAN", message, reason)

    def observe(self, message: str, reason: str = "") -> None:
        self.event("OBSERVE", message, reason)

    def decide(self, subject: str, choice: str, reason: str = "") -> None:
        self.event("DECIDE", f"{subject} → {choice}", reason)

    def context(self, message: str, reason: str = "") -> None:
        self.event("CONTEXT", message, reason)

    def tool(self, name: str, detail: str = "", reason: str = "") -> None:
        self.event("TOOL", f"{name}({detail})" if detail else name, reason)

    def validate(self, message: str, reason: str = "") -> None:
        self.event("VALIDATE", message, reason)

    def reflect(self, message: str, reason: str = "") -> None:
        self.event("REFLECT", message, reason)

    def repair(self, message: str, reason: str = "") -> None:
        self.event("REPAIR", message, reason)

    def ok(self, message: str, reason: str = "") -> None:
        self.event("PASS", message, reason)

    def block(self, message: str, reason: str = "") -> None:
        self.event("BLOCK", message, reason)

    # ---- 마무리 -----------------------------------------------------------
    def summary(self, rows: list[tuple[str, str]], title: str = "실행 요약") -> None:
        """마지막 성과 요약표. 시연 영상 4:30~5:00 구간('수치로 정리')에 그대로 쓰인다."""
        if not self._on:
            return
        if self._in_stage:
            self.end_stage()
        width = max((len(k) for k, _ in rows), default=10)
        bar = "=" * 78
        self._emit("")
        self._emit(self._paint(bar, _C.CYAN))
        self._emit(self._paint(f"  {title}", _C.BOLD))
        self._emit(self._paint(bar, _C.CYAN))
        for k, v in rows:
            self._emit(f"  {k:<{width}}  {self._paint(str(v), _C.BOLD)}")
        self._emit(self._paint(bar, _C.CYAN))
        self._emit("")


log = ReasoningLog()
