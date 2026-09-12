# -*- coding: utf-8 -*-
"""<pre> 안의 고정폭 표를 진짜 <table>로 바꾼다.

붙여넣을 때 칸이 갈리려면 열이 탭으로 구분돼야 하는데, 공백 정렬은 한 칸에 다 들어간다.
열 경계는 '표시 폭' 기준으로 잡는다 — 한글이 두 칸이라 문자 인덱스로 자르면 어긋난다.
"""
import re
import unicodedata

SEP = re.compile(r'^[\s]*[─\-]{4,}[─\-+│|]*\s*$')


def w(ch):
    return 2 if unicodedata.east_asian_width(ch) in 'WF' else 1


def widths(line):
    """각 문자의 시작 표시열을 돌려준다."""
    out, col = [], 0
    for ch in line:
        out.append(col)
        col += w(ch)
    return out, col


def slice_by_cols(line, bounds):
    """표시열 경계로 자른다."""
    starts, _ = widths(line)
    cells, n = [], len(line)
    for i, b0 in enumerate(bounds):
        b1 = bounds[i + 1] if i + 1 < len(bounds) else 10 ** 6
        buf = ''
        for k in range(n):
            if b0 <= starts[k] < b1:
                buf += line[k]
        cells.append(buf.strip())
    return cells


def header_bounds(header):
    """머리행에서 '공백 2칸 이상' 뒤를 열 시작으로 본다."""
    starts, _ = widths(header)
    bounds, run = [], 0
    for k, ch in enumerate(header):
        if ch == ' ':
            run += 1
        else:
            if run >= 2 or k == 0 or not bounds:
                if not bounds or starts[k] > bounds[-1]:
                    bounds.append(starts[k])
            run = 0
    return bounds


def parse_table(lines, hi, si):
    """hi=머리행 index, si=구분선 index. (헤더, 행들, 끝 index)"""
    header = lines[hi]
    pipe = '|' in header
    if pipe:
        cols = [c.strip() for c in header.split('|')]
        ncol = len(cols)
    else:
        bounds = header_bounds(header)
        cols = slice_by_cols(header, bounds)
        ncol = len(cols)

    rows, j = [], si + 1
    while j < len(lines):
        ln = lines[j]
        if not ln.strip():
            break
        if SEP.match(ln):          # 표 안의 두 번째 구분선 = 구획선
            j += 1
            continue
        if pipe:
            cells = [c.strip() for c in ln.split('|')]
            cells += [''] * (ncol - len(cells))
            cells = cells[:ncol]
        else:
            cells = slice_by_cols(ln, bounds)
        # 이어지는 줄(첫 칸이 비어 있고 뒤에 내용이 있음)은 앞 행에 붙인다
        if rows and cells[0] == '' and any(c for c in cells[1:]):
            for c in range(ncol):
                if cells[c]:
                    rows[-1][c] = (rows[-1][c] + ' ' + cells[c]).strip()
        else:
            rows.append(cells)
        j += 1
    return cols, rows, j


def esc(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def render(cols, rows):
    out = ['<table class="grid"><thead><tr>']
    out += ['<th>%s</th>' % esc(c) for c in cols]
    out.append('</tr></thead><tbody>')
    for r in rows:
        out.append('<tr>' + ''.join('<td>%s</td>' % esc(c) for c in r) + '</tr>')
    out.append('</tbody></table>')
    return ''.join(out)


def convert_block(body):
    """<pre> 본문을 [텍스트|표] 조각 목록으로 나눈다. 표가 없으면 None."""
    lines = body.split('\n')
    pieces, i, found = [], 0, False
    buf = []
    while i < len(lines):
        if i + 1 < len(lines) and SEP.match(lines[i + 1]) and lines[i].strip():
            cols, rows, nxt = parse_table(lines, i, i + 1)
            if len(cols) >= 2 and rows:
                if buf:
                    pieces.append(('pre', '\n'.join(buf).strip('\n')))
                    buf = []
                pieces.append(('table', (cols, rows)))
                found = True
                i = nxt
                continue
        buf.append(lines[i])
        i += 1
    if buf:
        pieces.append(('pre', '\n'.join(buf).strip('\n')))
    return pieces if found else None
