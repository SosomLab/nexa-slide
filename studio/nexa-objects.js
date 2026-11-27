// nexa-objects.js - 떠 있는 개체의 조작(공용) - 고르기 · 끌어 옮기기 · 크기 손잡이 · 화살표 이동 · 지우기 · 복제 · Esc.
//   슬라이드 요소 · 페이지 도형·글 상자 · 시트 그림이 **같은 기준**으로 움직이게 한다(사용자 결정 2026-11-27 - docs/dev/page-editor/design.md 10-5 동작 기준표).
//   기준(세 화면 공통):
//     · 고르기 = 누르면 하나(여럿 고른 것 중 하나를 누르기만 해도 그것만), Shift·Ctrl 로 더하기·빼기, 바깥을 누르거나 Esc 로 풀림
//     · 끌기 = 화면 3px 을 넘으면 시작, 고른 것 모두 같이, Shift = 가로·세로 한 축으로, 놓을 때 한 번 모델에 쓴다(실행 취소 한 단계)
//     · 크기 = 8방향 손잡이(선은 양 끝 · 손잡이를 하나만 쓰는 화면은 se), 그림은 모서리에서 비율 유지(Shift 로 풀기) · 도형은 Shift 로 비율 유지, 최소 크기
//     · 화살표 = 한 걸음, Shift = 큰 걸음 · Delete/Backspace = 지우기 · Ctrl+D = 복제(어긋남은 어댑터 단위) · 잠긴 것은 옮기지도 지우지도 않는다
//   좌표 단위(px · mm)와 매이는 대상(캔버스 · 문단 · 칸)은 문서 종류의 성격이라 어댑터가 맡는다 - 이 모듈은 "모델 단위의 사각형"만 다룬다.
//   계산(DOM 없음): snap · resize · axisLock · inBox · nudge · guideSnap · HANDLES     (시험: tests/nexa_objects_check.js)
//   붙이기: NexaObjects.attach(o) → { selection(), select(ids), clear(), refresh(), destroy() }
//     o.layers        개체 요소가 든 레이어들(이벤트를 건다) · o.hit(target) → 개체 id | null(글 편집 중인 자리 등은 null)
//     o.el(id)        그 개체의 요소 · o.rect(id) → {x,y,w,h}(모델 단위) · o.scale() → 화면 px ÷ 모델 단위
//     o.rules(id)     → {ratio: "keep"|"shift"|"none", min, line?, locked?} · o.step = [한 걸음, 큰 걸음] · o.dupOffset
//     o.preview(id, rect | null)   끄는 중 표시(null = 되돌리기) · o.commit([{id, rect}], why)   놓을 때 모델에 쓰기("move" | "resize" | "nudge")
//     o.remove(ids) · o.duplicate(ids) → 새 id 들 · o.onSelect(ids) · o.editing() → true 면 키를 받지 않는다 · o.multi(기본 true)
(function (root) {
  "use strict";
  const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
  const snap = (v, grid) => (grid > 0 ? Math.round(v / grid) * grid : v);
  /** 한 축으로만 - 더 많이 움직인 쪽을 남긴다(Shift 끌기) */
  const axisLock = (dx, dy) => (Math.abs(dx) >= Math.abs(dy) ? [dx, 0] : [0, dy]);
  /** 사각형이 고르기 상자 안에 완전히 들어가는가 */
  const inBox = (r, b) => r.x >= b.x && r.y >= b.y && r.x + r.w <= b.x + b.w && r.y + r.h <= b.y + b.h;
  /** 화살표 키 → [dx, dy](아니면 null) */
  function nudge(key, big, step, bigStep) {
    const d = big ? bigStep : step, m = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] }[key];
    return m || null;
  }
  /** 손잡이를 (dx, dy) 만큼 끌었을 때의 사각형. opt: keep(비율 유지) · min(최소 크기, 선은 0) - 반대쪽 모서리·변이 고정된다 */
  function resize(r, handle, dx, dy, opt = {}) {
    const min = opt.min === undefined ? 1 : opt.min, W = handle.includes("w"), E = handle.includes("e"), N = handle.includes("n"), S = handle.includes("s");
    let w = r.w + (E ? dx : W ? -dx : 0), h = r.h + (S ? dy : N ? -dy : 0);
    if (opt.keep && r.w > 0 && r.h > 0) {
      const k = r.w / r.h;
      if ((E || W) && (N || S)) { if (Math.abs(w - r.w) / r.w >= Math.abs(h - r.h) / r.h) h = w / k; else w = h * k; }  // 모서리 - 더 많이 바뀐 쪽을 따른다
      else if (E || W) h = w / k; else w = h * k;
    }
    w = Math.max(min, w); h = Math.max(min, h);
    if (opt.keep && r.w > 0 && r.h > 0) { const k = r.w / r.h; if (w / h > k) h = w / k; else w = h * k; }  // 최소에 걸렸으면 모자란 쪽을 키워 비율을 맞춘다(둘 다 최소 이상)
    const x = W ? r.x + r.w - w : (!E && opt.keep && (N || S)) ? r.x + (r.w - w) / 2 : r.x;
    const y = N ? r.y + r.h - h : (!S && opt.keep && (E || W)) ? r.y + (r.h - h) / 2 : r.y;
    return { x, y, w, h };
  }
  /** 안내선에 붙이기 - 사각형의 왼쪽·가운데·오른쪽(위·가운데·아래)이 targets {x:[…], y:[…]} 에 tol 안으로 오면 붙인다 → {dx, dy, gx, gy}(붙은 선) */
  function guideSnap(r, targets, tol) {
    const out = { dx: 0, dy: 0, gx: null, gy: null };
    for (const [axis, at, size, d, g] of [["x", r.x, r.w, "dx", "gx"], ["y", r.y, r.h, "dy", "gy"]]) {
      let best = tol + 1e-9;
      for (const t of (targets && targets[axis]) || []) for (const p of [at, at + size / 2, at + size]) { const diff = t - p; if (Math.abs(diff) < Math.abs(best)) { best = diff; out[d] = diff; out[g] = t; } }
    }
    return out;
  }

  function attach(o) {
    const doc = (o.layers[0] || {}).ownerDocument || document, win = doc.defaultView;
    let sel = [], drag = null;
    const multi = o.multi !== false, rules = (id) => (o.rules ? o.rules(id) || {} : {});
    const mark = () => { for (const L of o.layers) for (const el of L.querySelectorAll(".nx-sel")) el.classList.remove("nx-sel", "sel"); for (const id of sel) { const el = o.el(id); if (el) el.classList.add("nx-sel", "sel"); } };
    function select(ids, quiet) {
      const next = [...new Set((ids || []).filter((id) => id != null))];
      const same = next.length === sel.length && next.every((id, i) => id === sel[i]);
      sel = next; mark(); if (!same && !quiet && o.onSelect) o.onSelect(sel.slice());
    }
    const clear = () => select([]);
    function onDown(e) {
      if (e.button !== 0 && e.button !== 2) return;
      const id = o.hit(e.target, e); if (id == null) return;
      const add = multi && (e.shiftKey || e.ctrlKey || e.metaKey);
      if (add) select(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]); else if (!sel.includes(id)) select([id]);
      if (e.button !== 0 || add || !sel.includes(id)) return;
      const handleEl = e.target.closest && e.target.closest("[data-nxh], .nx-h"), handle = handleEl ? handleEl.dataset.nxh || "se" : null;
      const ids = (handle ? [id] : sel).filter((x) => !rules(x).locked); if (!ids.length) return;
      e.preventDefault(); if (doc.activeElement && doc.activeElement.blur && !o.keepFocus) doc.activeElement.blur();
      drag = { hit: id, ids, handle, x: e.clientX, y: e.clientY, start: new Map(ids.map((x) => [x, o.rect(x)])), moved: false, last: null };
      win.addEventListener("pointermove", onMove); win.addEventListener("pointerup", onUp);
    }
    function calc(e) {
      const k = o.scale() || 1; let dx = (e.clientX - drag.x) / k, dy = (e.clientY - drag.y) / k;
      if (!drag.moved && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) < 3) return null;  // 화면 3px 을 넘어야 시작
      drag.moved = true;
      if (drag.handle) {
        const id = drag.ids[0], r = rules(id), keep = r.ratio === "keep" ? !e.shiftKey : r.ratio === "shift" ? e.shiftKey : false;
        return [{ id, rect: resize(drag.start.get(id), drag.handle, dx, dy, { keep, min: r.line ? 0 : r.min === undefined ? 1 : r.min }) }];
      }
      if (e.shiftKey) [dx, dy] = axisLock(dx, dy);
      return drag.ids.map((id) => { const s = drag.start.get(id); return { id, rect: { x: s.x + dx, y: s.y + dy, w: s.w, h: s.h } }; });
    }
    function onMove(e) { if (!drag) return; const list = calc(e); if (!list) return; drag.last = list; for (const it of list) o.preview(it.id, it.rect, drag.handle ? "resize" : "move"); }
    function onUp(e) {
      win.removeEventListener("pointermove", onMove); win.removeEventListener("pointerup", onUp);
      const d = drag; drag = null; if (!d) return;
      const list = d.last;
      if (!d.moved || !list) { if (!d.moved && !d.handle && sel.length > 1) select([d.hit]); return; }  // 여럿 고른 것 중 하나를 끌지 않고 누르기만 했으면 그것만 남긴다(PowerPoint 와 같다)
      for (const it of list) o.preview(it.id, null);
      o.commit(list, d.handle ? "resize" : "move");
      mark();
    }
    function onKey(e) {
      if (!sel.length || e.isComposing || (o.editing && o.editing(e))) return;
      const t = e.target; if (t && t.closest && t.closest("input, select, textarea, [contenteditable=true], .dlg, .nd-box")) return;
      const free = sel.filter((id) => !rules(id).locked), mod = e.ctrlKey || e.metaKey;
      if (e.key === "Escape") { e.preventDefault(); clear(); return; }
      if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); if (free.length) { const ids = free.slice(); select(sel.filter((id) => !ids.includes(id)), true); o.remove(ids); if (o.onSelect) o.onSelect(sel.slice()); } return; }
      if (mod && (e.key === "d" || e.key === "D") && o.duplicate) { e.preventDefault(); if (free.length) { const made = o.duplicate(free.slice()); if (made && made.length) select(made); } return; }
      if (mod || e.altKey) return;
      const step = o.step || [1, 8], mv = nudge(e.key, e.shiftKey, step[0], step[1]); if (!mv || !free.length) return;
      e.preventDefault();
      o.commit(free.map((id) => { const r = o.rect(id); return { id, rect: { x: r.x + mv[0], y: r.y + mv[1], w: r.w, h: r.h } }; }), "nudge"); mark();
    }
    const onDocDown = (e) => { if (!sel.length || drag) return; if (o.keepOn && o.keepOn(e)) return; if (o.layers.some((L) => L.contains(e.target)) && o.hit(e.target, e) != null) return; if (e.target.closest && e.target.closest(".menu")) return; clear(); };
    for (const L of o.layers) L.addEventListener("pointerdown", onDown);
    doc.addEventListener("mousedown", onDocDown);
    doc.addEventListener("keydown", onKey, true);
    return {
      selection: () => sel.slice(), select, clear, refresh: mark,
      destroy() { for (const L of o.layers) L.removeEventListener("pointerdown", onDown); doc.removeEventListener("mousedown", onDocDown); doc.removeEventListener("keydown", onKey, true); },
    };
  }

  root.NexaObjects = { HANDLES, snap, axisLock, inBox, nudge, resize, guideSnap, attach };
  if (typeof module !== "undefined" && module.exports) module.exports = root.NexaObjects;
})(typeof window !== "undefined" ? window : globalThis);
