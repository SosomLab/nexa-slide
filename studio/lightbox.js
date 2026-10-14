/* 첨부 미리보기(라이트박스 + 캐러셀) - 요청 첨부 축소판을 누르면 새 창 대신 화면 위 오버레이로 본다. 편집기(studio.js)·시작 페이지 서버 작업 카드가 같이 쓴다.
     NexaLightbox.open(items, index, opts)   items = [{url, name, size?, type?}], opts = {title?, alt?: {label, items}}  (alt = 범위 넓혀 보기 토글, 예 "이 슬라이드의 모든 요청 첨부")
   조작: ◀ ▶ · ← → 키 · 스와이프 · 아래 축소판 줄 · Esc/바깥/✕ 닫기 · 휠 확대 · 끌어 이동 · 두 번 누르기 = 맞춤/원본 · [원본 열기] [내려받기]. PDF 는 iframe, 그 밖 문서는 아이콘 카드 + [열기]. */
(function () {
  const CSS = `
  .nx-lb { position: fixed; inset: 0; z-index: 1200; background: rgba(0,0,0,.86); display: flex; flex-direction: column; font: 13px/1.4 var(--font, "Malgun Gothic", sans-serif); color: #eee; user-select: none; }
  .nx-lb .top { display: flex; align-items: center; gap: 10px; padding: 8px 12px; flex: none; }
  .nx-lb .top .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .nx-lb .top .cnt { opacity: .8; }
  .nx-lb .top button, .nx-lb .top a { border: 1px solid rgba(255,255,255,.3); background: rgba(255,255,255,.08); color: #fff; border-radius: 999px; padding: 3px 11px; font: inherit; cursor: pointer; text-decoration: none; }
  .nx-lb .top button:hover, .nx-lb .top a:hover { background: rgba(255,255,255,.18); }
  .nx-lb .top button.on { background: rgba(255,255,255,.3); }
  .nx-lb .stage { flex: 1; min-height: 0; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: grab; }
  .nx-lb .stage.drag { cursor: grabbing; }
  .nx-lb .stage img { max-width: 96%; max-height: 96%; object-fit: contain; transform-origin: center; transition: transform .08s; box-shadow: 0 8px 40px rgba(0,0,0,.6); }
  .nx-lb .stage img.free { max-width: none; max-height: none; }
  .nx-lb .stage iframe { width: 92%; height: 96%; border: 0; background: #fff; border-radius: 6px; }
  .nx-lb .stage .doc { background: rgba(255,255,255,.08); border-radius: 14px; padding: 28px 36px; text-align: center; font-size: 14px; }
  .nx-lb .stage .doc .ic { font-size: 56px; margin-bottom: 8px; }
  .nx-lb .nav { position: absolute; top: 50%; transform: translateY(-50%); width: 44px; height: 64px; border: 0; background: rgba(0,0,0,.35); color: #fff; font-size: 26px; cursor: pointer; border-radius: 8px; }
  .nx-lb .nav:hover { background: rgba(0,0,0,.6); } .nx-lb .nav.l { left: 10px; } .nx-lb .nav.r { right: 10px; } .nx-lb .nav:disabled { opacity: .25; cursor: default; }
  .nx-lb .strip { flex: none; display: flex; gap: 6px; justify-content: center; padding: 8px 12px 10px; overflow-x: auto; }
  .nx-lb .strip button { flex: none; width: 64px; height: 46px; border: 2px solid transparent; border-radius: 7px; padding: 0; background: rgba(255,255,255,.08); overflow: hidden; cursor: pointer; color: #ddd; font-size: 20px; }
  .nx-lb .strip button img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .nx-lb .strip button.on { border-color: #fff; }`;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const isImg = (a) => /^image\//.test(a.type || "") || /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(a.name || a.url || "");
  const isPdf = (a) => /pdf/.test(a.type || "") || /\.pdf$/i.test(a.name || a.url || "");
  const kb = (n) => (n == null ? "" : n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))}KB` : `${(n / 1024 / 1024).toFixed(1)}MB`);
  let root = null, st = null;

  function build() {
    const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s);
    root = document.createElement("div"); root.className = "nx-lb"; root.setAttribute("role", "dialog"); root.setAttribute("aria-label", "첨부 미리보기");
    root.innerHTML = `<div class="top"><span class="cnt"></span><span class="name"></span><button type="button" class="alt" style="display:none"></button><a class="orig" target="_blank" rel="noopener">원본 열기</a><a class="dl" download>내려받기</a><button type="button" class="x" aria-label="닫기">✕</button></div>
      <div class="stage"><button type="button" class="nav l" aria-label="이전">‹</button><div class="body"></div><button type="button" class="nav r" aria-label="다음">›</button></div><div class="strip"></div>`;
    root.style.display = "none";
    document.body.appendChild(root);
    root.querySelector(".x").onclick = close;
    root.querySelector(".nav.l").onclick = () => go(st.i - 1);
    root.querySelector(".nav.r").onclick = () => go(st.i + 1);
    root.querySelector(".alt").onclick = () => { st.useAlt = !st.useAlt; const cur = st.list[st.i]; st.list = st.useAlt ? st.alt.items : st.base; st.i = Math.max(0, st.list.findIndex((a) => a.url === cur.url)); render(); };
    const stage = root.querySelector(".stage");
    stage.addEventListener("click", (e) => { if (e.target === stage || e.target.classList.contains("body")) close(); });
    stage.addEventListener("wheel", (e) => { const img = stage.querySelector("img"); if (!img) return; e.preventDefault(); zoomTo(st.z * (e.deltaY < 0 ? 1.15 : 1 / 1.15)); }, { passive: false });
    stage.addEventListener("dblclick", (e) => { if (e.target.tagName === "IMG") { zoomTo(st.z === 1 ? Math.max(1.01, e.target.naturalWidth / e.target.getBoundingClientRect().width * st.z) : 1); } });
    let drag = null;
    stage.addEventListener("pointerdown", (e) => { if (e.target.tagName === "IMG" || e.target.classList.contains("body")) { drag = { x: e.clientX, y: e.clientY, tx: st.tx, ty: st.ty, moved: false }; stage.setPointerCapture(e.pointerId); stage.classList.add("drag"); } });
    stage.addEventListener("pointermove", (e) => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true; if (st.z > 1) { st.tx = drag.tx + dx; st.ty = drag.ty + dy; applyT(); } });
    stage.addEventListener("pointerup", (e) => { if (!drag) return; const dx = e.clientX - drag.x; stage.classList.remove("drag"); if (st.z <= 1 && Math.abs(dx) > 60) go(st.i + (dx < 0 ? 1 : -1)); drag = null; });  // 스와이프
    root.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") go(st.i - 1); else if (e.key === "ArrowRight") go(st.i + 1); e.stopPropagation(); });
    root.querySelector(".strip").addEventListener("click", (e) => { const b = e.target.closest("[data-i]"); if (b) go(+b.dataset.i); });
  }
  function applyT() { const img = root.querySelector(".stage img"); if (img) { img.style.transform = `translate(${st.tx}px, ${st.ty}px) scale(${st.z})`; } }
  function zoomTo(z) { st.z = Math.min(8, Math.max(1, z)); if (st.z === 1) { st.tx = st.ty = 0; } applyT(); }
  function render() {
    const a = st.list[st.i]; if (!a) return close();
    st.z = 1; st.tx = st.ty = 0;
    root.querySelector(".cnt").textContent = `${st.i + 1} / ${st.list.length}`;
    root.querySelector(".name").textContent = `${a.name || ""}${a.size ? ` · ${kb(a.size)}` : ""}${st.title ? ` · ${st.title}` : ""}`;
    root.querySelector(".orig").href = a.url; root.querySelector(".dl").href = a.url; root.querySelector(".dl").setAttribute("download", a.name || "");
    const alt = root.querySelector(".alt");
    if (st.alt && st.alt.items && st.alt.items.length > st.base.length) { alt.style.display = ""; alt.textContent = st.alt.label; alt.classList.toggle("on", !!st.useAlt); } else alt.style.display = "none";
    const body = root.querySelector(".body");
    body.innerHTML = isImg(a) ? `<img src="${esc(a.url)}" alt="${esc(a.name || "")}" draggable="false">`
      : isPdf(a) ? `<iframe src="${esc(a.url)}" title="${esc(a.name || "PDF")}"></iframe>`
      : `<div class="doc"><div class="ic">📄</div><div>${esc(a.name || "")}${a.size ? ` · ${kb(a.size)}` : ""}</div><div style="margin-top:12px"><a href="${esc(a.url)}" target="_blank" rel="noopener" style="color:#fff">열기 ↗</a></div></div>`;
    root.querySelector(".nav.l").disabled = st.i <= 0; root.querySelector(".nav.r").disabled = st.i >= st.list.length - 1;
    root.querySelector(".strip").innerHTML = st.list.length > 1 ? st.list.map((x, i) => `<button type="button" data-i="${i}" class="${i === st.i ? "on" : ""}" title="${esc(x.name || "")}">${isImg(x) ? `<img src="${esc(x.url)}" alt="" loading="lazy">` : "📄"}</button>`).join("") : "";
    const on = root.querySelector(".strip .on"); if (on && on.scrollIntoView) on.scrollIntoView({ inline: "center", block: "nearest" });
  }
  function go(i) { if (!st || i < 0 || i >= st.list.length) return; st.i = i; render(); }
  function open(items, index = 0, opts = {}) {
    if (!items || !items.length) return;
    if (!root) build();
    st = { base: items.slice(), list: items.slice(), i: Math.max(0, Math.min(index, items.length - 1)), z: 1, tx: 0, ty: 0, title: opts.title || "", alt: opts.alt || null, useAlt: false, prev: document.activeElement };
    root.style.display = ""; root.tabIndex = -1; render(); root.focus();
  }
  function close() { if (!root) return; root.style.display = "none"; root.querySelector(".body").innerHTML = ""; if (st && st.prev && st.prev.focus) st.prev.focus(); st = null; }
  window.NexaLightbox = { open, close };
})();
