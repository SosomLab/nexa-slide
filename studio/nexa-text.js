// 글 편집 엔진(공용) - 서식 있는 글의 모델과 연산. 페이지 본문·표 셀·머리말이 쓰고, 뒤에 슬라이드 글 상자·시트 셀도 쓴다(docs/dev/page-editor/design.md 5절).
//   문단의 글 = runs: [{t: "글", b, i, u, s, c, hl, sup, sub, font, size, link, ruby}] - t 말고는 모두 서식(mark). 없는 키 = 꺼짐.
//   위치(offset)는 문단 안 UTF-16 코드 단위 - DOM Range 의 offset 과 같은 단위라 선택 변환이 단순하다.
//   모든 연산은 **새 배열을 돌려주고 입력을 고치지 않는다**. 결과는 늘 정규화돼 있다(빈 조각 없음 · 서식이 같은 이웃은 합침 · 꺼진 서식 키 없음).
//   이 파일은 모델만 다룬다(DOM 없음 - node 에서 시험: tests/nexa_text_check.js). 입력·선택·그리기는 같은 파일의 뒤쪽 절에 더한다(PG-031).
(function (root) {
  "use strict";
  const MARKS = ["b", "i", "u", "s", "c", "hl", "sup", "sub", "font", "size", "link", "ruby"];
  const BOOL = new Set(["b", "i", "s", "sup", "sub"]);  // 켜짐/꺼짐뿐인 서식(u 는 종류가 있다: true | "double" | "dot" …)
  const EXCL = { sup: "sub", sub: "sup" };  // 함께 켤 수 없는 짝 - 하나를 켜면 다른 하나는 끈다

  /** 조각의 서식만 - 꺼진 것(false · null · undefined · "")은 뺀다 */
  function marksOf(r) {
    const m = {};
    for (const k of MARKS) { const v = r[k]; if (v !== undefined && v !== null && v !== false && v !== "" && v !== 0) m[k] = BOOL.has(k) ? true : v; }
    return m;
  }
  function sameMarks(a, b) {
    for (const k of MARKS) if ((a[k] === undefined ? null : a[k]) !== (b[k] === undefined ? null : b[k])) return false;
    return true;
  }
  const mk = (t, m) => ({ t, ...m });

  /** 정규화 - 빈 조각을 버리고, 서식이 같은 이웃을 합치고, 꺼진 서식 키를 뺀다. 글이 없으면 [] */
  function normalize(runs) {
    const out = [];
    for (const r of runs || []) {
      if (!r || typeof r.t !== "string" || !r.t) continue;
      const m = marksOf(r), last = out[out.length - 1];
      if (last && sameMarks(last, m)) last.t += r.t; else out.push(mk(r.t, m));
    }
    return out;
  }
  const length = (runs) => (runs || []).reduce((n, r) => n + (r.t ? r.t.length : 0), 0);
  const text = (runs) => (runs || []).map((r) => r.t || "").join("");
  const fromPlain = (s, marks) => (s ? [mk(String(s), marksOf(marks || {}))] : []);
  const clamp = (runs, at) => Math.max(0, Math.min(length(runs), at | 0));

  /** [from, to) 구간의 조각들 */
  function slice(runs, from, to) {
    const n = length(runs); from = clamp(runs, from); to = to === undefined ? n : clamp(runs, to);
    const out = []; let pos = 0;
    for (const r of runs || []) {
      const end = pos + r.t.length;
      if (end > from && pos < to) out.push(mk(r.t.slice(Math.max(0, from - pos), Math.min(r.t.length, to - pos)), marksOf(r)));
      pos = end;
    }
    return normalize(out);
  }
  /** at 에서 둘로 - [앞, 뒤] */
  const split = (runs, at) => [slice(runs, 0, at), slice(runs, at)];
  const join = (a, b) => normalize([...(a || []), ...(b || [])]);

  /** 그 위치에서 글을 치면 붙을 서식 - 바로 앞 글자의 서식(문단 맨 앞이면 첫 글자의 것). 링크·윗주는 이어 붙지 않는다(끝에서 치면 빠져나온다) */
  function marksAt(runs, at) {
    at = clamp(runs, at); let pos = 0, hit = null;
    for (const r of runs || []) { const end = pos + r.t.length; if (at > pos && at <= end) { hit = { r, atEnd: at === end }; break; } pos = end; }
    if (!hit) { const first = (runs || [])[0]; if (!first) return {}; hit = { r: first, atEnd: false, head: true }; }
    const m = marksOf(hit.r);
    if (hit.atEnd || hit.head) { delete m.link; delete m.ruby; }
    return m;
  }
  /** 구간 전체에 공통인 서식(서식 막대의 켜짐 표시) - 구간이 비면 marksAt */
  function commonMarks(runs, from, to) {
    if (to <= from) return marksAt(runs, from);
    const part = slice(runs, from, to); if (!part.length) return {};
    const m = marksOf(part[0]);
    for (const r of part.slice(1)) for (const k of Object.keys(m)) if (m[k] !== (r[k] === undefined ? null : r[k])) delete m[k];
    return m;
  }

  /** at 에 조각들을 끼운다 */
  function insertRuns(runs, at, ins) { const [a, b] = split(runs, at); return normalize([...a, ...(ins || []), ...b]); }
  /** at 에 글을 끼운다 - marks 를 안 주면 그 자리의 서식을 잇는다 */
  function insertText(runs, at, s, marks) { return s ? insertRuns(runs, at, [mk(String(s), marks ? marksOf(marks) : marksAt(runs, at))]) : normalize(runs); }
  /** [from, to) 를 지운다 */
  function remove(runs, from, to) { if (to <= from) return normalize(runs); return join(slice(runs, 0, from), slice(runs, to)); }
  /** [from, to) 를 글로 바꾼다 - 서식은 지워지는 구간의 첫 글자 것을 잇는다(낱말을 골라 치면 그 서식으로) */
  function replaceText(runs, from, to, s, marks) {
    const m = marks ? marksOf(marks) : (to > from ? marksOf(slice(runs, from, from + 1)[0] || {}) : marksAt(runs, from));
    return insertRuns(remove(runs, from, to), from, s ? [mk(String(s), m)] : []);
  }

  /** [from, to) 에 서식을 건다 - value 가 꺼짐 값이면 벗긴다. 위·아래 첨자처럼 함께 켤 수 없는 짝은 다른 쪽을 끈다 */
  function setMark(runs, from, to, key, value) {
    if (!MARKS.includes(key) || to <= from) return normalize(runs);
    const on = !(value === undefined || value === null || value === false || value === "" || value === 0);
    const mid = slice(runs, from, to).map((r) => {
      const m = marksOf(r);
      if (on) { m[key] = BOOL.has(key) ? true : value; if (EXCL[key]) delete m[EXCL[key]]; } else delete m[key];
      return mk(r.t, m);
    });
    return normalize([...slice(runs, 0, from), ...mid, ...slice(runs, to)]);
  }
  /** 켜고 끄기 - 구간 전체가 이미 켜져 있으면 끄고, 하나라도 꺼져 있으면 전체를 켠다(Word 와 같다) */
  function toggleMark(runs, from, to, key, value) {
    if (to <= from) return normalize(runs);
    const want = value === undefined ? true : value;
    const all = slice(runs, from, to).every((r) => (BOOL.has(key) ? !!r[key] : r[key] === want));
    return setMark(runs, from, to, key, all ? null : want);
  }
  /** [from, to) 의 서식을 모두 벗긴다(서식 지우기) - keep 에 적은 키는 남긴다(예: 링크) */
  function clearMarks(runs, from, to, keep) {
    if (to <= from) return normalize(runs);
    const mid = slice(runs, from, to).map((r) => { const m = {}; for (const k of keep || []) if (r[k] !== undefined) m[k] = r[k]; return mk(r.t, m); });
    return normalize([...slice(runs, 0, from), ...mid, ...slice(runs, to)]);
  }

  // ---------------------------------------------------------------- 문단(블록) 단위
  /** 문단을 at 에서 둘로(Enter) - 뒤 문단은 newId 를 받고 문단 속성(정렬·스타일 등)을 물려받는다. 제목 끝에서 나누면 뒤는 본문 스타일(next) */
  function splitBlock(block, at, newId, next) {
    const [a, b] = split(block.runs || [], at);
    const tail = { ...block, id: newId, runs: b };
    if (next !== undefined && !b.length) { if (next === null) delete tail.style; else tail.style = next; }
    return [{ ...block, runs: a }, tail];
  }
  /** 두 문단을 하나로(문단 맨 앞에서 Backspace) - 앞 문단의 속성을 따르고, 이은 자리(앞 문단의 길이)를 함께 돌려준다 */
  function joinBlocks(a, b) { return { block: { ...a, runs: join(a.runs, b.runs) }, at: length(a.runs) }; }

  /** 글 → 조각 → 글 왕복용 - 줄바꿈으로 나눠 문단별 runs 목록으로(붙여넣기의 일반 글) */
  const plainToParagraphs = (s, marks) => String(s || "").replace(/\r\n?/g, "\n").split("\n").map((ln) => fromPlain(ln, marks));

  // ---------------------------------------------------------------- 블록 목록 단위(여러 문단에 걸친 선택) - 위치 = {id, off}
  //   글 블록 = runs 배열이 있는 블록. 그 밖(표·그림·쪽 나누기)은 통째로 다룬다(구간에 끼면 지워진다).
  const isText = (b) => !!b && Array.isArray(b.runs);
  const idx = (blocks, id) => blocks.findIndex((b) => b.id === id);
  /** 두 위치를 문서 순서로 - [앞, 뒤]. 모르는 id 면 null */
  function ordered(blocks, a, b) {
    const ia = idx(blocks, a.id), ib = idx(blocks, b.id);
    if (ia < 0 || ib < 0) return null;
    return ia < ib || (ia === ib && a.off <= b.off) ? [a, b] : [b, a];
  }
  const collapsed = (a, b) => a.id === b.id && a.off === b.off;
  /** 구간을 지운다 → {blocks, pos}. 여러 문단에 걸치면 첫 문단에 끝 문단의 나머지를 잇는다(첫 문단의 속성을 따른다) */
  function deleteRange(blocks, a, b) {
    const o = ordered(blocks, a, b); if (!o) return { blocks, pos: a };
    const [s, e] = o, is = idx(blocks, s.id), ie = idx(blocks, e.id), first = blocks[is], last = blocks[ie];
    if (is === ie) {
      if (!isText(first) || s.off === e.off) return { blocks, pos: s };
      return { blocks: blocks.map((x, k) => (k === is ? { ...x, runs: remove(x.runs, s.off, e.off) } : x)), pos: s };
    }
    const head = isText(first) ? slice(first.runs, 0, s.off) : [], tail = isText(last) ? slice(last.runs, e.off) : [];
    const keep = isText(first) ? first : last;  // 첫 블록이 글이 아니면(그림 등) 끝 문단이 남는다
    const merged = isText(keep) ? { ...keep, runs: join(head, tail) } : null;
    const out = [...blocks.slice(0, is), ...(merged ? [merged] : []), ...blocks.slice(ie + 1)];
    return { blocks: out, pos: merged ? { id: merged.id, off: length(head) } : s };
  }
  /** 위치에 글을 넣는다 → {blocks, pos} */
  function insertAt(blocks, pos, s, marks) {
    const i = idx(blocks, pos.id); if (i < 0 || !isText(blocks[i]) || !s) return { blocks, pos };
    return { blocks: blocks.map((x, k) => (k === i ? { ...x, runs: insertText(x.runs, pos.off, s, marks) } : x)), pos: { id: pos.id, off: pos.off + String(s).length } };
  }
  /** 위치에서 문단을 나눈다(Enter) → {blocks, pos: 새 문단의 맨 앞} */
  function splitAt(blocks, pos, newId, next) {
    const i = idx(blocks, pos.id); if (i < 0 || !isText(blocks[i])) return { blocks, pos };
    const [p1, p2] = splitBlock(blocks[i], pos.off, newId, next);
    return { blocks: [...blocks.slice(0, i), p1, p2, ...blocks.slice(i + 1)], pos: { id: newId, off: 0 } };
  }
  /** 문단 맨 앞에서 Backspace - 앞 글 문단과 잇는다. 앞이 글이 아니면(표·그림) 그 블록을 지운다. 할 것이 없으면 null */
  function joinBackward(blocks, pos) {
    const i = idx(blocks, pos.id); if (i <= 0 || pos.off !== 0 || !isText(blocks[i])) return null;
    const prev = blocks[i - 1];
    if (!isText(prev)) return { blocks: [...blocks.slice(0, i - 1), ...blocks.slice(i)], pos };
    const j = joinBlocks(prev, blocks[i]);
    return { blocks: [...blocks.slice(0, i - 1), j.block, ...blocks.slice(i + 1)], pos: { id: prev.id, off: j.at } };
  }
  /** 문단 끝에서 Delete - 뒤 문단을 끌어온다 */
  function joinForward(blocks, pos) {
    const i = idx(blocks, pos.id); if (i < 0 || i >= blocks.length - 1 || !isText(blocks[i]) || pos.off !== length(blocks[i].runs)) return null;
    const nxt = blocks[i + 1];
    if (!isText(nxt)) return { blocks: [...blocks.slice(0, i + 1), ...blocks.slice(i + 2)], pos };
    return { blocks: [...blocks.slice(0, i), joinBlocks(blocks[i], nxt).block, ...blocks.slice(i + 2)], pos };
  }
  /** 구간에 든 글 블록과 그 안의 범위 [{i, from, to}] */
  function spans(blocks, a, b) {
    const o = ordered(blocks, a, b); if (!o) return [];
    const [s, e] = o, is = idx(blocks, s.id), ie = idx(blocks, e.id), out = [];
    for (let k = is; k <= ie; k++) {
      if (!isText(blocks[k])) continue;
      const from = k === is ? s.off : 0, to = k === ie ? e.off : length(blocks[k].runs);
      if (to > from) out.push({ i: k, from, to });
    }
    return out;
  }
  /** 구간에 서식을 건다. toggle 이면 구간 전체가 이미 그 값일 때 벗긴다(여러 문단에 걸쳐도 한 번에 판단) */
  function markRange(blocks, a, b, key, value, toggle) {
    const sp = spans(blocks, a, b); if (!sp.length) return blocks;
    let v = value === undefined ? true : value;
    if (toggle) {
      const all = sp.every((x) => slice(blocks[x.i].runs, x.from, x.to).every((r) => (BOOL.has(key) ? !!r[key] : r[key] === v)));
      if (all) v = null;
    }
    const by = new Map(sp.map((x) => [x.i, x]));
    return blocks.map((x, k) => (by.has(k) ? { ...x, runs: setMark(x.runs, by.get(k).from, by.get(k).to, key, v) } : x));
  }
  /** 구간 전체에 공통인 서식 - 구간이 비면 그 자리에서 칠 때 붙을 서식 */
  function marksInRange(blocks, a, b) {
    const sp = spans(blocks, a, b);
    if (!sp.length) { const i = idx(blocks, a.id); return i >= 0 && isText(blocks[i]) ? marksAt(blocks[i].runs, a.off) : {}; }
    let m = null;
    for (const x of sp) { const c = commonMarks(blocks[x.i].runs, x.from, x.to); if (!m) m = c; else for (const k of Object.keys(m)) if (m[k] !== c[k]) delete m[k]; }
    return m || {};
  }
  /** 구간에 걸친 글 블록의 문단 속성을 바꾼다(정렬·스타일 등) - attrs 의 null 값은 그 키를 지운다 */
  function setBlockAttrs(blocks, a, b, attrs) {
    const o = ordered(blocks, a, b); if (!o) return blocks;
    const is = idx(blocks, o[0].id), ie = idx(blocks, o[1].id);
    return blocks.map((x, k) => {
      if (k < is || k > ie || !isText(x)) return x;
      const y = { ...x };
      for (const [key, v] of Object.entries(attrs)) { if (v === null || v === undefined) delete y[key]; else y[key] = v; }
      return y;
    });
  }
  /** 위치에 문단들을 넣는다(붙여넣기) - 첫 문단은 그 자리에 잇고, 가운데는 새 문단, 마지막은 뒤 글 앞에 잇는다. paras = [runs, …] */
  function insertParas(blocks, pos, paras, newId) {
    const i = idx(blocks, pos.id); if (i < 0 || !isText(blocks[i]) || !paras || !paras.length) return { blocks, pos };
    const cur = blocks[i], [head, tail] = split(cur.runs, pos.off);
    if (paras.length === 1) return { blocks: blocks.map((x, k) => (k === i ? { ...x, runs: join(join(head, paras[0]), tail) } : x)), pos: { id: cur.id, off: length(head) + length(paras[0]) } };
    const made = [{ ...cur, runs: join(head, paras[0]) }];
    for (let k = 1; k < paras.length; k++) made.push({ ...cur, id: newId(), runs: k === paras.length - 1 ? join(paras[k], tail) : normalize(paras[k]) });
    const lastB = made[made.length - 1];
    return { blocks: [...blocks.slice(0, i), ...made, ...blocks.slice(i + 1)], pos: { id: lastB.id, off: length(paras[paras.length - 1]) } };
  }

  // ---------------------------------------------------------------- 입력(DOM) - contenteditable 호스트에 붙인다(PG-031)
  //   mount(host, opts) → 편집기. **모델이 진실**이다: 입력(beforeinput)을 가로채 모델을 고치고 바뀐 블록만 다시 그린 뒤 선택을 되돌린다.
  //   한글 조합(IME) 중에는 브라우저가 DOM 을 고치게 두고 조합이 끝나면 그 문단의 글을 모델과 비교해(앞뒤 같은 부분을 빼고) 읽어 들인다.
  //   opts: get() → blocks · set(blocks, why) 저장(why = "type" | "delete" | "enter" | "format" | "paste" | "ime" - 실행 취소 묶음용)
  //         newId() · nextStyle(block) → 문단 끝에서 Enter 뒤의 스타일(없으면 물려받음) · renderBlock(block) → 글이 아닌 블록의 요소
  //         decorate(el, block) 문단 요소 꾸미기(스타일·정렬) · color(c) · font(f) 토큰 → CSS 값 · onSelect(state) · undo() · redo()
  function mount(host, opts) {
    const doc = host.ownerDocument, win = doc.defaultView;
    host.contentEditable = "true"; host.spellcheck = false; host.classList.add("nt-host");
    let drawn = new Map();   // id → {block, el} - 블록 객체가 그대로면 요소를 다시 만들지 않는다
    let pending = null;      // 선택이 비었을 때 켜 둔 서식(굵게를 누르고 치기) - 다음 입력에 쓰고, 다른 곳으로 가면 버린다
    let pendAt = null, composing = false, compId = null;
    const blocks = () => opts.get() || [];
    const esc = (s) => (win.CSS && win.CSS.escape ? win.CSS.escape(s) : String(s).replace(/"/g, '\\"'));

    function paint(span, r) {
      const st = span.style;
      if (r.b) st.fontWeight = "700";
      if (r.i) st.fontStyle = "italic";
      const deco = [r.u ? "underline" : "", r.s ? "line-through" : ""].filter(Boolean).join(" ");
      if (deco) st.textDecoration = deco;
      if (r.u && r.u !== true) st.textDecorationStyle = { double: "double", dot: "dotted", dash: "dashed", wave: "wavy" }[r.u] || "";
      if (r.c) st.color = opts.color ? opts.color(r.c) : r.c;
      if (r.hl) st.backgroundColor = opts.color ? opts.color(r.hl) : r.hl;
      if (r.sup || r.sub) { st.verticalAlign = r.sup ? "super" : "sub"; st.fontSize = "0.7em"; }
      if (r.font) st.fontFamily = opts.font ? opts.font(r.font) : r.font;
      if (r.size) st.fontSize = r.size + "pt";
      if (r.link) { span.dataset.link = r.link; span.classList.add("nt-link"); }
      if (r.ruby) span.dataset.ruby = r.ruby;
    }
    function fill(el, runs) {
      el.replaceChildren();
      for (const r of runs || []) { const sp = doc.createElement("span"); sp.textContent = r.t; paint(sp, r); el.appendChild(sp); }
      // 빈 문단, 또는 줄바꿈으로 끝나는 문단은 마지막 줄이 높이를 갖게 <br> 을 둔다(글 길이에는 세지 않는다)
      if (!runs || !runs.length || /\n$/.test(runs[runs.length - 1].t)) el.appendChild(doc.createElement("br"));
    }
    function blockEl(b) {
      let el;
      if (isText(b)) { el = doc.createElement("div"); el.className = "nt-p"; fill(el, b.runs); if (opts.decorate) opts.decorate(el, b); }
      else { el = (opts.renderBlock && opts.renderBlock(b)) || doc.createElement("div"); el.classList.add("nt-obj"); el.contentEditable = "false"; }
      el.dataset.id = b.id;
      return el;
    }
    /** 모델대로 그린다 - 객체가 바뀐 블록만 새로 만든다. force = 그 id 는 무조건 다시(조합 뒤 DOM 이 어긋났을 때) */
    function render(force) {
      const next = new Map(), els = [];
      for (const b of blocks()) {
        const old = drawn.get(b.id);
        const el = old && old.block === b && b.id !== force && old.el.isConnected ? old.el : blockEl(b);
        next.set(b.id, { block: b, el }); els.push(el);
      }
      drawn = next;
      let same = host.childNodes.length === els.length;
      for (let k = 0; same && k < els.length; k++) same = host.childNodes[k] === els[k];
      if (!same) host.replaceChildren(...els);
    }
    const elOf = (id) => (drawn.get(id) || {}).el || host.querySelector(`[data-id="${esc(id)}"]`);

    /** DOM 위치 → 모델 위치 */
    function pointFrom(node, offset) {
      if (!node || !host.contains(node)) return null;
      if (node === host) {  // 호스트 자체가 선택 기준(블록 사이) - 그 자리 블록의 맨 앞 또는 앞 블록의 끝
        const kids = host.children; if (!kids.length) return null;
        if (offset < kids.length) return { id: kids[offset].dataset.id, off: 0 };
        const last = kids[kids.length - 1], lb = (drawn.get(last.dataset.id) || {}).block;
        return { id: last.dataset.id, off: isText(lb) ? length(lb.runs) : 0 };
      }
      let el = node.nodeType === 1 ? node : node.parentElement;
      while (el && el.parentElement !== host) el = el.parentElement;
      if (!el || !el.dataset.id) return null;
      const b = (drawn.get(el.dataset.id) || {}).block;
      if (!isText(b)) return { id: el.dataset.id, off: 0 };
      const r = doc.createRange(); r.selectNodeContents(el);
      try { r.setEnd(node, offset); } catch (e) { return { id: b.id, off: 0 }; }
      return { id: b.id, off: Math.min(r.toString().length, length(b.runs)) };  // <br> 은 글이 아니라 세지 않는다
    }
    /** 모델 위치 → DOM 위치 [node, offset] */
    function domPoint(pos) {
      const el = elOf(pos.id); if (!el) return null;
      const w = doc.createTreeWalker(el, 4 /* SHOW_TEXT */); let left = pos.off, n, last = null;
      while ((n = w.nextNode())) { if (left <= n.data.length) return [n, left]; left -= n.data.length; last = n; }
      return last ? [last, last.data.length] : [el, 0];
    }
    function selection() {
      const s = doc.getSelection(); if (!s || !s.rangeCount || !host.contains(s.anchorNode)) return null;
      const a = pointFrom(s.anchorNode, s.anchorOffset), f = pointFrom(s.focusNode, s.focusOffset);
      return a && f ? { a, f } : null;
    }
    function select(a, f) {
      const pa = domPoint(a), pf = domPoint(f || a); if (!pa || !pf) return;
      const s = doc.getSelection();
      if (s.setBaseAndExtent) s.setBaseAndExtent(pa[0], pa[1], pf[0], pf[1]);
      else { const r = doc.createRange(); r.setStart(pa[0], pa[1]); r.collapse(true); s.removeAllRanges(); s.addRange(r); }
    }
    function commit(bs, pos, why, force) { opts.set(bs, why); render(force); if (pos) select(pos); notify(); }
    const state = () => { const s = selection(); return { sel: s, marks: s ? { ...marksInRange(blocks(), s.a, s.f), ...(pending && collapsed(s.a, s.f) ? pending : {}) } : {} }; };
    function notify() { if (opts.onSelect) opts.onSelect(state()); }
    function usePending(pos) { const m = pending && pendAt && collapsed(pendAt, pos) ? cleanPending(pos) : undefined; pending = pendAt = null; return m; }
    function cleanPending(pos) {  // 그 자리의 서식에 켜 둔 것을 얹는다(false 는 끔)
      const i = idx(blocks(), pos.id), base = i >= 0 && isText(blocks()[i]) ? marksAt(blocks()[i].runs, pos.off) : {};
      const m = { ...base, ...pending }; for (const k of Object.keys(m)) if (m[k] === false) delete m[k];
      return m;
    }

    /** 선택 구간을 지우고 그 자리에 무언가를 한다 - fn(blocks, pos) → {blocks, pos} */
    function replaceSel(fn, why, range) {
      const s = range || selection(); if (!s) return;
      let r = collapsed(s.a, s.f) ? { blocks: blocks(), pos: s.a } : deleteRange(blocks(), s.a, s.f);
      if (fn) r = fn(r.blocks, r.pos);
      commit(r.blocks, r.pos, why);
    }
    function typeText(s, range) {
      // 고른 글 위에 치면 그 글의 첫 글자 서식을 잇는다(굵은 낱말을 골라 치면 굵게) - 지운 뒤의 자리 서식(앞 글자)이 아니라
      const cur = range || selection(); let first;
      if (cur && !collapsed(cur.a, cur.f)) {
        const o = ordered(blocks(), cur.a, cur.f), b = o && blocks()[idx(blocks(), o[0].id)];
        const r = isText(b) ? slice(b.runs, o[0].off, o[0].off + 1)[0] : null;
        if (r) { first = marksOf(r); delete first.link; delete first.ruby; }
      }
      replaceSel((bs, pos) => { const m = usePending(pos) || first; return insertAt(bs, pos, s, m); }, "type", range);
    }
    function del(forward, e) {
      const s = selection(); if (!s) return;
      if (!collapsed(s.a, s.f)) return replaceSel(null, "delete");
      // 지울 범위는 브라우저가 계산한 것을 쓴다(낱말 단위 · 이모지·조합 문자 한 덩어리) - 없으면 한 코드 단위
      const tr = e && e.getTargetRanges ? e.getTargetRanges()[0] : null;
      if (tr) {
        const a = pointFrom(tr.startContainer, tr.startOffset), b = pointFrom(tr.endContainer, tr.endOffset);
        if (a && b && !collapsed(a, b)) return replaceSel(null, "delete", { a, f: b });
      }
      const j = forward ? joinForward(blocks(), s.a) : joinBackward(blocks(), s.a);
      if (j) return commit(j.blocks, j.pos, "delete");
      const i = idx(blocks(), s.a.id), b = blocks()[i]; if (!isText(b)) return;
      const from = forward ? s.a.off : s.a.off - 1; if (from < 0 || from >= length(b.runs)) return;
      replaceSel(null, "delete", { a: { id: b.id, off: from }, f: { id: b.id, off: from + 1 } });
    }
    function enter() {
      replaceSel((bs, pos) => {
        const i = idx(bs, pos.id), b = bs[i];
        const atEnd = isText(b) && pos.off === length(b.runs);
        return splitAt(bs, pos, opts.newId(), atEnd && opts.nextStyle ? opts.nextStyle(b) : undefined);
      }, "enter");
    }
    function paste(dt) {
      const plain = dt ? dt.getData("text/plain") : ""; if (!plain) return;
      replaceSel((bs, pos) => insertParas(bs, pos, plainToParagraphs(plain, usePending(pos) || marksInRange(bs, pos, pos)), opts.newId), "paste");
    }
    /** 서식 켜고 끄기 - 선택이 비었으면 다음 입력에 쓸 서식으로 켜 둔다 */
    function toggle(key, value) {
      const s = selection(); if (!s) return;
      const v = value === undefined ? true : value;
      if (collapsed(s.a, s.f)) {
        const cur = { ...marksInRange(blocks(), s.a, s.f), ...(pending && pendAt && collapsed(pendAt, s.a) ? pending : {}) };
        pending = { ...(pendAt && collapsed(pendAt, s.a) ? pending : {}), [key]: (BOOL.has(key) ? !!cur[key] : cur[key] === v) ? false : v };
        pendAt = s.a; return notify();
      }
      const [a, f] = [s.a, s.f];
      opts.set(markRange(blocks(), a, f, key, v, true), "format"); render(); select(a, f); notify();
    }
    /** 서식 값을 정한다(색·크기·글꼴처럼 켜고 끄기가 아닌 것) - null 이면 벗긴다 */
    function setMarkSel(key, value) {
      const s = selection(); if (!s) return;
      if (collapsed(s.a, s.f)) { pending = { ...(pendAt && collapsed(pendAt, s.a) ? pending : {}), [key]: value === null || value === undefined ? false : value }; pendAt = s.a; return notify(); }
      opts.set(markRange(blocks(), s.a, s.f, key, value === undefined ? null : value, false), "format"); render(); select(s.a, s.f); notify();
    }
    function blockAttrs(attrs) {
      const s = selection(); if (!s) return;
      opts.set(setBlockAttrs(blocks(), s.a, s.f, attrs), "format"); render(); select(s.a, s.f); notify();
    }
    /** DOM 이 모델과 어긋났을 때(조합 입력 · 맞춤법 교정 · 끌어 놓기) 그 문단의 글을 읽어 들인다 - 앞뒤 같은 부분을 빼고 가운데만 바꾼다 */
    function syncBlock(id, why) {
      const el = elOf(id), i = idx(blocks(), id), b = blocks()[i]; if (!el || !isText(b)) return;
      const now = el.textContent, old = text(b.runs);
      const s = selection(), caret = s && s.f.id === id ? null : s && s.f;  // 같은 문단이면 아래에서 DOM 기준으로 다시 잰다
      let off = null;
      if (s && s.f.id === id) { const ds = doc.getSelection(), r = doc.createRange(); r.selectNodeContents(el); try { r.setEnd(ds.focusNode, ds.focusOffset); off = r.toString().length; } catch (e) { off = now.length; } }
      if (now === old) { render(id); if (off !== null) select({ id, off }); return; }
      let p = 0; while (p < now.length && p < old.length && now[p] === old[p]) p++;
      let q = 0; while (q < now.length - p && q < old.length - p && now[now.length - 1 - q] === old[old.length - 1 - q]) q++;
      const m = usePending({ id, off: p });
      const runs = replaceText(b.runs, p, old.length - q, now.slice(p, now.length - q), m);
      commit(blocks().map((x, k) => (k === i ? { ...x, runs } : x)), off !== null ? { id, off: Math.min(off, now.length) } : caret, why || "ime", id);
    }

    const FMT = { formatBold: "b", formatItalic: "i", formatUnderline: "u", formatStrikeThrough: "s", formatSuperscript: "sup", formatSubscript: "sub" };
    function onBeforeInput(e) {
      const t = e.inputType || "";
      if (composing || e.isComposing || t === "insertCompositionText" || t === "deleteCompositionText") return;  // 조합 중 - 브라우저에 맡긴다
      e.preventDefault();
      if (t === "insertText" || t === "insertReplacementText") typeText(e.data != null ? e.data : (e.dataTransfer ? e.dataTransfer.getData("text/plain") : ""));
      else if (t === "insertParagraph") enter();
      else if (t === "insertLineBreak") typeText("\n");
      else if (t === "insertFromPaste" || t === "insertFromDrop" || t === "insertFromYank") paste(e.dataTransfer);
      else if (t.startsWith("delete")) del(/Forward/.test(t), e);
      else if (FMT[t]) toggle(FMT[t]);
      else if (t === "historyUndo") { if (opts.undo) opts.undo(); }
      else if (t === "historyRedo") { if (opts.redo) opts.redo(); }
      // 그 밖(insertOrderedList 등)은 막기만 한다 - 목록·표는 문단 속성으로 다룬다
    }
    function onCompStart() {
      const s = selection();
      if (s && !collapsed(s.a, s.f)) replaceSel(null, "delete");  // 고른 글 위에서 조합을 시작하면 먼저 모델에서 지운다(DOM 이 여러 문단을 합치기 전에)
      const s2 = selection(); compId = s2 ? s2.f.id : null; composing = true;
    }
    function onCompEnd() { composing = false; const id = compId; compId = null; if (id) syncBlock(id, "ime"); }
    function onInput(e) {  // 우리가 막지 못한 DOM 변경(조합은 compositionend 가 처리) - 선택이 있는 문단을 읽어 들인다
      if (composing || (e && e.isComposing)) return;
      const s = selection(); if (s) syncBlock(s.f.id, "type");
    }
    function onKeyDown(e) {
      if (composing || e.isComposing) return;
      const mod = e.ctrlKey || e.metaKey; if (!mod || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === "b" || k === "i" || k === "u") { e.preventDefault(); toggle(k); }
      else if (k === "z") { e.preventDefault(); if (e.shiftKey) { if (opts.redo) opts.redo(); } else if (opts.undo) opts.undo(); }
      else if (k === "y") { e.preventDefault(); if (opts.redo) opts.redo(); }
    }
    function onSelChange() {
      if (composing) return;
      const s = selection(); if (!s) return;
      if (pending && !(pendAt && collapsed(s.a, s.f) && collapsed(pendAt, s.a))) pending = pendAt = null;
      notify();
    }
    host.addEventListener("beforeinput", onBeforeInput);
    host.addEventListener("compositionstart", onCompStart);
    host.addEventListener("compositionend", onCompEnd);
    host.addEventListener("input", onInput);
    host.addEventListener("keydown", onKeyDown);
    doc.addEventListener("selectionchange", onSelChange);
    render();
    return {
      render, selection, select, state, toggle, setMark: setMarkSel, blockAttrs, typeText, enter, syncBlock,
      focus() { host.focus(); },
      /** 밖에서 문서를 바꾼 뒤(실행 취소 · 남의 변경) - 다시 그리고 선택을 되돌린다 */
      refresh(sel) { render(); if (sel) select(sel.a, sel.f); notify(); },
      destroy() {
        host.removeEventListener("beforeinput", onBeforeInput); host.removeEventListener("compositionstart", onCompStart);
        host.removeEventListener("compositionend", onCompEnd); host.removeEventListener("input", onInput);
        host.removeEventListener("keydown", onKeyDown); doc.removeEventListener("selectionchange", onSelChange);
      },
    };
  }

  root.NexaText = { MARKS, marksOf, sameMarks, normalize, length, text, fromPlain, slice, split, join, marksAt, commonMarks,
    insertRuns, insertText, remove, replaceText, setMark, toggleMark, clearMarks, splitBlock, joinBlocks, plainToParagraphs,
    isText, ordered, deleteRange, insertAt, splitAt, joinBackward, joinForward, spans, markRange, marksInRange, setBlockAttrs, insertParas, mount };
})(typeof window !== "undefined" ? window : globalThis);
