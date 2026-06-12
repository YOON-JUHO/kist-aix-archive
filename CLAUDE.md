# CLAUDE.md — 이 저장소에서 작업하는 Claude를 위한 지침

## 이 저장소는 무엇인가

KIST 그룹웨어 'AI 아카이브' 게시판(BBS9157) 글을 요약·추천하는 **Claude Code 스킬** 배포 저장소.
스킬 본체는 `skills/aix-archive/`, 데이터 수집·서빙 도구는 `tools/`와 `server/`에 있다.

## 구조

```
kist-aix-archive/
├── .claude-plugin/            ← Claude Code 플러그인/마켓플레이스 매니페스트
│   ├── plugin.json
│   └── marketplace.json
├── skills/aix-archive/
│   ├── SKILL.md               ← 스킬 본체(지침). 스킬 동작을 바꾸려면 여기부터
│   └── scripts/archive.py     ← 검색/목록/통계/본문 헬퍼 (표준 라이브러리만, 의존성 0)
├── tools/
│   └── bbs9157_harvest.user.js  ← 수집기(Tampermonkey). 그룹웨어에서 글을 모아 공유 서버에 업로드
├── server/
│   └── aix_archive_api.py     ← 공유 서버 라우터(FastAPI) 참조 사본. 실제 배포본은 별도 플랫폼에 있음
├── README.md                  ← 사용자 문서 (한/영)
└── CLAUDE.md                  ← 이 파일
```

## 데이터 흐름 (중요)

수집기(로그인된 브라우저) → POST(토큰 헤더) → 원내 공유 서버 → GET ← archive.py(각 사용자 PC, 로컬 캐시 보관)

- **게시판 데이터(JSON)는 절대 이 저장소에 커밋하지 않는다.** 원내 자료다. `.gitignore`가 막고 있지만, `git add` 전에 한 번 더 확인할 것.
- 업로드는 `X-AIX-Archive-Token` 헤더로 인증한다. **토큰을 코드·문서에 하드코딩하지 않는다** (서버: 환경변수 `AIX_ARCHIVE_TOKEN`, 수집기: Tampermonkey 저장소).
- archive.py의 최신본 선택은 파일 수정시각이 아니라 **내용물의 글 최신 날짜** 기준이다. 이 동작을 되돌리지 말 것.

## 수정 시 규칙

- `archive.py`는 **파이썬 표준 라이브러리만** 사용한다. 외부 패키지를 추가하지 않는다(전 직원 PC에서 무설치로 돌아야 함).
- 수집기를 수정하면 상단 `@version` 을 올리고, 변경 요지를 커밋 메시지에 남긴다.
- `server/aix_archive_api.py` 를 바꾸면 실제 운영 플랫폼(app.py)에도 같은 변경을 반영해야 한다고 사용자에게 알릴 것.
- README는 한국어/영어 두 섹션이 항상 같은 내용을 담도록 함께 수정한다.

## 검증 방법

```bash
python -m py_compile skills/aix-archive/scripts/archive.py   # 문법
AIX_ARCHIVE_URL="" python skills/aix-archive/scripts/archive.py stats   # 데이터 없을 때 안내 메시지 확인
```
