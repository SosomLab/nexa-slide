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

  root.NexaText = { MARKS, marksOf, sameMarks, normalize, length, text, fromPlain, slice, split, join, marksAt, commonMarks,
    insertRuns, insertText, remove, replaceText, setMark, toggleMark, clearMarks, splitBlock, joinBlocks, plainToParagraphs };
})(typeof window !== "undefined" ? window : globalThis);
