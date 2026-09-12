# -*- coding: utf-8 -*-
"""워크시트의 고정폭 표를 '표 복사' 버튼용 TSV로 뽑아 심는다.

플랫폼의 GRID 입력칸은 **탭으로 구분된 텍스트**를 붙여넣어야 칸이 갈린다. 공백 정렬은
아무리 예쁘게 맞춰도 한 칸에 전부 들어간다. 화면에 보이는 <pre>는 그대로 두고(읽기용),
붙여넣기용 TSV만 따로 만들어 data-tsv에 담는다 — 보이는 것과 복사되는 것을 분리한다.

열 경계는 두 가지로 잡는다.
  1) 구분선에 '+'나 '|'가 있으면 그 위치가 정답이다.
  2) 없으면 '공백 2칸 이상'으로 자른다. 이어지는 줄(앞 칸이 비었거나 칸 수가 모자란 줄)은
     앞 행의 해당 칸에 붙인다 - 별도 행으로 내보내면 GRID에 빈 행이 생긴다.

실행: python tools/add_grid_copy.py [--dump]
"""
import html
import io
import re
import sys
import unicodedata
from pathlib import Path

# 콘솔 기본 코드페이지(cp949)에서 박스 문자·em dash가 UnicodeEncodeError를 낸다.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "weekly" / "assets" / "submission-worksheet.html"

SEP = re.compile(r"^[\s]*[─\-]{4,}[─\-+│|]*\s*$")
NEWPARA = re.compile(r"^\s{0,2}\d+[.)]\s|^\S")


def _w(ch: str) -> int:
    """표시 폭. 'A'(모호)도 2칸으로 센다.

    `—`·`·`·`↳` 는 east_asian_width가 'A'(ambiguous)를 돌려주지만 한국어 터미널·에디터에서는
    두 칸으로 그려진다. 1칸으로 세면 그 줄만 경계가 밀려 값이 쪼개진다 - 실제로 `PASS`가
    `P`와 `ASS`로 갈리는 것을 확인했다.
    """
    return 2 if unicodedata.east_asian_width(ch) in "WFA" else 1


def _starts(line: str) -> list[int]:
    out, col = [], 0
    for ch in line:
        out.append(col)
        col += _w(ch)
    return out


def _slice(line: str, bounds: list[int]) -> list[str]:
    st = _starts(line)
    cells = []
    for i, b0 in enumerate(bounds):
        b1 = bounds[i + 1] if i + 1 < len(bounds) else 10 ** 6
        cells.append("".join(line[k] for k in range(len(line)) if b0 <= st[k] < b1).strip())
    return cells


def _split2(line: str) -> list[str]:
    return [c for c in re.split(r"\s{2,}", line.strip()) if c]


def _parse(lines: list[str], hi: int, si: int):
    header, sepline = lines[hi], lines[si]
    # 이 표의 데이터 행이 0열에서 시작하면 '들여쓰기 없음'은 새 문단 신호가 아니다.
    first_row = lines[si + 1] if si + 1 < len(lines) else ""
    rows_at_zero = bool(first_row) and not first_row.startswith(" ")
    pipe = "|" in header
    bounds = None
    if pipe:
        cols = [c.strip() for c in header.split("|")]
    elif "+" in sepline:
        st = _starts(sepline)
        bounds = [0] + [st[k] + 1 for k, ch in enumerate(sepline) if ch == "+"]
        cols = _slice(header, bounds)
    else:
        cols = _split2(header)
    n = len(cols)

    rows, j = [], si + 1
    while j < len(lines):
        ln = lines[j]
        if not ln.strip():
            nxt = lines[j + 1] if j + 1 < len(lines) else ""
            nxt2 = lines[j + 2] if j + 2 < len(lines) else ""
            new_para = re.match(r"^\s{0,2}\d+[.)]\s", nxt) or (
                not rows_at_zero and re.match(r"^\S", nxt))
            if not nxt.strip() or new_para or SEP.match(nxt2):
                break
            j += 1
            continue
        if SEP.match(ln):
            j += 1
            continue
        if pipe:
            cells = [c.strip() for c in ln.split("|")]
        elif bounds is not None:
            cells = _slice(ln, bounds)
        else:
            cells = _split2(ln)
        cells = (cells + [""] * n)[:n]

        # 이어지는 줄은 첫 칸이 비어 있을 때만 앞 행에 붙인다. 위치를 추정해 붙이면
        # 값이 엉뚱한 칸으로 가거나 쪼개진다(실측으로 확인).
        if rows and cells[0] == "" and any(cells[1:]):
            for k in range(1, n):
                if cells[k]:
                    rows[-1][k] = (rows[-1][k] + " " + cells[k]).strip()
        else:
            rows.append(cells)
        j += 1
    return cols, rows, j


def tables_in(body: str):
    """**열 경계가 확정되는 표만** 돌려준다.

    구분선에 '+'가 있거나 머리행에 '|'가 있으면 경계가 정확하다. 공백 정렬만 된 표는
    '공백 2칸' 추정으로 자를 수밖에 없는데, 여러 줄에 걸친 셀에서 값이 쪼개지는 것을
    실측으로 확인했다(`PASS`가 `P`/`ASS`로 갈렸다). **잘못 갈린 TSV를 붙여넣는 것은 한
    칸에 다 들어가는 것보다 나쁘다** - 확신이 없으면 버튼을 달지 않는다.
    """
    lines = body.split("\n")
    out, i = [], 0
    while i < len(lines):
        if (i + 1 < len(lines) and SEP.match(lines[i + 1]) and lines[i].strip()
                and ("+" in lines[i + 1] or "|" in lines[i])):
            cols, rows, nxt = _parse(lines, i, i + 1)
            if len(cols) >= 2 and rows:
                out.append((cols, rows))
                i = nxt
                continue
        i += 1
    return out


def to_tsv(tables) -> str:
    blocks = []
    for cols, rows in tables:
        lines = ["\t".join(cols)] + ["\t".join(r) for r in rows]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


FIELD_RE = re.compile(r'(<div class="field">.*?</div>\s*\n)', re.S)


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    dump = "--dump" in sys.argv
    pres = re.findall(r"<pre>(.*?)</pre>", src, re.S)

    total = 0
    for idx, body in enumerate(pres):
        tabs = tables_in(html.unescape(body))
        if not tabs:
            continue
        total += len(tabs)
        if dump:
            for cols, rows in tabs:
                print(f"\n=== pre#{idx} · 열 {len(cols)} · 행 {len(rows)} ===")
                print("  " + " | ".join(cols))
                for r in rows[:3]:
                    print("   " + " | ".join(r))
                if len(rows) > 3:
                    print(f"   … {len(rows) - 3}행 더")
    print(f"\n표 {total}개 검출")
    if dump:
        return 0

    # field 블록 단위로 처리한다. 정규식으로 field 하나를 통째로 잡으려 하면 .fhead의
    # 닫는 </div>에서 먼저 끊긴다 - 그래서 여는 태그로 쪼갠 뒤 각 조각을 본다.
    MARK = '<div class="field">'
    parts = src.split(MARK)
    rebuilt = [parts[0]]
    for chunk in parts[1:]:
        pm = re.search(r"<pre>(.*?)</pre>", chunk, re.S)
        tabs = tables_in(html.unescape(pm.group(1))) if pm else []
        if not tabs:
            rebuilt.append(MARK + chunk)
            continue
        tsv = html.escape(to_tsv(tabs), quote=True)
        chunk = chunk.replace(
            '<button class="copy" type="button">복사</button>',
            '<button class="copy" type="button">복사</button>'
            '<button class="copygrid" type="button">표 복사</button>', 1)
        rebuilt.append(f'<div class="field" data-tsv="{tsv}">' + chunk)
    out = "".join(rebuilt)
    n = out.count('class="copygrid"')
    TARGET.write_text(out, encoding="utf-8")
    print(f"'표 복사' 버튼 {n}개 삽입")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
