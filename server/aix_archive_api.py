# -*- coding: utf-8 -*-
"""
KIST 강릉 연구지원 플랫폼(FastAPI, :7777)에 추가하는 'AI 아카이브' 공유 데이터 허브 라우터.

엔드포인트
  POST /api/aix-archive          : 수집기(Tampermonkey)가 보낸 harvest JSON을 최신본으로 저장
                                   (헤더 X-AIX-Archive-Token 으로 업로드 토큰 검증)
  GET  /api/aix-archive/latest   : 저장된 최신본을 그대로 반환 (스킬의 archive.py가 받아감)

이렇게 두면 '한 명이 한 번 수집 → 전 직원의 스킬이 같은 최신 데이터'가 된다.

플랫폼 메인 앱에 붙이는 법 (예: main.py):
    from aix_archive_api import router as aix_archive_router
    app.include_router(aix_archive_router)

업로드 토큰 설정 (서버 쪽, 필수)
  - 환경변수 AIX_ARCHIVE_TOKEN 에 비밀 토큰을 설정한다. (예: setx AIX_ARCHIVE_TOKEN "..." 후 서버 재시작)
  - 미설정 시 업로드는 전부 거부된다(읽기 GET 은 영향 없음). '잠긴 게 기본'이다.
  - 수집기(Tampermonkey)에는 같은 토큰을 메뉴에서 한 번 입력해 두면 된다.

주의
  - 수집기는 그룹웨어(ngw.kist.re.kr) 페이지에서 이 :7777 로 cross-origin POST를 한다.
    CORS 허용 목록에 그룹웨어 origin이 있어야 하며, 커스텀 헤더(X-AIX-Archive-Token)를 쓰므로
    allow_headers 에 "*" 또는 해당 헤더가 포함되어야 한다.
  - 저장 위치(STORE)는 플랫폼의 데이터 폴더에 맞게 바꿔도 된다.
"""
from pathlib import Path
import hmac
import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/aix-archive", tags=["aix-archive"])

# 저장 위치 — 플랫폼 구조에 맞게 조정 가능
DATA_DIR = Path(__file__).resolve().parent / "data"
STORE = DATA_DIR / "aix_archive_latest.json"

TOKEN_HEADER = "X-AIX-Archive-Token"


def _check_token(request: Request):
    """업로드 토큰 검증. (None = 통과, JSONResponse = 거부 응답)"""
    expected = os.environ.get("AIX_ARCHIVE_TOKEN", "")
    if not expected:
        # 토큰 미설정 = 업로드 잠금. 운영자가 환경변수를 설정해야 열린다.
        return JSONResponse(
            {"ok": False, "error": "uploads disabled: AIX_ARCHIVE_TOKEN not set on server"},
            status_code=503,
        )
    got = request.headers.get(TOKEN_HEADER, "")
    if not hmac.compare_digest(got, expected):
        return JSONResponse({"ok": False, "error": "invalid or missing upload token"}, status_code=401)
    return None


@router.post("")
async def upload_archive(request: Request):
    """수집기가 보낸 harvest 전체(JSON)를 최신본으로 덮어쓴다. 토큰 검증 통과 시에만."""
    denied = _check_token(request)
    if denied is not None:
        return denied
    payload = await request.json()
    if not isinstance(payload, dict) or "articles" not in payload:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "count": len(payload.get("articles", {}))}


@router.get("/latest")
async def latest_archive():
    """저장된 최신본을 반환. 아직 업로드 전이면 빈 구조 + 404. (읽기는 토큰 불필요)"""
    if not STORE.exists():
        return JSONResponse({"articles": {}}, status_code=404)
    return JSONResponse(json.loads(STORE.read_text(encoding="utf-8")))
