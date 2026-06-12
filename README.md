# KIST AI 아카이브 스킬 · kist-aix-archive

> KIST 그룹웨어의 **‘AI 아카이브’ 게시판** 글을 Claude가 한 줄로 요약하고, 원하는 주제의 글을 추천해 주는 Claude Code 스킬입니다.

**언어 · Language: [한국어](#한국어) | [English](#english)**

---

<a id="한국어"></a>

## 한국어

**AIX전략실은 KIST의 AI Facilitator로서**, 원내 구성원 누구나 연구와 행정에 AI를 활용할 수 있도록 이끌고 있습니다. 그 거점이 그룹웨어의 **‘AI 아카이브’ 게시판**(게시판 번호 `BBS9157`)입니다. Claude Code·Gemini 같은 AI 도구의 실전 활용법, 정기 AIX 교육 강의자료, 직원들이 직접 만든 스킬·하네스, AI for Science 연구 동향, 보고서 작성·업무 자동화 같은 원내 적용 사례가 이곳에 올라옵니다.

그런데 글이 **이틀에 한 건꼴** 로 올라오고 답글로 이어지는 시리즈물도 많다 보니, *앞으로 수없이 쌓여갈 글들을 일일이 다 들여다보는 것은 어렵겠다* 는 판단이 들었습니다 — 이 스킬은 그래서 만들어졌습니다. 게시판을 여는 일 자체는 어렵지 않지만,

- 출장이나 실험으로 **며칠만 비우면** 밀린 글을 일일이 열어 따라잡아야 하고,
- 글이 **시간순으로만 쌓이기 때문에**, 정작 필요해진 순간에 *"분명 하네스 관련 글이 있었는데…"* 를 과거 목록을 뒤지며 찾아야 하며,
- 제목만으로는 내용을 가늠하기 어려운 글과 답글 체인을 **하나하나 클릭해서** 확인해야 합니다.

이 스킬은 그 과정을 대화 한 번으로 줄입니다. 작업하던 Claude Code 창에서 *"지난주 올라온 글 요약해줘"*, *"하네스 관련 글 추천해줘"* 라고 물으면, Claude가 게시판 전체(본문 포함)를 읽고 **한 줄 요약과 추천** 으로 답합니다. 게시판은 시간순으로 쌓이지만, 이 스킬은 **주제로 꺼내 쓰게** 해 줍니다.

### 설치 (Install)

Claude Code를 열고 아래처럼 말하면 끝입니다.

```
https://github.com/YOON-JUHO/kist-aix-archive 이 스킬 설치해 줘
```

설치 후 Claude Code를 한 번 재시작하세요. (이 스킬은 Claude Code에서만 동작합니다.)

**지원 환경:** Windows · macOS(Apple Silicon·Intel) · Linux 어디서나 동작합니다. Claude Code만 설치돼 있으면 되고, 도우미 스크립트는 **Python 3 표준 라이브러리만** 사용하므로 별도 패키지 설치가 필요 없습니다.

**설치와 첫 실행은 원내망(KIST 내부 네트워크)에서 해 주세요.** 첫 실행 때 원내 공유 서버에서 게시판 데이터를 받아 PC에 보관하며, 이후에는 원외에서도 마지막으로 받아둔 내용 기준으로 동작합니다. 원내망에 다시 연결되면 자동으로 최신화됩니다.

### 기여 (Contribution)

- 게시판 글을 일일이 열어보지 않아도, **한 줄 요약** 으로 핵심을 빠르게 파악합니다.
- *“하네스 관련 글 추천해줘”* 처럼 **주제로 물어보면** 관련 글을 골라 줍니다.
- 답하기 전에 **데이터 기준일**(며칠자까지 수집되었는지)을 함께 알려줘, 지금 보는 내용이 얼마나 최신인지 알 수 있습니다.

### 동작 방식 (Methods)

- `archive.py` — 외부 라이브러리 없이 **파이썬 표준 라이브러리만으로** 만든 도우미로, 키워드 검색·목록·통계·본문 보기를 제공합니다.
- Claude는 이 도우미의 출력을 읽어 **그때그때** 요약·추천을 만듭니다(요약을 미리 만들어 저장해 두지 않습니다).
- 글 데이터는 **원내 공유 서버** 에서 최신본을 받아오며, 받을 때마다 PC에 사본을 남깁니다. 서버에 닿지 못하면 **마지막으로 받아둔 사본** 으로 동작합니다. (게시판 데이터는 원내 자료이므로 이 저장소에는 포함되어 있지 않습니다.)

### 사용 예시 (Examples)

**밀린 글 따라잡기**

- "AI 아카이브 최근 글 5개만 한 줄씩 요약해줘"
- "지난주에 올라온 글 중에 놓치면 아까운 것만 골라줘"
- "이제현 실장님이 5월 이후 올린 글 요약해줘"

**주제로 찾기·추천받기**

- "하네스(harness) 관련 글 전부 찾아줘"
- "Claude Code 처음 시작하는 사람한테 추천할 글 순서대로 알려줘"
- "보고서 작성 자동화에 써먹을 만한 글 있어?"

**한 편 깊이 읽기**

- "'Zotero + Claude Code + Obsidian' 시리즈 내용 정리해줘 — 답글까지 포함해서"
- "'AI를 쓸 때 검증은 필수입니다' 글의 핵심 주장이 뭐야?"

**읽는 데서 끝내지 않고, 바로 실행하기**

게시글에 소개된 도구를 그 자리에서 설치·적용할 수 있습니다. Claude Code가 본문 속 안내(저장소 주소, 절차)를 읽고 직접 수행하기 때문입니다.

- "'paper-curation 업데이트' 글 본문 읽고, 안내된 대로 paper-curation 설치해줘"
- "'주간동향 작성 자동화 skill' 글에 나온 스킬, 내 환경에도 설정해줘"

> 단, 수집 데이터는 글의 **텍스트만** 담으므로, 첨부파일이나 이미지 속 안내는 Claude가 해당 저장소의 README 등을 직접 찾아 보완합니다. 어떤 명령이 실행되는지는 진행 과정에서 단계별로 확인할 수 있습니다.

**응답 형태(예시)**

> 📌 (글 제목) — 한 줄 요약. *(작성일)*
> 📌 (글 제목) — 한 줄 요약. *(작성일)*
> *지금 보고 있는 데이터 기준일: 2026-06-12*

### 저장소 구조 (Project Structure)

```
kist-aix-archive/
├── .claude-plugin/              ← Claude Code 플러그인 매니페스트
├── skills/aix-archive/
│   ├── SKILL.md                 ← 스킬 본체 (Claude가 따르는 지침)
│   └── scripts/archive.py       ← 검색·목록·통계·본문 헬퍼 (의존성 없음)
├── tools/
│   └── bbs9157_harvest.user.js  ← 수집기 (Tampermonkey, 수집 담당자용)
├── server/
│   └── aix_archive_api.py       ← 공유 서버 라우터 (FastAPI, 참조용)
├── CLAUDE.md                    ← 이 저장소에서 작업하는 Claude를 위한 지침
└── README.md
```

### 한계 (Limitations)

- **실시간이 아닙니다.** 게시판이 **원내망과 로그인 안쪽** 에 있어, 로그인한 사람의 브라우저가 아니면 글을 읽어올 수 없습니다. 그래서 담당자 한 명이 게시판을 볼 때 글을 모아 **원내 공유 서버** 에 올려두고, 다른 사람들의 스킬은 그 서버에서 최신본을 받아보는 구조입니다. 일반 사용자는 따로 할 일이 없지만, 방금 올라온 글이 곧바로 반영되지는 않을 수 있습니다.
- **서버에 닿지 못할 때** 는 마지막으로 받아둔 사본으로 동작하므로 내용이 다소 오래되었을 수 있으며, 이때 Claude가 기준일을 함께 알려줍니다. 그래서 **첫 실행만큼은 원내망에서** 해야 합니다 — 받아둔 사본이 아직 없기 때문입니다.

> 데이터 최신화는 본 스킬을 개발한 **천연물신약사업단 윤주호**(yoonjuho@kist.re.kr)가 맡고 있으며, 게시판을 확인하는 과정에서 자연스럽게 갱신됩니다. 갱신이 필요하거나 궁금한 점이 있으면 편하게 연락 주세요.

---

<a id="english"></a>

## English

**As KIST's AI Facilitator, the AIX Strategy Office** guides everyone at the institute toward using AI in both research and administration. Its home base is the **‘AI Archive’ board** (board number `BBS9157`) on the groupware, which carries hands-on guides for AI tools like Claude Code and Gemini, lecture materials from the regular AIX training series, skills and harnesses built by staff, AI-for-Science research trends, and real internal use cases such as report writing and workflow automation.

But with new posts landing roughly **every other day** — many growing into reply-chain series — it became clear that *reading every one of the countless posts that will keep piling up just isn't feasible*. That's why this skill was built. Opening the board itself is easy, but:

- Step away for a few days for a trip or experiments, and you're **opening backlogged posts one by one** to catch up.
- Posts pile up **only in chronological order**, so the moment you actually need something, you're scrolling old listings thinking *"there was a harness post somewhere…"*.
- Titles alone rarely tell the whole story, so you end up **clicking through** posts and reply chains to check.

This skill collapses all of that into a single question. Right from the Claude Code window you're already working in, ask *"summarize last week's posts"* or *"recommend posts about harnesses"*, and Claude reads the whole board (bodies included) and answers with **one-line summaries and recommendations**. The board accumulates by time; this skill lets you **retrieve by topic**.

### Install

Open Claude Code and just say:

```
Install this skill: https://github.com/YOON-JUHO/kist-aix-archive
```

Restart Claude Code once after installation. (This skill runs in Claude Code only.)

**Supported environments:** Works on Windows, macOS (Apple Silicon & Intel), and Linux. You only need Claude Code installed; the helper script uses the **Python 3 standard library only**, so no extra packages are required.

**Please install and run it for the first time on the KIST internal network.** On first run it fetches the board data from the internal shared server and keeps a copy on your PC; after that it works outside the network too, based on the last copy it received. It refreshes automatically whenever you're back on the internal network.

### Contribution

- Get the gist fast with **one-line summaries** instead of opening every post.
- **Ask by topic** — e.g. *“recommend posts about harnesses”* — and it picks the relevant ones.
- Before answering, it tells you the **data cutoff date** (how far the collection goes), so you know how current the content is.

### Methods

- `archive.py` — a helper built with the **Python standard library only** (no external dependencies), providing keyword search, listing, stats, and post viewing.
- Claude reads this helper's output to produce summaries and recommendations **on the fly** (it does not pre-store summaries).
- Post data is pulled from an **internal shared server**, and each successful fetch leaves a copy on your PC. If the server is unreachable, the skill runs on **the last copy it received**. (The board data itself is internal material and is not included in this repository.)

### Examples

**Catch up on what you missed**

- "Summarize the 5 most recent AI Archive posts, one line each"
- "From last week's posts, pick only the ones worth not missing"
- "Summarize the posts Director Jehyun Lee has written since May"

**Search & get recommendations by topic**

- "Find every post about harnesses"
- "What should a Claude Code beginner read, and in what order?"
- "Anything useful for automating report writing?"

**Read one post in depth**

- "Walk me through the 'Zotero + Claude Code + Obsidian' series — replies included"
- "What's the core argument of the 'verification is a must when using AI' post?"

**Don't just read — act on it**

You can install or apply a tool introduced in a post on the spot, because Claude Code reads the instructions in the post body (repo address, steps) and carries them out itself.

- "Read the 'paper-curation update' post and install paper-curation as instructed"
- "Set up the skill from the 'weekly-trends automation skill' post in my environment too"

> Note: the collected data contains **text only**, so for instructions inside attachments or images, Claude fills the gap by checking the linked repository's README and similar sources. You can review each command step by step as it proceeds.

**Sample response shape**

> 📌 (post title) — one-line summary. *(date)*
> 📌 (post title) — one-line summary. *(date)*
> *Data cutoff of what you're seeing: 2026-06-12*

### Project Structure

```
kist-aix-archive/
├── .claude-plugin/              ← Claude Code plugin manifests
├── skills/aix-archive/
│   ├── SKILL.md                 ← The skill itself (instructions Claude follows)
│   └── scripts/archive.py       ← Search/list/stats/view helper (zero dependencies)
├── tools/
│   └── bbs9157_harvest.user.js  ← Harvester (Tampermonkey, for the collector)
├── server/
│   └── aix_archive_api.py       ← Shared-server router (FastAPI, for reference)
├── CLAUDE.md                    ← Instructions for Claude working in this repo
└── README.md
```

### Limitations

- **Not real-time.** The board sits **behind the internal network and a login**, so its posts can only be read from the browser of someone who is logged in. So one person gathers the posts when they open the board and uploads them to an **internal shared server**, and everyone else's skill receives the latest copy from there. Regular users have nothing to do, but a just-posted item may not appear immediately.
- **When the server is unreachable**, the skill runs on the last copy it received, so the contents may be a bit out of date — and Claude will tell you the cutoff date. This is also why **the very first run must happen on the internal network** — there is no saved copy yet.

> Data updates are handled by **Juho Yoon** (yoonjuho@kist.re.kr) of the Natural Products Drug Discovery Project Group, who developed this skill; the data refreshes naturally as the board is browsed. Feel free to reach out with any update requests or questions.
