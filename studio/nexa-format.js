// nexa-format.js - 글자 서식 단추(공용 컴포넌트) - 글 편집 엔진(nexa-text.js)에 붙는 굵게·기울임·밑줄·취소선·첨자·색·형광 단추.
//   페이지 편집기의 서식 막대와 슬라이드 편집기의 "글 편집 중" 서식 줄이 같이 쓴다(PG-043 · PG-108 - 시트 셀이 nexa-text 를 쓰게 되면 거기도).
//   NexaFormat.html(keys, opts)   → 단추들의 HTML. keys = ["b","i","u","s","sup","sub","c","hl"] 중에서, opts: cls(단추 class) · color(c) → CSS 색(강조 색 견본)
//   NexaFormat.bind(host, editor, opts) → 단추를 누르면 editor()(지금 편집기 - nexa-text mount 의 결과)의 선택에 서식을 건다.
//        mousedown 에서 처리하고 기본 동작을 막는다 - 편집 상자의 선택·초점을 잃지 않게. opts: values {c, hl} 색·형광 값(함수면 누를 때 부른다) · after() 누른 뒤
//   NexaFormat.sync(host, marks)  → 지금 선택의 서식(editor.state().marks)대로 단추에 on 표시
(function (root) {
  "use strict";
  const DEFS = {
    b: ["<b>가</b>", "굵게 (Ctrl+B)"], i: ["<i>가</i>", "기울임 (Ctrl+I)"], u: ["<u>가</u>", "밑줄 (Ctrl+U)"], s: ["<s>가</s>", "취소선"],
    sup: ["x²", "위 첨자"], sub: ["x₂", "아래 첨자"], c: [null, "강조 색"], hl: [null, "형광펜"],
  };
  const VALUES = { c: "primary", hl: "#fff59d" };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  function html(keys, opts = {}) {
    const cls = opts.cls || "btn", col = opts.color ? opts.color(VALUES.c) : "#c8553d";
    return (keys || Object.keys(DEFS)).filter((k) => DEFS[k]).map((k) => {
      const label = k === "c" ? `<span style="color:${esc(col)}">가</span>` : k === "hl" ? `<span style="background:${VALUES.hl}">가</span>` : DEFS[k][0];
      return `<button type="button" class="${esc(cls)}" data-mark="${k}" title="${esc(DEFS[k][1])}">${label}</button>`;
    }).join("");
  }
  function bind(host, editor, opts = {}) {
    const vals = { ...VALUES, ...(opts.values || {}) };
    const on = (e) => {
      const b = e.target.closest("[data-mark]"); if (!b || !host.contains(b) || b.disabled) return;
      const ed = editor(); if (!ed) return;
      e.preventDefault();
      const k = b.dataset.mark;
      if (k === "c" || k === "hl") ed.toggle(k, typeof vals[k] === "function" ? vals[k]() : vals[k]); else ed.toggle(k);
      if (opts.after) opts.after(k);
    };
    host.addEventListener("mousedown", on);
    // 마우스 없이 누른 경우(키보드 · 스크립트의 click()) - 마우스로 누른 click 은 detail 이 1 이상이라 건너뛴다(mousedown 에서 이미 처리)
    host.addEventListener("click", (e) => { if (!e.detail) on(e); });
    return () => host.removeEventListener("mousedown", on);
  }
  function sync(host, marks) { for (const el of host.querySelectorAll("[data-mark]")) el.classList.toggle("on", !!(marks || {})[el.dataset.mark]); }

  root.NexaFormat = { DEFS, VALUES, html, bind, sync };
})(typeof window !== "undefined" ? window : globalThis);
