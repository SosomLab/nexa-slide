/* nexa-slide 새 시트 대화 상자 - 제목 · 테마 · 넣을 페이지 · 문서 정보(과제명·고객사·작성자·버전). docs/sheets.md 5절.
   편집기(studio.js)와 시트 화면(sheet.js)이 같이 쓴다.
     NexaSheetNew.open()   → 만든 시트 id(취소면 null). POST /api/decks {action:"create", kind:"sheet", title, theme?, pages?, vars?}
   테마 목록 GET /api/sheet-themes, 테마 내용(vars 기본값) GET /api/sheet-themes/<이름>. 목록을 못 읽으면 테마 없는 빈 시트만 만든다. */
(function () {
  "use strict";
  const BASE = (location.pathname.match(/^\/w\/[^/]+/) || [""])[0];
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const VARS = [["project", "과제명"], ["client", "고객사"], ["author", "작성자"], ["version", "버전"]];
  const CSS = `
  .nx-sn { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 120; display: flex; align-items: center; justify-content: center; font: 13px/1.45 var(--font, "Malgun Gothic", sans-serif); color: var(--ink, #1F1B1B); }
  .nx-sn .box { background: #fff; border-radius: 18px; padding: 18px 22px; width: min(560px, 94vw); max-height: 88vh; overflow-y: auto; box-shadow: 0 6px 24px rgba(0,0,0,.16); display: flex; flex-direction: column; gap: 10px; }
  .nx-sn h3 { margin: 0; font-size: 16px; }
  .nx-sn label.f { display: block; font-weight: 700; font-size: 12px; margin: 2px 0 3px; }
  .nx-sn input[type=text], .nx-sn select { width: 100%; font: inherit; padding: 6px 9px; border: 1px solid var(--line, #D8C2C0); border-radius: 8px; background: #fff; box-sizing: border-box; }
  .nx-sn .pages { display: flex; flex-wrap: wrap; gap: 6px 14px; }
  .nx-sn .pages label { display: inline-flex; gap: 5px; align-items: center; }
  .nx-sn .vars { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; }
  .nx-sn .hint { color: var(--ink2, #534343); font-size: 12px; }
  .nx-sn .err { color: var(--err, #BA1A1A); font-size: 12px; min-height: 1em; }
  .nx-sn .acts { display: flex; gap: 6px; justify-content: flex-end; }
  .nx-sn button { font: inherit; border: 0; background: var(--tone, #F2EFEF); border-radius: 999px; padding: 6px 16px; cursor: pointer; }
  .nx-sn button.primary { background: var(--p, #A91F24); color: #fff; font-weight: 700; }
  .nx-sn button:disabled { opacity: .5; cursor: default; }`;
  async function call(method, url, body) {
    try {
      const r = await fetch(BASE + url, { method, cache: "no-store", headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
      let d = null; try { d = await r.json(); } catch (e) { /* 빈 응답 */ }
      if (window.NexaMenu && NexaMenu.auth401) NexaMenu.auth401(r, d);
      return { ok: r.ok, status: r.status, data: d };
    } catch (e) { return { ok: false, status: 0, data: null }; }
  }

  function open() {
    if (!document.getElementById("nx-sn-css")) { const st = document.createElement("style"); st.id = "nx-sn-css"; st.textContent = CSS; document.head.appendChild(st); }
    return new Promise((resolve) => {
      const back = document.createElement("div"); back.className = "nx-sn";
      back.innerHTML = `<div class="box" role="dialog" aria-label="새 시트">
        <h3>▦ 새 시트(엑셀)</h3>
        <div><label class="f" for="snTitle">제목</label><input type="text" id="snTitle" placeholder="예: 요구사항 정의서"></div>
        <div><label class="f" for="snTheme">테마</label><select id="snTheme"><option value="">테마 없음 - 빈 시트</option></select><div class="hint" id="snThemeHint">테마 목록을 읽는 중…</div></div>
        <div id="snPagesBox" hidden><label class="f">넣을 페이지</label><div class="pages" id="snPages"></div></div>
        <div id="snVarsBox" hidden><label class="f">문서 정보 <span class="hint" style="font-weight:400">- 페이지의 {{자리}} 에 들어갑니다(나중에 비워 둔 칸은 그대로)</span></label>
          <div class="vars">${VARS.map(([k, l]) => `<div><label class="f" for="snv-${k}" style="font-weight:400">${l}</label><input type="text" id="snv-${k}" data-var="${k}"></div>`).join("")}</div></div>
        <div class="err" id="snErr"></div>
        <div class="acts"><button id="snCancel">취소</button><button class="primary" id="snOk">만들기</button></div></div>`;
      document.body.appendChild(back);
      const $ = (s) => back.querySelector(s);
      let list = [], done = false;
      const close = (v) => { if (done) return; done = true; back.remove(); document.removeEventListener("keydown", onKey, true); resolve(v); };
      const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(null); } if (e.key === "Enter" && !e.isComposing && e.target.tagName === "INPUT") { e.preventDefault(); create(); } };
      document.addEventListener("keydown", onKey, true);
      back.addEventListener("mousedown", (e) => { if (e.target === back) close(null); });
      $("#snCancel").onclick = () => close(null);
      $("#snOk").onclick = () => create();
      setTimeout(() => $("#snTitle").focus(), 0);

      async function pickTheme() {
        const name = $("#snTheme").value, t = list.find((x) => x.name === name);
        const pages = (t && t.pages) || [];
        $("#snPagesBox").hidden = !pages.length; $("#snVarsBox").hidden = !name;
        $("#snPages").innerHTML = pages.map((pg, i) => `<label><input type="checkbox" data-pg="${esc(pg.kind || "")}" data-i="${i}" checked> ${esc(pg.name || pg.kind)}</label>`).join("");
        if (!name) return;
        const d = await call("GET", `/api/sheet-themes/${encodeURIComponent(name)}`);
        if ($("#snTheme").value !== name) return;
        const tv = (d.ok && d.data && d.data.vars) || {};
        for (const [k] of VARS) { const inp = $(`#snv-${k}`); if (!inp.value || inp.dataset.auto) { inp.value = tv[k] != null ? String(tv[k]) : ""; inp.dataset.auto = inp.value ? "1" : ""; } }
      }
      back.addEventListener("input", (e) => { if (e.target.dataset && e.target.dataset.var) e.target.dataset.auto = ""; });
      $("#snTheme").onchange = pickTheme;
      call("GET", "/api/sheet-themes").then((r) => {
        list = r.ok && Array.isArray(r.data) ? r.data : [];
        const sel = $("#snTheme");
        sel.innerHTML = `<option value="">테마 없음 - 빈 시트</option>` + list.map((t) => `<option value="${esc(t.name)}">${esc(t.label || t.name)}${t.source === "workspace" ? " · 작업 공간" : ""}</option>`).join("");
        const pre = list.find((t) => t.source === "workspace") || null;  // 회사 테마가 있으면 그것부터
        if (pre) sel.value = pre.name;
        $("#snThemeHint").textContent = list.length ? "셀 스타일·색·글꼴과 표지·이력 같은 페이지 틀을 테마에서 가져옵니다" : "테마가 없습니다 - 빈 시트로 만듭니다";
        pickTheme();
      });

      async function create() {
        const title = $("#snTitle").value.trim();
        if (!title) { $("#snErr").textContent = "제목을 적어 주세요"; $("#snTitle").focus(); return; }
        const theme = $("#snTheme").value, body = { action: "create", kind: "sheet", title };
        if (theme) {
          body.theme = theme;
          const boxes = [...back.querySelectorAll("#snPages input[type=checkbox]")];
          if (boxes.length) body.pages = boxes.filter((b) => b.checked).map((b) => b.dataset.pg);
          const vars = {}; for (const [k] of VARS) { const v = $(`#snv-${k}`).value.trim(); if (v) vars[k] = v; }
          body.vars = vars;
        }
        $("#snOk").disabled = true; $("#snErr").textContent = "";
        const r = await call("POST", "/api/decks", body);
        $("#snOk").disabled = false;
        if (!r.ok || !r.data || !r.data.id) { $("#snErr").textContent = "만들지 못했습니다: " + ((r.data && r.data.error) || r.status); return; }
        close(r.data.id);
      }
    });
  }
  window.NexaSheetNew = { open };
})();
