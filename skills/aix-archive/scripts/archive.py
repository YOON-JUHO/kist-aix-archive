#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIST AI 아카이브(BBS9157) 검색/요약 헬퍼 — 의존성 없음(순수 표준 라이브러리).

Tampermonkey 수집기가 떨군 bbs9157_harvest.json 을 읽어서
  - 최근 글 목록(list)
  - 질문 기반 관련 글 검색(search, 한글+영문 BM25-lite)
  - 특정 글 본문 전체 출력(show)
  - 데이터 통계(stats)
를 제공한다. Claude(또는 사람)가 이 출력을 읽고 한줄평/요약/추천을 만든다.

사용 예:
  python archive.py stats
  python archive.py list --recent 10
  python archive.py list --writer 이제현 --since 2026-05-01
  python archive.py search "클로드 코드 스킬 설치" --top 5
  python archive.py show NEW17809704280080011
  python archive.py show 1        # list/search 결과의 순번으로도 지정 가능

데이터 소스 우선순위:
  1) --data <경로>  또는  환경변수 AIX_ARCHIVE_JSON  (강제 지정)
  2) 원내 공유 서버에서 최신본을 가져와 캐시  — 주소는 AIX_ARCHIVE_URL 또는 set-url 로 저장
  3) 로컬 자동 탐색(이전 캐시, ~/Downloads 등) 중 글 최신 날짜가 가장 앞선 파일
서버에서 받아오면 한 명만 수집해도 모든 사용자가 같은 최신 데이터를 본다.
서버가 닿지 않으면 자동으로 로컬 폴백한다.
서버 주소는 원내 게시판 공지에서 받아 `archive.py set-url <주소>` 로 한 번 저장한다.
"""
import argparse
import glob
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter

# 공유 데이터 허브 주소는 코드에 넣지 않는다(공개 저장소). 다음 순서로 찾는다:
#   1) 환경변수 AIX_ARCHIVE_URL
#   2) 설정 파일 ~/.aix-archive-config.json 의 "url"
# 둘 다 없으면 서버 연동을 끄고 로컬 캐시/파일만 사용한다.
# 주소는 원내 게시판 공지(Assemble 등)에서 받아 `archive.py set-url <주소>` 로 한 번 저장한다.
_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".aix-archive-config.json")
_CACHE_PATH = os.path.join(os.path.expanduser("~"), ".aix-archive-cache.json")
_CACHE_TTL = 120  # 초. 한 질문 내 여러 번 호출돼도 이 시간 안엔 재요청 안 함.


def _resolve_url():
    """서버 주소를 환경변수 → 설정 파일 순으로 찾는다. 없으면 None(서버 연동 끔)."""
    env = os.environ.get("AIX_ARCHIVE_URL")
    if env is not None:
        return env or None  # 빈 문자열이면 명시적으로 끔
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return (json.load(f).get("url") or "").strip() or None
    except Exception:
        return None

# ----------------------------------------------------------------------------- 데이터 로딩

# 그룹웨어 본문 꼬리에 붙는 UI/스크립트 찌꺼기 절단 마커
_TAIL_MARKERS = (
    "의견(", "의견쓰기", "의견추가", "인쇄 답글쓰기", "if( window._menuGbn",
    "jQuery('#commentCnt", "PC저장 게시판구독", "URL복사 메일전달",
)


def clean_text(t):
    t = (t or "").replace("\ufffd", "").strip()
    cut = len(t)
    for m in _TAIL_MARKERS:
        p = t.find(m)
        if p != -1:
            cut = min(cut, p)
    return t[:cut].strip()


def _forced_paths(explicit):
    """사용자가 명시한 경로(--data) / 환경변수 — 있으면 무조건 이걸 쓴다."""
    if explicit:
        yield explicit
    env = os.environ.get("AIX_ARCHIVE_JSON")
    if env:
        yield env


def _auto_paths():
    """자동 탐색 대상. 이 중 '가장 최근에 수정된' 파일을 고른다(=가장 최근 다운로드본)."""
    paths = []
    here = os.path.dirname(os.path.abspath(__file__))
    paths.append(os.path.join(here, "..", "data", "bbs9157_harvest.json"))  # 번들 스냅샷
    home = os.path.expanduser("~")
    for d in (os.getcwd(), os.path.join(home, "Downloads"), os.path.join(home, "다운로드"), home):
        # bbs9157_harvest.json, bbs9157_harvest (2).json 등 다운로드 변형 모두 포함
        paths.extend(glob.glob(os.path.join(d, "bbs9157_harvest*.json")))
    return paths


def _read(p):
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    arts = raw.get("articles", raw if isinstance(raw, dict) else {})
    out = []
    for k, a in arts.items():
        if not isinstance(a, dict):
            continue
        if a.get("ok") is False:
            continue
        text = clean_text(a.get("text"))
        if not text and not (a.get("subject") or "").strip():
            continue
        out.append({
            "id": a.get("id") or k,
            "subject": (a.get("subject") or "").strip(),
            "writer": (a.get("writer") or "").strip(),
            "date": (a.get("date") or "").strip(),
            "bbsName": (a.get("bbsName") or "").strip(),
            "text": text,
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out, os.path.abspath(p)


def _refresh_server_cache():
    """공유 서버에서 최신본을 받아 로컬 캐시에 저장하고 그 경로를 돌려준다.
    서버가 닿지 않거나 꺼져 있으면 None(또는 기존 캐시)을 돌려줘 로컬 폴백되게 한다."""
    url = _resolve_url()
    if not url:  # 빈 문자열 등으로 끄면 서버 연동 안 함
        return None
    # 캐시가 충분히 최신이면(같은 질문 내 반복 호출) 재요청 생략
    try:
        if os.path.isfile(_CACHE_PATH) and (time.time() - os.path.getmtime(_CACHE_PATH)) < _CACHE_TTL:
            return _CACHE_PATH
    except OSError:
        pass
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            raw = r.read()
        json.loads(raw)  # 유효성 검증(깨진 응답 캐시 방지)
        with open(_CACHE_PATH, "wb") as f:
            f.write(raw)
        return _CACHE_PATH
    except Exception:
        # 실패 시 기존 캐시가 있으면 그거라도 쓰고, 없으면 로컬 폴백
        return _CACHE_PATH if os.path.isfile(_CACHE_PATH) else None


def _content_key(p):
    """파일 '내용' 기준 최신도 키: (글 최신 날짜, 파일 수정시각).
    파일을 언제 복사/다운로드했는지(mtime)가 아니라, 안에 담긴 글이 며칠자까지인지로 비교한다.
    날짜 문자열('2026-06-09 11:00:28.0' 형식)은 사전순 비교가 곧 시간순 비교다.
    깨진 파일은 최하위로 밀어 선택되지 않게 한다."""
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        arts = raw.get("articles", raw if isinstance(raw, dict) else {})
        max_date = ""
        for a in arts.values():
            if isinstance(a, dict) and a.get("ok") is not False:
                d = (a.get("date") or "").strip()
                if d > max_date:
                    max_date = d
        mtime = os.path.getmtime(p)
        return (max_date, mtime)
    except Exception:
        return ("", -1.0)


def load_articles(explicit=None):
    # 1) --data / 환경변수 파일이 있으면 그걸 강제 사용
    for p in _forced_paths(explicit):
        if p and os.path.isfile(p):
            return _read(p)
    # 2) 공유 서버에서 최신본을 받아 캐시(성공 시 보통 이게 가장 최신이 된다)
    server_cache = _refresh_server_cache()
    # 3) 자동 탐색: 서버 캐시 + 로컬 후보 중 '담긴 글이 가장 최신'인 파일 선택
    #    (mtime 비교는 오래된 사본을 복사만 해도 이겨버리는 함정이 있어 내용 기준으로 비교)
    cands = ([server_cache] if server_cache else []) + _auto_paths()
    found = [p for p in cands if p and os.path.isfile(p)]
    if found:
        newest = max(found, key=_content_key)
        return _read(newest)
    return None, None


def die_no_data():
    sys.stderr.write(
        "[archive] 게시판 데이터를 아직 받지 못했습니다.\n"
        "  이 스킬은 원내 공유 서버에서 데이터를 받아옵니다. 다음을 확인해 주세요.\n"
        "  1) 서버 주소가 설정되어 있는지: archive.py set-url <주소>\n"
        "     (주소는 원내 게시판 'AI 아카이브'/Assemble 공지에서 받으세요)\n"
        "  2) 원내망(KIST 내부 네트워크)에 연결된 상태에서 한 번 실행했는지\n"
        "     (이후에는 원외에서도 마지막으로 받아둔 내용으로 동작합니다)\n"
        "  - 또는 Tampermonkey 수집기로 받은 JSON 경로를 --data 로 지정해도 됩니다.\n"
    )
    sys.exit(2)

# ----------------------------------------------------------------------------- 토크나이즈 / 검색

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]+")


def tokenize(s):
    """영문/숫자는 단어 단위, 한글은 2-gram(2글자) 단위로 쪼갠다. 형태소 분석기 불필요."""
    s = (s or "").lower()
    toks = _WORD_RE.findall(s)
    for run in _HANGUL_RE.findall(s):
        if len(run) == 1:
            toks.append(run)
        else:
            toks.extend(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def build_bm25(docs, k1=1.5, b=0.75):
    N = len(docs)
    doc_tf = [Counter(tokenize(d["subject"] + " " + d["subject"] + " " + d["text"])) for d in docs]
    lengths = [sum(tf.values()) for tf in doc_tf]
    avgdl = (sum(lengths) / N) if N else 1.0
    df = Counter()
    for tf in doc_tf:
        df.update(tf.keys())
    idf = {t: math.log(1 + (N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
    return doc_tf, lengths, avgdl, idf, k1, b


def bm25_score(qtoks, tf, dl, avgdl, idf, k1, b):
    score = 0.0
    for t in qtoks:
        if t not in tf:
            continue
        f = tf[t]
        score += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
    return score

# ----------------------------------------------------------------------------- 출력 헬퍼

def snippet(text, qtoks=None, width=160):
    text = re.sub(r"\s+", " ", text).strip()
    if not qtoks:
        return text[:width] + ("…" if len(text) > width else "")
    low = text.lower()
    pos = -1
    for t in qtoks:
        if len(t) < 2:
            continue
        p = low.find(t)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, pos - width // 4)
    seg = text[start:start + width]
    return ("…" if start > 0 else "") + seg + ("…" if start + width < len(text) else "")


def print_row(i, a, extra=""):
    d = a["date"][:10] if a["date"] else "          "
    print(f"[{i}] {d} | {a['writer'] or '-':<6} | {a['subject']}")
    print(f"     id={a['id']}{extra}")

# ----------------------------------------------------------------------------- 서브커맨드

def cmd_stats(docs, path):
    writers = Counter(a["writer"] or "-" for a in docs)
    dates = sorted(a["date"] for a in docs if a["date"])
    print(f"데이터 파일 : {path}")
    print(f"수집 글 수  : {len(docs)}")
    if dates:
        print(f"기간        : {dates[0][:10]} ~ {dates[-1][:10]}")
    print("작성자별    : " + ", ".join(f"{w}({c})" for w, c in writers.most_common()))


def cmd_list(docs, args):
    rows = docs
    if args.writer:
        rows = [a for a in rows if args.writer in a["writer"]]
    if args.since:
        rows = [a for a in rows if a["date"][:10] >= args.since]
    if args.until:
        rows = [a for a in rows if a["date"][:10] <= args.until]
    rows = rows[: args.recent]
    if not rows:
        print("조건에 맞는 글이 없습니다.")
        return
    for i, a in enumerate(rows, 1):
        print_row(i, a)


def cmd_search(docs, args):
    qtoks = tokenize(args.query)
    doc_tf, lengths, avgdl, idf, k1, b = build_bm25(docs)
    scored = []
    for idx, a in enumerate(docs):
        s = bm25_score(qtoks, doc_tf[idx], lengths[idx], avgdl, idf, k1, b)
        if s > 0:
            scored.append((s, idx))
    scored.sort(reverse=True)
    if not scored:
        print(f'"{args.query}" 와 관련된 글을 찾지 못했습니다. 더 일반적인 키워드로 다시 검색해 보세요.')
        return
    print(f'질문: "{args.query}" — 관련도 상위 {min(args.top, len(scored))}건\n')
    for rank, (s, idx) in enumerate(scored[: args.top], 1):
        a = docs[idx]
        print_row(rank, a, extra=f"  (관련도 {s:.1f})")
        print(f"     … {snippet(a['text'], qtoks)}\n")


def cmd_show(docs, args):
    key = args.id
    a = None
    if key.isdigit():
        i = int(key)
        if 1 <= i <= len(docs):
            a = docs[i - 1]
    if a is None:
        a = next((x for x in docs if x["id"] == key), None)
    if a is None:
        a = next((x for x in docs if key in x["id"]), None)
    if a is None:
        print(f"해당 글을 찾지 못했습니다: {key}")
        return
    print(f"제목   : {a['subject']}")
    print(f"작성자 : {a['writer']}")
    print(f"작성일 : {a['date']}")
    print(f"게시판 : {a['bbsName']}")
    print(f"id     : {a['id']}")
    print("-" * 60)
    print(a["text"])

# ----------------------------------------------------------------------------- main

def cmd_set_url(url):
    url = (url or "").strip()
    try:
        cfg = {}
        if os.path.isfile(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["url"] = url
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
        print(f"서버 주소를 저장했습니다: {url}")
        print(f"  (설정 파일: {_CONFIG_PATH})")
    except Exception as e:
        sys.stderr.write(f"[archive] 주소 저장 실패: {e}\n")
        sys.exit(2)


def main():
    p = argparse.ArgumentParser(description="KIST AI 아카이브 검색/요약 헬퍼")
    p.add_argument("--data", help="harvest JSON 경로(미지정 시 자동 탐색)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats", help="데이터 통계")

    pl = sub.add_parser("list", help="최근 글 목록")
    pl.add_argument("--recent", type=int, default=15, help="개수(기본 15)")
    pl.add_argument("--writer", help="작성자 필터")
    pl.add_argument("--since", help="YYYY-MM-DD 이후")
    pl.add_argument("--until", help="YYYY-MM-DD 이전")

    ps = sub.add_parser("search", help="질문 기반 관련 글 검색")
    ps.add_argument("query")
    ps.add_argument("--top", type=int, default=5, help="상위 N건(기본 5)")

    psh = sub.add_parser("show", help="특정 글 본문 전체")
    psh.add_argument("id", help="글 id 또는 list/search 순번")

    pu = sub.add_parser("set-url", help="원내 공유 서버 주소를 저장(최초 1회). 주소는 게시판 공지 참조")
    pu.add_argument("url", help="예: http://<원내서버>:<포트>/api/aix-archive/latest")

    args = p.parse_args()

    # set-url 은 데이터 로딩 전에 처리(데이터가 아직 없어도 실행 가능해야 함)
    if args.cmd == "set-url":
        cmd_set_url(args.url)
        return

    docs, path = load_articles(args.data)
    if docs is None:
        die_no_data()

    if args.cmd == "stats":
        cmd_stats(docs, path)
    elif args.cmd == "list":
        cmd_list(docs, args)
    elif args.cmd == "search":
        cmd_search(docs, args)
    elif args.cmd == "show":
        cmd_show(docs, args)


if __name__ == "__main__":
    main()
