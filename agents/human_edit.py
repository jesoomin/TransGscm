"""사람 수정 라인 비율(HUMAN_EDIT_RATIO) 측정.

멘토 코멘트 §H가 **"가장 중요한 대리 지표"** 로 꼽은 값이다 — 자동 생성된 코드 중 사람이 리뷰하며
실제로 손댄 라인의 비율. 실제 공수 절감률에 가장 가까운 관측치라 ROI 보고에 그대로 쓸 수 있다.

그동안 `CONV_FILE.HUMAN_EDIT_RATIO` 컬럼만 있고 **기록 지점이 코드에 하나도 없었다.** 즉
"측정 시점이 안 왔다"가 아니라 **측정할 수단 자체가 없었다.** 이 모듈이 그 수단이다.

**측정 방식**
  1. 승인·저장 시점에 생성물 원본을 `tracking/generated-snapshots/{화면}/`에 스냅샷으로 남긴다.
  2. 나중에 사람이 `pilot/`의 파일을 고친 뒤 `measure_screen()`을 부르면, 스냅샷과 현재 파일을
     줄 단위로 비교해 **변경/추가/삭제된 라인 수 / 생성 라인 수**를 낸다.
  3. 스냅샷이 없으면 `미측정`이다 — 0%로 보고하지 않는다. "안 고쳤다"와 "못 쟀다"는 다르다.

**왜 git diff로 안 하나**: `pilot/`은 사람이 커밋 전에 여러 번 손댈 수 있고, 재생성으로 덮어써질
수도 있다. 커밋 경계가 아니라 **"생성 직후"** 라는 정확한 기준선이 필요해서 스냅샷을 따로 둔다.

**세는 규칙** (`difflib.SequenceMatcher` 기준)
  - `replace`: 양쪽 중 **큰 쪽**을 센다(3줄을 1줄로 줄인 것도 3줄을 본 것이다)
  - `delete` / `insert`: 해당 줄 수를 그대로
  - 공백만 다른 줄은 변경으로 세지 않는다(포맷터 실행이 지표를 흔들지 않도록)
"""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = _PROJECT_ROOT / "tracking" / "generated-snapshots"
# 리뷰를 거친 산출물을 두는 곳. `pilot/`은 사람이 "승인하고 저장"을 눌러야만 파일이 생기는
# 곳이라(그 보장을 깨면 안 된다), 승인 전 리뷰 결과는 여기에 따로 둔다.
REVIEWED_DIR = _PROJECT_ROOT / "tracking" / "reviewed"
# 리뷰본이 «어느 생성분»을 보고 만들어졌는지 적어두는 파일. 이게 없으면 파이프라인을 다시 돌려
# 스냅샷이 갱신됐을 때, 옛 리뷰본과 새 생성물을 비교해 엉뚱한 수치가 나온다 - 실제로 그 일이
# 일어나서(4.34% -> 15.3%) 원인을 찾는 데 시간을 썼다. 그때는 사람이 눈치채야 했지만 이제는
# 측정기가 스스로 "이 리뷰본은 낡았다"고 말한다.
REVIEW_META = "_review.json"


def file_digest(text: str) -> str:
    """줄바꿈 차이(CRLF/LF)에 흔들리지 않는 내용 해시."""
    return hashlib.sha256("\n".join(text.splitlines()).encode("utf-8")).hexdigest()


def snapshot_digests(screen_id: str, snapshot_dir: Path | None = None) -> dict[str, str]:
    """생성 스냅샷의 파일별 내용 해시. 리뷰 시작 시점을 고정하는 데 쓴다."""
    base = (snapshot_dir or SNAPSHOT_DIR) / screen_id
    if not base.is_dir():
        return {}
    return {p.name: file_digest(p.read_text(encoding="utf-8", errors="replace"))
            for p in sorted(base.iterdir())
            if p.is_file() and p.name not in ("_manifest.json", REVIEW_META)}


def read_review_meta(screen_id: str, reviewed_dir: Path | None = None) -> dict | None:
    meta = (reviewed_dir or REVIEWED_DIR) / screen_id / REVIEW_META
    if not meta.is_file():
        return None
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def review_staleness(screen_id: str, snapshot_dir: Path | None = None,
                     reviewed_dir: Path | None = None) -> list[str]:
    """리뷰본과 현재 생성분이 어긋난 부분을 파일 단위로 돌려준다(빈 리스트 = 최신)."""
    meta = read_review_meta(screen_id, reviewed_dir)
    if meta is None:
        return []
    base = meta.get("base_digests") or {}
    now = snapshot_digests(screen_id, snapshot_dir)
    drift = []
    for fname in sorted(set(base) | set(now)):
        if base.get(fname) != now.get(fname):
            drift.append(fname)
    return drift


@dataclass
class FileEdit:
    file_name: str
    generated_lines: int
    edited_lines: int

    @property
    def ratio(self) -> float:
        return self.edited_lines / self.generated_lines if self.generated_lines else 0.0


@dataclass
class ScreenEdit:
    screen_id: str
    measured: bool
    files: list[FileEdit] = field(default_factory=list)
    note: str = ""

    @property
    def generated_lines(self) -> int:
        return sum(f.generated_lines for f in self.files)

    @property
    def edited_lines(self) -> int:
        return sum(f.edited_lines for f in self.files)

    @property
    def ratio(self) -> float | None:
        if not self.measured or not self.generated_lines:
            return None
        return self.edited_lines / self.generated_lines


def _norm(lines: list[str]) -> list[str]:
    """공백만 다른 줄을 같은 줄로 보게 정규화한다(포맷터가 지표를 흔들지 않도록)."""
    return [" ".join(l.split()) for l in lines]


def snapshot_screen(screen_id: str, files: dict[str, str],
                    snapshot_dir: Path | None = None) -> Path:
    """승인·저장 시점의 생성물을 스냅샷으로 남긴다. 이후 측정의 기준선이 된다."""
    base = (snapshot_dir or SNAPSHOT_DIR) / screen_id
    base.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (base / fname).write_text(content, encoding="utf-8")
    (base / "_manifest.json").write_text(
        json.dumps({"screen_id": screen_id, "files": sorted(files)},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return base


def count_edited_lines(generated: str, current: str) -> int:
    """생성물 대비 현재 내용에서 사람이 손댄 라인 수."""
    a, b = _norm(generated.splitlines()), _norm(current.splitlines())
    edited = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            edited += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            edited += i2 - i1
        elif tag == "insert":
            edited += j2 - j1
    return edited


def measure_screen(screen_id: str, current_files: dict[str, str],
                   snapshot_dir: Path | None = None) -> ScreenEdit:
    """스냅샷과 현재 파일을 비교한다. 스냅샷이 없으면 **미측정**으로 돌려준다."""
    base = (snapshot_dir or SNAPSHOT_DIR) / screen_id
    if not base.is_dir():
        return ScreenEdit(screen_id, measured=False,
                          note="생성 시점 스냅샷이 없습니다 — 저장 시 snapshot_screen()이 호출돼야 합니다")

    # 리뷰본이 지금 스냅샷이 아니라 예전 생성분을 보고 만들어졌으면 비교 자체가 성립하지 않는다.
    # 0%도 아니고 큰 수치도 아니라 **미측정**이다 - "안 고쳤다"와 "못 쟀다"를 섞지 않는 것과 같은
    # 이유로, "낡은 기준으로 쟀다"도 섞지 않는다.
    # 리뷰본 폴더는 있는데 기준선 기록(_review.json)이 없으면 «무엇을 보고 고쳤는지»를 알 수
    # 없다. 이 상태에서 나온 숫자는 지난 세션에 실제로 사람을 헷갈리게 했다 - 재생성 뒤에도
    # 옛 리뷰본이 남아 30% 가까운 값을 태연히 보고했다. 모르면 모른다고 한다.
    reviewed = REVIEWED_DIR / screen_id
    if reviewed.is_dir() and not (reviewed / REVIEW_META).is_file():
        return ScreenEdit(
            screen_id, measured=False,
            note=("리뷰본의 기준선 기록이 없습니다(_review.json) — 어느 생성분을 보고 고친 "
                  f"것인지 알 수 없어 측정하지 않습니다. `python -m agents.review open "
                  f"{screen_id}`로 리뷰를 다시 시작하세요."))

    drift = review_staleness(screen_id, snapshot_dir)
    if drift:
        return ScreenEdit(
            screen_id, measured=False,
            note=(f"리뷰본이 이전 생성분 기준입니다 — 그 뒤 재생성으로 {len(drift)}개 파일이 "
                  f"바뀌었습니다({', '.join(drift[:3])}"
                  f"{' 외 %d건' % (len(drift) - 3) if len(drift) > 3 else ''}). "
                  f"`python -m agents.review open {screen_id}`로 리뷰를 다시 시작하세요."))

    out = ScreenEdit(screen_id, measured=True)
    for snap in sorted(base.glob("*")):
        if snap.name in ("_manifest.json", REVIEW_META) or not snap.is_file():
            continue
        generated = snap.read_text(encoding="utf-8", errors="replace")
        current = current_files.get(snap.name)
        if current is None:
            # 생성됐던 파일이 지금 없다 = 사람이 지웠다. 전량 변경으로 센다.
            n = generated.count("\n") + 1
            out.files.append(FileEdit(snap.name, n, n))
            continue
        out.files.append(FileEdit(
            snap.name, generated.count("\n") + 1, count_edited_lines(generated, current)))
    if not out.files:
        out.measured = False
        out.note = "스냅샷 폴더는 있으나 비교할 파일이 없습니다"
    return out


def measure_all(current_by_screen: dict[str, dict[str, str]],
                snapshot_dir: Path | None = None) -> dict:
    """여러 화면을 한 번에 측정하고 집계한다.

    반환의 `ratio`는 **측정된 화면만** 대상으로 한다 — 미측정 화면을 0%로 섞어 넣으면 지표가
    좋아 보이게 왜곡된다(이 프로젝트가 리뷰 축소율에서 이미 한 번 겪은 실수).
    """
    screens = {sid: measure_screen(sid, files, snapshot_dir)
               for sid, files in current_by_screen.items()}
    measured = [s for s in screens.values() if s.measured]
    gen = sum(s.generated_lines for s in measured)
    edited = sum(s.edited_lines for s in measured)
    return {
        "measured_screens": len(measured),
        "unmeasured_screens": len(screens) - len(measured),
        "generated_lines": gen,
        "edited_lines": edited,
        "human_edit_ratio": round(edited / gen, 4) if gen else None,
        "per_screen": {
            sid: {"measured": s.measured, "ratio": s.ratio,
                  "generated_lines": s.generated_lines, "edited_lines": s.edited_lines,
                  "note": s.note}
            for sid, s in screens.items()
        },
    }


def save_reviewed(screen_id: str, files: dict[str, str],
                  reviewed_dir: Path | None = None) -> Path:
    """리뷰를 마친 산출물을 기록한다. 측정의 «현재 상태» 쪽 입력이 된다."""
    base = (reviewed_dir or REVIEWED_DIR) / screen_id
    base.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (base / fname).write_text(content, encoding="utf-8")
    return base


def open_review(screen_id: str, reviewer: str = "",
                snapshot_dir: Path | None = None,
                reviewed_dir: Path | None = None,
                reset: bool = False) -> tuple[Path, list[str]]:
    """생성분을 리뷰 작업본으로 펼치고, 그 시점의 기준선을 고정한다.

    이미 사람이 손댄 파일은 **덮어쓰지 않는다**(reset=True일 때만 덮어쓴다) - 리뷰 도중 파이프라인을
    다시 돌렸다고 사람 작업이 날아가면 안 된다. 대신 어떤 파일이 새 생성분과 갈라졌는지 돌려줘서
    사람이 직접 판단하게 한다.
    """
    src = (snapshot_dir or SNAPSHOT_DIR) / screen_id
    if not src.is_dir():
        raise FileNotFoundError(f"생성 스냅샷이 없습니다: {src}")
    dst = (reviewed_dir or REVIEWED_DIR) / screen_id
    dst.mkdir(parents=True, exist_ok=True)

    kept: list[str] = []
    for p in sorted(src.iterdir()):
        if not p.is_file() or p.name in ("_manifest.json", REVIEW_META):
            continue
        target = dst / p.name
        generated = p.read_text(encoding="utf-8", errors="replace")
        if target.exists() and not reset:
            if file_digest(target.read_text(encoding="utf-8", errors="replace")) != file_digest(generated):
                kept.append(p.name)
                continue
        target.write_text(generated, encoding="utf-8")

    (dst / REVIEW_META).write_text(
        json.dumps({
            "screen_id": screen_id,
            "opened_at": datetime.now().isoformat(timespec="seconds"),
            "reviewer": reviewer,
            "accepted_at": None,
            "base_digests": snapshot_digests(screen_id, snapshot_dir),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dst, kept


def accept_review(screen_id: str, reviewer: str = "",
                  reviewed_dir: Path | None = None) -> dict:
    """사람이 리뷰를 마쳤다고 표시한다. 이후 이 화면의 «현재» 산출물은 리뷰본이 된다."""
    meta = read_review_meta(screen_id, reviewed_dir)
    if meta is None:
        raise FileNotFoundError(
            f"{screen_id}: 리뷰가 시작되지 않았습니다 — 먼저 `review open {screen_id}`를 실행하세요")
    meta["accepted_at"] = datetime.now().isoformat(timespec="seconds")
    if reviewer:
        meta["reviewer"] = reviewer
    ((reviewed_dir or REVIEWED_DIR) / screen_id / REVIEW_META).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def load_current_files(screen_id: str) -> dict[str, str]:
    """측정 대상 «현재» 파일을 찾는다 - 리뷰본이 있으면 그걸, 없으면 `pilot/` 저장분을 쓴다."""
    base = REVIEWED_DIR / screen_id
    if base.is_dir():
        return {p.name: p.read_text(encoding="utf-8", errors="replace")
                for p in base.iterdir() if p.is_file() and p.name != REVIEW_META}
    return load_pilot_files(screen_id)


def load_pilot_files(screen_id: str, pilot_root: Path | None = None) -> dict[str, str]:
    """`pilot/` 트리에서 이 화면의 현재 산출물을 파일명 기준으로 모은다."""
    root = pilot_root or (_PROJECT_ROOT / "pilot")
    prefix = screen_id[:1].upper() + screen_id[1:].lower()  # PLA087 -> Pla087
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in root.rglob(f"{prefix}*"):
        if path.is_file():
            out[path.name] = path.read_text(encoding="utf-8", errors="replace")
    return out
