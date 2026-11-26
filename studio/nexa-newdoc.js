// 공용 "새 문서" 대화 상자 - 슬라이드 · 시트 · 페이지 중에서 골라 만든다. 세 편집기가 같이 쓴다(docs/dev/page-editor/design.md 8절).
//   NexaNewDoc.open({ api, kind? }) → 만든 문서 {id, kind}(취소면 null). api = NexaShell 의 api(method, url, body).
//   종류는 NexaKinds.list(experimental) - 실험 종류(페이지)는 /api/config 의 experimental 에 있을 때만 보인다.
//   페이지는 템플릿을 고른다(GET /api/page-templates - 자주 쓴 것이 앞). 시트는 테마 대화 상자(NexaSheetNew)가 있으면 그것으로 넘긴다.
//   스타일은 이 파일이 싣는다(세 화면의 CSS 가 아직 따로라서 - 공용 스타일 PG-012 뒤에 옮긴다).
(function (root) {
  "use strict";
  const CSS = `
.nd-back { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 900; display: flex; align-items: center; justify-content: center; }
.nd-box { background: #fff; color: #1f1f1f; border-radius: 12px; box-shadow: 0 18px 60px rgba(0,0,0,.3); width: min(720px, calc(100vw - 32px)); max-height: calc(100vh - 48px); display: flex; flex-direction: column; font: 13px/1.5 inherit; }
.nd-box h3 { margin: 0; padding: 16px 20px 8px; font-size: 16px; }
.nd-kinds { display: flex; gap: 8px; padding: 4px 20px 10px; }
.nd-kinds button { flex: 1; border: 1px solid #d9d6d0; background: #fff; border-radius: 10px; padding: 10px 8px; cursor: pointer; font: inherit; text-align: left; }
.nd-kinds button b { display: block; font-size: 14px; } .nd-kinds button small { color: #7a756d; }
.nd-kinds button.on { border-color: #c8553d; background: #fff3ef; }
.nd-body { padding: 0 20px; overflow: auto; }
.nd-body label { display: block; font-weight: 600; margin: 8px 0 4px; }
.nd-body input[type=text] { width: 100%; padding: 8px 10px; border: 1px solid #d9d6d0; border-radius: 8px; font: inherit; }
.nd-tpls { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; padding-bottom: 6px; }
.nd-tpl { border: 1px solid #d9d6d0; border-radius: 10px; padding: 9px 10px; cursor: pointer; background: #fff; text-align: left; font: inherit; position: relative; min-height: 64px; }
.nd-tpl b { display: block; } .nd-tpl small { color: #7a756d; display: block; line-height: 1.35; }
.nd-tpl.on { border-color: #c8553d; background: #fff3ef; }
.nd-tpl .rec { position: absolute; top: 6px; right: 8px; font-size: 10px; color: #c8553d; }
.nd-group { grid-column: 1 / -1; color: #7a756d; font-size: 11px; margin-top: 4px; }
.nd-foot { display: flex; gap: 8px; justify-content: flex-end; padding: 12px 20px 16px; }
.nd-foot button { border: 1px solid #d9d6d0; background: #fff; border-radius: 8px; padding: 7px 16px; font: inherit; cursor: pointer; }
.nd-foot button.primary { background: #c8553d; border-color: #c8553d; color: #fff; } .nd-foot button:disabled { opacity: .5; cursor: default; }
.nd-err { color: #a3301c; padding: 0 20px; min-height: 1.2em; }
`;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const DESC = { deck: "발표 자료 (PowerPoint)", sheet: "표 · 계산 (Excel)", page: "문서 (Word · Pages)" };

  async function open(opts = {}) {
    const api = opts.api, doc = document;
    if (!doc.getElementById("nd-css")) { const s = doc.createElement("style"); s.id = "nd-css"; s.textContent = CSS; doc.head.appendChild(s); }
    const cfg = await api("GET", "/api/config");
    const kinds = root.NexaKinds.list((cfg.ok && cfg.data && cfg.data.experimental) || []);
    let kind = kinds.some((k) => k.kind === opts.kind) ? opts.kind : kinds[0].kind, tpls = null, tpl = "blank";
    return new Promise((resolve) => {
      const back = doc.createElement("div"); back.className = "nd-back";
      back.innerHTML = `<div class="nd-box" role="dialog" aria-label="새 문서"><h3>새 문서</h3><div class="nd-kinds"></div><div class="nd-body"><label for="ndTitle">제목</label><input type="text" id="ndTitle" maxlength="200" placeholder="문서 제목"><div id="ndExtra"></div></div><div class="nd-err" id="ndErr"></div><div class="nd-foot"><button id="ndCancel">취소</button><button id="ndOk" class="primary">만들기</button></div></div>`;
      doc.body.appendChild(back);
      const q = (s) => back.querySelector(s), title = q("#ndTitle");
      const end = (v) => { back.remove(); doc.removeEventListener("keydown", onKey, true); resolve(v); };
      function onKey(e) { if (e.key === "Escape") { e.stopPropagation(); end(null); } else if (e.key === "Enter" && e.target === title) { e.preventDefault(); create(); } }
      doc.addEventListener("keydown", onKey, true);
      function drawKinds() {
        q(".nd-kinds").innerHTML = kinds.map((k) => `<button data-kind="${k.kind}" class="${k.kind === kind ? "on" : ""}"><b>${k.icon} ${esc(k.label)}</b><small>${esc(DESC[k.kind] || "")}</small></button>`).join("");
      }
      async function drawExtra() {
        const box = q("#ndExtra"); box.innerHTML = "";
        title.placeholder = { deck: "새 덱 제목", sheet: "새 시트 제목", page: "새 문서 제목" }[kind] || "제목";
        if (kind === "sheet" && root.NexaSheetNew) { box.innerHTML = `<p style="color:#7a756d">[만들기]를 누르면 시트 테마·페이지를 고르는 창으로 넘어갑니다.</p>`; return; }
        if (kind !== "page") return;
        if (!tpls) { const r = await api("GET", "/api/page-templates"); tpls = r.ok && Array.isArray(r.data) ? r.data : []; if (kind !== "page") return; }
        let html = `<label>템플릿</label><div class="nd-tpls">`, group = null;
        for (const t of tpls) {
          if (t.rec && group !== "rec") { group = "rec"; html += `<div class="nd-group">자주 쓰는 템플릿</div>`; }
          else if (!t.rec && group !== t.group) { group = t.group; html += `<div class="nd-group">${esc(t.groupLabel || t.group)}</div>`; }
          html += `<button class="nd-tpl ${t.name === tpl ? "on" : ""}" data-tpl="${esc(t.name)}" title="${esc(t.desc)}"><b>${esc(t.label)}</b><small>${esc(t.desc)}</small>${t.used ? `<span class="rec">${t.used}회</span>` : ""}</button>`;
        }
        box.innerHTML = html + `</div><p style="margin:8px 0 0"><button type="button" class="nd-tpl" id="ndImport" style="min-height:0;display:inline-block">Word 문서(.docx)에서 가져오기</button><input type="file" id="ndFile" accept=".docx" hidden></p>`;
      }
      async function create() {
        const t = title.value.trim();
        if (kind === "sheet" && root.NexaSheetNew) { end(null); const id = await root.NexaSheetNew.open(); resolve(id ? { id, kind: "sheet" } : null); return; }
        if (!t) { q("#ndErr").textContent = "제목을 적어 주세요"; title.focus(); return; }
        q("#ndOk").disabled = true;
        const body = { action: "create", title: t }; if (kind !== "deck") body.kind = kind; if (kind === "page" && tpl) body.theme = tpl;
        const r = await api("POST", "/api/decks", body);
        if (!r.ok || !r.data || !r.data.id) { q("#ndErr").textContent = "만들지 못했습니다: " + ((r.data && r.data.error) || r.status); q("#ndOk").disabled = false; return; }
        end({ id: r.data.id, kind, title: t, decks: r.data.decks });  // decks = 만든 뒤의 덱 목록(서버 응답) - 부른 화면이 바로 목록을 갱신하게
      }
      back.addEventListener("mousedown", (e) => { if (e.target === back) end(null); });
      back.addEventListener("click", (e) => {
        const k = e.target.closest("[data-kind]"), tp = e.target.closest("[data-tpl]");
        if (k) { kind = k.dataset.kind; drawKinds(); drawExtra(); title.focus(); }
        else if (tp) { tpl = tp.dataset.tpl; back.querySelectorAll(".nd-tpl").forEach((x) => x.classList.toggle("on", x === tp)); }
        else if (e.target.id === "ndImport") q("#ndFile").click();
        else if (e.target.id === "ndCancel") end(null);
        else if (e.target.id === "ndOk") create();
      });
      // Word 문서 가져오기 - 파일을 고르면 바로 올려 페이지 문서를 만든다(제목 칸이 비어 있으면 문서의 제목·파일 이름)
      back.addEventListener("change", async (e) => {
        if (e.target.id !== "ndFile") return;
        const f = e.target.files[0]; if (!f) return;
        if (!/\.docx$/i.test(f.name)) { q("#ndErr").textContent = "Word 문서(.docx)만 가져올 수 있습니다"; return; }
        q("#ndErr").textContent = "가져오는 중…"; q("#ndOk").disabled = true;
        const data = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1] || ""); fr.onerror = rej; fr.readAsDataURL(f); });
        const r = await api("POST", "/api/decks", { action: "import", name: f.name, title: title.value.trim(), data });
        if (!r.ok || !r.data || !r.data.id) { q("#ndErr").textContent = "가져오지 못했습니다: " + ((r.data && r.data.error) || r.status); q("#ndOk").disabled = false; return; }
        end({ id: r.data.id, kind: "page", title: r.data.title, decks: r.data.decks, warnings: r.data.warnings || [] });
      });
      drawKinds(); drawExtra(); title.focus();
    });
  }
  root.NexaNewDoc = { open };
})(typeof window !== "undefined" ? window : globalThis);
