// nexa-reqpanel.js - AI 요청 패널의 배선(공용 컴포넌트) - 공용 요청 모듈(nexa-requests.js)과 세션 표시(wsession.js)를 화면의 패널에 붙인다.
//   시트 · 페이지 편집기가 같이 쓴다(슬라이드 편집기는 초안·메모 흐름이 달라 SESS/RQ 만 같은 모듈을 쓴다 - docs/dev/page-editor/design.md 10-5).
//   패널의 DOM 은 화면이 둔다(같은 id): #sessChip · #reqText · #reqSend · #reqAtt · #reqHint · #reqFilter · #reqList · #attFile, 묶는 틀 = opts.compose(기본 "#side .compose")
//   NexaReqPanel.mount(o) → { SESS, RQ, render, send, onVersion(v), load }
//     o.api · toast · openMenu · esc · base · deckId()          화면의 공용 도구
//     o.state           요청 목록·세션 상태를 둘 객체(state.reqs · state.session 을 쓴다)
//     o.target          nexa-requests 의 대상 어댑터 {key, current, label, num, scope, goto, extra?}
//     o.buildBody()     보낼 요청의 대상 칸 {slide, element?, elements?, range?…}(action·status·text 는 여기서 붙인다)
//     o.beforeSend()    보내기 전(편집 끝내기 · 저장) - async
//     o.ready()         그릴 수 있는가(문서를 읽었는가) - 없으면 늘 그린다
//     o.filter          {html(recent) → 필터 줄 왼쪽 HTML, test(q) → 보일 요청인가, click(button) → 처리했으면 true} - 없으면 "최근 요청 n건"
//     o.emptyText()     목록이 비었을 때의 글(HTML)
//     o.olderNote       이전 요청이 있을 때 목록 위에 보일 안내(HTML) - 없으면 안 보인다
//     o.typed           {get(), set(v)} 입력 중인 글의 임시 저장 - 없으면 끈다
//     o.preClick(e)     목록을 눌렀을 때 공용 처리보다 먼저 볼 것 - 처리했으면 true(async)
//     o.onRender(info)  그린 뒤({recent, older, list, open}) · o.onChange() 요청 목록이 바뀔 때(render 뒤) · o.onDeckChanged() 문서를 곧 다시 읽게
(function (root) {
  "use strict";
  function mount(o) {
    const $ = (s) => document.querySelector(s), st = o.state, compose = o.compose || "#side .compose";
    if (!root.NexaRequests) return null;
    if (!Array.isArray(st.reqs)) st.reqs = [];
    const ready = () => (o.ready ? o.ready() : true);
    let RQ = null;
    const SESS = root.NexaSession ? root.NexaSession.create({ api: o.api, toast: o.toast, openMenu: o.openMenu, esc: o.esc, base: o.base, deckId: o.deckId,
      onChange: (s, changed) => { st.session = s; if (changed && ready()) render(); } }) : null;
    function render() {
      if (!RQ || !ready()) return;
      const recent = st.reqs.filter(RQ.recent), older = st.reqs.length - recent.length, list = o.filter ? recent.filter(o.filter.test) : recent;
      $("#reqFilter").innerHTML = (o.filter ? o.filter.html(recent) : `<span class="hint">최근 요청 ${recent.length}건</span>`)
        + `<span style="flex:1"></span><button class="chip sm" id="reqMore" title="이전 요청까지 모두 찾아보기(편집 화면 위에 뜹니다)">더보기${older ? ` · 이전 ${older}` : ""}</button>`;
      $("#reqList").innerHTML = (older && o.olderNote ? o.olderNote : "") + (list.length ? RQ.threadsHtml(list) : `<div class="hint" style="padding:18px;text-align:center">${o.emptyText ? o.emptyText() : "최근 요청이 없습니다"}</div>`);
      $("#reqHint").innerHTML = RQ.sessionHint();
      if (o.onRender) o.onRender({ recent, older, list, open: st.reqs.filter((q) => q.status === "open" || q.status === "working").length });
      RQ.afterRender();
    }
    RQ = root.NexaRequests.create({ api: o.api, toast: o.toast, esc: o.esc, base: o.base, deckId: o.deckId, session: SESS, getReqs: () => st.reqs, setReqs: (l) => { st.reqs = l; },
      onChange: () => { if (!ready()) return; render(); if (o.onChange) o.onChange(); }, target: o.target, att: { boxes: { tab: "#reqAtt", fu: "#fuAtt" } }, onDeckChanged: o.onDeckChanged });
    async function send() {
      const ta = $("#reqText"), text = ta.value.trim();
      if (!text && !RQ.att.slot("tab").length) { ta.focus(); return; }
      if (o.beforeSend) await o.beforeSend();
      const r = await RQ.add({ action: "add", status: "open", ...(o.buildBody ? o.buildBody() : {}), text: text || "(첨부 참고)" }, "tab", { flush: true });
      if (!r) return;
      ta.value = ""; if (o.typed) o.typed.set("");
      o.toast(RQ.connected() ? "요청을 세션에 보냈습니다" : "요청을 남겼습니다 - 세션이 연결되면 전달됩니다");
    }
    const chip = $("#sessChip"); if (chip) chip.onclick = (e) => (SESS ? SESS.menu(e.currentTarget) : null);
    $("#reqSend").onclick = send;
    // Enter = 보내기, Shift+Enter = 줄바꿈(한글 조합 중 Enter 는 조합 확정만)
    $("#reqText").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    if (o.typed) { $("#reqText").addEventListener("input", () => o.typed.set($("#reqText").value.trim() ? $("#reqText").value : "")); const v = o.typed.get(); if (v) $("#reqText").value = v; }
    $("#reqList").addEventListener("click", async (e) => {
      if (o.preClick && (await o.preClick(e))) return;
      if (await RQ.click(e)) return;
      const c = e.target.closest(".req[data-rid]"), r = c && st.reqs.find((q) => q.id === c.dataset.rid);
      if (r && !e.target.closest("button, a, textarea, input") && o.target.goto) o.target.goto(r);
    });
    $("#reqList").addEventListener("keydown", (e) => RQ.keydown(e));  // 후속 입력칸 Enter = 보내기 · Esc = 닫기
    RQ.att.wire($(compose), "tab");                                    // 요청 첨부 - 붙여넣기(그림)·끌어다 놓기
    $(compose).addEventListener("click", (e) => RQ.click(e));          // ＋ 첨부 · 빼기 · 축소판 · 세션 시작 링크
    $("#reqFilter").addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.id === "reqMore") { RQ.openHist(); return; }
      if (o.filter && o.filter.click && o.filter.click(b)) render();
    });
    /** 판(/api/version)의 응답 - 세션 표시와 요청 목록을 따라간다 */
    async function onVersion(v) { if (v && v.session && SESS) SESS.render(v.session, v.activity); if (v) await RQ.sync(v); }
    return { SESS, RQ, render, send, onVersion, load: async () => { await RQ.load(); render(); } };
  }
  root.NexaReqPanel = { mount };
})(typeof window !== "undefined" ? window : globalThis);
