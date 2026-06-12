// ==UserScript==
// @name         KIST 그룹웨어 BBS9157 본문 수집기 v2.0
// @namespace    kist-ai4s
// @version      2.0
// @description  AI Facilitator 게시판을 열면 게시판 프레임에서 전체 자동 수집→원내 공유 서버 업로드(% 오버레이). 서버 주소·업로드 토큰은 메뉴에서 설정.
// @match        http://ngw.kist.re.kr:9000/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @grant        GM_registerMenuCommand
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      *
// @all-frames   true
// ==/UserScript==

(function () {
  'use strict';
  if (window.__nemoHarvestBuilt) return; // 같은 프레임 중복 방지

  // 업로드 주소·토큰은 코드에 넣지 않고(공개 저장소) Tampermonkey 저장소에 보관한다.
  // 주소는 원내 게시판 공지에서 받아 메뉴 '🔧 서버 주소 설정'으로 한 번 입력한다.
  const URL_KEY = 'aixUploadUrl';
  const TOKEN_KEY = 'aixUploadToken';
  const getUploadUrl = () => { try { return GM_getValue(URL_KEY, '') || ''; } catch (e) { return ''; } };
  const getToken = () => { try { return GM_getValue(TOKEN_KEY, '') || ''; } catch (e) { return ''; } };
  function setUrlPrompt() {
    const cur = getUploadUrl();
    const v = prompt('원내 공유 서버 업로드 주소를 입력하세요 (예: http://<원내서버>:<포트>/api/aix-archive):', cur);
    if (v === null) return;
    try { GM_setValue(URL_KEY, v.trim()); alert(v.trim() ? '서버 주소 저장됨' : '주소 삭제됨'); } catch (e) { alert('저장 실패: ' + e); }
  }
  function setTokenPrompt() {
    const cur = getToken();
    const v = prompt('업로드 토큰을 입력하세요 (서버의 AIX_ARCHIVE_TOKEN 과 동일해야 함):', cur);
    if (v === null) return;
    try { GM_setValue(TOKEN_KEY, v.trim()); alert(v.trim() ? '토큰 저장됨' : '토큰 삭제됨'); } catch (e) { alert('저장 실패: ' + e); }
  }

  // 이 프레임이 "게시판 프레임"인지 판별 (목록 또는 상세)
  function isBoardFrame() {
    try {
      if (document.querySelector('.top_subject')) return true;          // 상세 화면
      const html = document.documentElement.innerHTML;
      if (html.indexOf('글번호') >= 0 && document.querySelector('table')) return true; // 목록 화면
      if (/NEW\d{15,20}/.test(html)) return true;                       // 글 ID 존재
    } catch (e) {}
    return false;
  }
  if (!(window.top === window.self || isBoardFrame())) return; // 게시판 프레임/독립창에서만 패널

  const KEY   = '__nemoHarvest_v1';
  const BBSID = 'BBS9157';
  const CATID = 'FREEBBS';
  const ID_RE = /NEW\d{15,20}/g;
  const DELAY = 250;

  function loadDB() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
  function saveDB(db) { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { console.warn(e); } }
  function db() { const d = loadDB(); d.ids = d.ids || []; d.articles = d.articles || {}; d.diag = d.diag || {}; return d; }

  function htmlToText(h) {
    try { return (new DOMParser().parseFromString(h, 'text/html').body.textContent || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim(); }
    catch (e) { return h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); }
  }
  function eachFrame(fn) {
    fn(document);
    document.querySelectorAll('iframe,frame').forEach(f => { try { if (f.contentDocument) fn(f.contentDocument); } catch (e) {} });
  }
  function scanIds() { const s = new Set(); eachFrame(d => { try { (d.documentElement.outerHTML.match(ID_RE) || []).forEach(x => s.add(x)); } catch (e) {} }); return [...s]; }
  function scanTokens() {
    const t = {};
    eachFrame(d => { try {
      const a = d.querySelector('input[name="_tokenid"]'); if (a && a.value) t._tokenid = a.value;
      const b = d.querySelector('input[name="transaction_token_key"]'); if (b && b.value) t.ttk = b.value;
    } catch (e) {} });
    return t;
  }
  function frameHtmlWithIds() { let best = ''; eachFrame(d => { try { const h = d.documentElement.outerHTML; if (/NEW\d{15,20}/.test(h) && h.length > best.length) best = h; } catch (e) {} }); return best.slice(0, 300000); }

  async function fetchArticle(id, tok) {
    const p = new URLSearchParams();
    p.set('facade', 'BBSArticleFacade'); p.set('command', 'viewArticle'); p.set('nextpage', '/bbs/articleView.jsp');
    p.set('articleId', id); p.set('orgArticleId', id); p.set('articleBbsId', BBSID); p.set('bbsId', BBSID);
    p.set('categoryId', CATID); p.set('articleList', JSON.stringify({ articleId: id, bbsId: BBSID, categoryId: CATID }));
    p.set('viewMode', 'VIEW'); p.set('userMode', 'USER'); p.set('popYn', 'Y'); p.set('publicYn', 'Y');
    p.set('leftPaneMenuId', 'FREEBBS_LIST'); p.set('transaction_yn', 'N'); p.set('paging_listcnt', '5');
    if (tok._tokenid) p.set('_tokenid', tok._tokenid);
    if (tok.ttk) p.set('transaction_token_key', tok.ttk);
    const res = await fetch('/xclick_kist/XClickController', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }, body: p.toString()
    });
    return { status: res.status, txt: await res.text() };
  }
  function parseArticle(id, txt) {
    const m = txt.match(new RegExp('<div id="contentArea_' + id + '"[^>]*>([\\s\\S]*?)</div>\\s*(?:<div|<table|<form|<script|$)'));
    const bodyHtml = m ? m[1] : '';
    const sm = txt.match(/<div class="top_subject"[^>]*>([\s\S]*?)<\/div>/);
    const g = re => { const x = txt.match(re); return x ? x[1].trim() : ''; };
    return {
      id,
      subject: sm ? htmlToText(sm[1]) : '',
      writer:  g(/name=['"]writer['"][^>]*value=['"]([^'"]*)['"]/),
      date:    g(/name=['"]notifyDate['"][^>]*value=['"]([^'"]*)['"]/),
      bbsName: g(/name=['"]bbsName['"][^>]*value=['"]([^'"]*)['"]/),
      text:    htmlToText(bodyHtml.replace(/<title>[\s\S]*?<\/title>/i, '')),
      bodyHtml: bodyHtml.slice(0, 120000),
      ok: !!bodyHtml
    };
  }

  function collectIds() {
    const d = db(); const found = scanIds(); const before = d.ids.length;
    found.forEach(id => { if (!d.ids.includes(id)) d.ids.push(id); });
    if (!d.diag.listHtmlSample) d.diag.listHtmlSample = frameHtmlWithIds();
    d.diag.lastTokens = scanTokens();
    saveDB(d); render();
    alert('이 페이지 ' + found.length + '개 발견 → 누적 ' + d.ids.length + '개 (+' + (d.ids.length - before) + ')');
  }
  let harvesting = false;
  async function harvest() {
    if (harvesting) return;
    const d = db();
    if (!d.ids.length) { alert('먼저 ① 로 글 ID를 모으세요.'); return; }
    const tok = scanTokens(); d.diag.usedTokens = tok; harvesting = true;
    const todo = d.ids.filter(id => !(d.articles[id] && d.articles[id].ok));
    for (let i = 0; i < todo.length; i++) {
      const id = todo[i]; setStatus('수집 중 ' + (i + 1) + '/' + todo.length);
      try { const r = await fetchArticle(id, tok); const a = parseArticle(id, r.txt); a.httpStatus = r.status;
        if (i === 0) d.diag.firstRawResponse = r.txt.slice(0, 200000); d.articles[id] = a; }
      catch (e) { d.articles[id] = { id, ok: false, error: String(e) }; }
      saveDB(d); render(); await new Promise(r => setTimeout(r, DELAY));
    }
    harvesting = false; setStatus('완료. ③ 다운로드 하세요.');
    alert('완료: 성공 ' + Object.values(d.articles).filter(a => a.ok).length + ' / 시도 ' + d.ids.length);
  }
  function download() {
    const d = db(); const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'bbs9157_harvest.json'; a.click();
  }

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // 게시판 목록을 페이지 단위로 POST 조회 → 그 페이지의 글 ID 배열 (kist.user.js의 listArticle 방식)
  async function fetchListPage(page, tok) {
    const p = new URLSearchParams();
    p.set('facade', 'BBSArticleFacade'); p.set('command', 'listArticle');
    p.set('nextpage', '/bbs/articleGenList.jsp'); p.set('categoryId', CATID);
    p.set('bbsId', BBSID); p.set('curMapYn', 'Y'); p.set('menuGbn', 'USERMAP');
    p.set('timeZone', 'GMT+09:00'); p.set('progressNo', 'Y'); p.set('searchMode', 'N');
    p.set('paging_listcnt', '100'); p.set('currpage_no', String(page)); p.set('transaction_yn', 'N');
    if (tok._tokenid) p.set('_tokenid', tok._tokenid);
    if (tok.ttk) p.set('transaction_token_key', tok.ttk);
    const res = await fetch('/xclick_kist/XClickController', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest' },
      body: p.toString()
    });
    const txt = await res.text();
    const set = new Set(); (txt.match(ID_RE) || []).forEach(x => set.add(x));
    return [...set];
  }

  // 슬림 페이로드로 서버 업로드 (cb: ok, 메시지)
  function doUpload(d, cb) {
    const slim = {};
    Object.keys(d.articles).forEach(k => {
      const a = d.articles[k];
      if (a && a.ok) slim[k] = { id: a.id, subject: a.subject, writer: a.writer, date: a.date, bbsName: a.bbsName, text: a.text, ok: true };
    });
    const okCount = Object.keys(slim).length;
    if (!okCount) { cb(false, '업로드할 본문 없음'); return; }
    let done = false;
    const finish = (ok, msg) => { if (done) return; done = true; cb(ok, msg); };
    const uploadUrl = getUploadUrl();
    if (!uploadUrl) { console.warn('[BBS9157] 서버 주소 미설정'); finish(false, '서버 주소 미설정 — 메뉴 \'🔧 서버 주소 설정\' 먼저'); return; }
    const token = getToken();
    if (!token) { console.warn('[BBS9157] 업로드 토큰 미설정'); finish(false, '업로드 토큰 미설정 — 메뉴 \'🔑 업로드 토큰 설정\' 먼저'); return; }
    console.log('[BBS9157] 업로드 시작:', okCount, '건 →', uploadUrl);
    GM_xmlhttpRequest({
      method: 'POST', url: uploadUrl, timeout: 30000,
      headers: { 'Content-Type': 'application/json', 'X-AIX-Archive-Token': token },
      data: JSON.stringify({ ids: d.ids, articles: slim }),
      onload: function (res) {
        console.log('[BBS9157] 업로드 응답 HTTP', res.status, (res.responseText || '').slice(0, 200));
        if (res.status >= 200 && res.status < 300) {
          let n = okCount; try { const j = JSON.parse(res.responseText); if (j.count != null) n = j.count; } catch (e) {}
          finish(true, n + '건');
        } else {
          if (res.status === 401) finish(false, '토큰 불일치 — 🔑 메뉴에서 다시 설정');
          else if (res.status === 503) finish(false, '서버에 토큰 미설정(AIX_ARCHIVE_TOKEN) — 관리자 확인');
          else finish(false, 'HTTP ' + res.status + ' (플랫폼 라우트 미반영 가능)');
        }
      },
      onerror:   function () { console.warn('[BBS9157] 업로드 onerror'); finish(false, '서버(' + uploadUrl + ') 미도달'); },
      ontimeout: function () { console.warn('[BBS9157] 업로드 timeout'); finish(false, '응답 없음(30초 초과) — 플랫폼 확인'); }
    });
  }

  function upload() {
    const d = db();
    setStatus('서버 업로드 중…');
    doUpload(d, (ok, msg) => { setStatus(ok ? '업로드 완료' : '업로드 실패'); alert(ok ? ('서버 업로드 완료: ' + msg) : ('업로드 실패 — ' + msg)); });
  }

  // ⚡ 전체 자동: 모든 목록 페이지 순회 → 본문 수집 → 서버 업로드 (진행률 %)
  let autoRunning = false;
  async function autoHarvest() {
    if (autoRunning || harvesting) return;
    autoRunning = true;
    const d = db();
    const tok = scanTokens(); d.diag.usedTokens = tok;
    try {
      setProg(2, '목록 수집 중…');
      let page = 1; const MAX_PAGES = 40;
      while (page <= MAX_PAGES) {
        let ids = [];
        try { ids = await fetchListPage(page, tok); } catch (e) { ids = []; }
        const before = d.ids.length;
        ids.forEach(id => { if (!d.ids.includes(id)) d.ids.push(id); });
        saveDB(d); render();
        setProg(Math.min(8, 2 + page), '목록 ' + page + '페이지 · 누적 ' + d.ids.length + '건');
        if (ids.length === 0) break;            // 더 이상 글 없음
        if (d.ids.length === before) break;      // 새 ID 없음(마지막/중복) → 종료
        page++; await sleep(DELAY);
      }
      const todo = d.ids.filter(id => !(d.articles[id] && d.articles[id].ok));
      for (let i = 0; i < todo.length; i++) {
        const id = todo[i];
        try { const r = await fetchArticle(id, tok); const a = parseArticle(id, r.txt); a.httpStatus = r.status; d.articles[id] = a; }
        catch (e) { d.articles[id] = { id, ok: false, error: String(e) }; }
        saveDB(d); render();
        const pct = 10 + Math.round((i + 1) / Math.max(1, todo.length) * 80);
        setProg(pct, '본문 ' + (i + 1) + '/' + todo.length);
        await sleep(DELAY);
      }
      setProg(95, '서버 업로드 중…');
      await new Promise(resolve => doUpload(d, (ok, msg) => {
        setProg(100, ok ? ('완료 — ' + msg) : ('업로드 실패 — ' + msg));
        if (ok) { try { localStorage.setItem('aixLastAuto', String(Date.now())); } catch (e) {} }
        else alert('업로드 실패 — ' + msg);
        resolve();
      }));
    } catch (e) {
      setProg(0, '오류: ' + e);
    } finally {
      autoRunning = false;
    }
  }

  // 화면엔 패널 없이 '진행률 % 오버레이'만 (작업 중에만 표시, 완료 3초 후 사라짐)
  let progEl, progFillEl, progTxtEl, hideTimer;
  function ensureProg() {
    if (progEl) return;
    let doc = document;
    try { if (window.top && window.top.document && window.top.document.body) doc = window.top.document; } catch (e) {}
    if (!doc.body) return;
    progEl = doc.createElement('div');
    progEl.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;background:#0f172a;color:#e2e8f0;font:12px/1.4 -apple-system,system-ui,sans-serif;padding:10px 12px;border-radius:10px;width:230px;box-shadow:0 6px 20px rgba(0,0,0,.45);display:none';
    progEl.innerHTML =
      '<div style="font-weight:600;margin-bottom:6px">📥 AI 아카이브 업로드</div>' +
      '<div style="background:#1e293b;border-radius:5px;height:10px;overflow:hidden"><div id="aixFill" style="height:100%;width:0%;background:#22c55e;transition:width .2s"></div></div>' +
      '<div id="aixTxt" style="text-align:center;margin-top:5px;color:#86efac">0%</div>';
    doc.body.appendChild(progEl);
    progFillEl = progEl.querySelector('#aixFill'); progTxtEl = progEl.querySelector('#aixTxt');
  }
  function setProg(pct, label) {
    ensureProg(); if (!progEl) return;
    clearTimeout(hideTimer);
    pct = Math.max(0, Math.min(100, pct));
    progEl.style.display = 'block';
    progFillEl.style.width = pct + '%';
    progTxtEl.textContent = (label ? label + ' · ' : '') + Math.round(pct) + '%';
    if (pct >= 100) hideTimer = setTimeout(() => { if (progEl) progEl.style.display = 'none'; }, 3000);
  }
  function setStatus(s) { console.log('[BBS9157]', s); }
  function render() { /* 패널 없음 — 진행은 setProg 오버레이로 표시 */ }

  // 자동 트리거: kist.user.js가 심은 플래그를 보고, '게시판 본문이 있는 프레임'에서만 실행한다.
  // (그 프레임이 세션 토큰을 가지므로 — v1.4가 동작하던 방식. 최상위/셸 프레임은 양보.)
  // 프레임·로딩 타이밍을 대비해 최대 ~8초 폴링.
  function maybeAutoRun() {
    const AUTO_THROTTLE_MIN = 0; // 0=AI Facilitator 누를 때마다 실행. N분이면 그 안엔 건너뜀. 메뉴의 ⚡는 항상 동작.
    let tries = 0, logged = false;
    const tick = () => {
      let flag = null; try { flag = sessionStorage.getItem('aixAutoHarvest'); } catch (e) {}
      const board = isBoardFrame();
      const ntok = Object.keys(scanTokens()).length;
      if (!logged) { logged = true; console.log('[BBS9157] 트리거 점검 · frame=' + (window.top === window.self ? 'top' : 'iframe') + ' · ' + location.pathname + ' · flag=' + flag + ' · board=' + board + ' · tokens=' + ntok); }
      if (flag === '1' && board) {
        try { sessionStorage.removeItem('aixAutoHarvest'); } catch (e) {} // 게시판 도착 후에만 소비(중간 메뉴 페이지가 가로채지 않도록)
        let lastT = 0; try { lastT = +localStorage.getItem('aixLastAuto') || 0; } catch (e) {}
        if (AUTO_THROTTLE_MIN > 0 && Date.now() - lastT < AUTO_THROTTLE_MIN * 60000) {
          console.log('[BBS9157] 최근 업로드됨 — 자동 건너뜀(메뉴 ⚡로 강제 가능)');
        } else {
          console.log('[BBS9157] 자동 트리거 감지 → 수집 시작 (frame=' + (window.top === window.self ? 'top' : 'iframe') + ')');
          setTimeout(autoHarvest, 1200);
        }
        return;
      }
      if (++tries < 27) setTimeout(tick, 300);
      else if (flag === '1') console.log('[BBS9157] 플래그는 있으나 게시판 프레임/토큰을 못 찾음 → 자동실행 보류. Tampermonkey 메뉴 ⚡로 실행해 보세요.');
    };
    tick();
  }

  function build() {
    if (!document.body) return setTimeout(build, 300);
    window.__nemoHarvestBuilt = true;
    // 메뉴 등록: 최상위 프레임 또는 게시판 프레임에서 (최상위가 frameset이라 body가 없으면 거기선 build가 멈추므로,
    // 게시판 프레임에서도 등록해 ⚡ 수동 실행을 항상 가능하게 한다). 화면엔 버튼 없음.
    try {
      if ((window.top === window.self || isBoardFrame()) && typeof GM_registerMenuCommand === 'function') {
        GM_registerMenuCommand('⚡ AI 아카이브 전체 수집·업로드', autoHarvest);
        GM_registerMenuCommand('💾 JSON 다운로드(개인용)', download);
        GM_registerMenuCommand('♻️ 수집 데이터 초기화', () => { localStorage.removeItem(KEY); alert('초기화됨'); });
        GM_registerMenuCommand('🔧 서버 주소 설정', setUrlPrompt);
        GM_registerMenuCommand('🔑 업로드 토큰 설정', setTokenPrompt);
      }
    } catch (e) {}
    maybeAutoRun();
  }
  build();
})();
