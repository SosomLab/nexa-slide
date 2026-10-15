/* nexa-slide 공용 찾기(NexaSearch) - 편집기 요청 기록·서버 작업 목록이 같이 쓴다.
     기본은 퍼지: 질의를 공백으로 나눈 낱말마다, 부분 일치가 없으면 글자가 순서대로 나오되 글자 사이 틈이 2자 이하면 맞는 것으로(띄어쓰기·한두 글자 차이 허용).
     토글(일반 편집기의 찾기와 같음): Aa 대소문자 구분 · ab 단어 단위 · .* 정규식 - 단어 단위나 정규식을 켜면 퍼지 대신 그 규칙으로 찾는다.
       NexaSearch.matcher(q, {caseSens, word, regex}) → { empty, test(str), any([str…]), hl(str) (일치 부분 <mark>), error(정규식 오류) }
       NexaSearch.toggles(host, key, onChange)        → host 안에 토글 3개(상태는 localStorage nexa-search-<key>), 돌려주는 함수로 지금 옵션을 읽는다 */
(function () {
  const LSK = (k) => "nexa-search-" + k;
  const load = (key) => { try { return JSON.parse(localStorage.getItem(LSK(key)) || "{}") || {}; } catch (e) { return {}; } };
  const save = (key, o) => { try { localStorage.setItem(LSK(key), JSON.stringify(o)); } catch (e) { /* 저장 못 해도 동작 */ } };
  const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const escH = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const GAP = 2;  // 퍼지에서 맞은 글자 사이에 건너뛸 수 있는 글자 수

  function fuzzyFind(text, word) {  // → [[시작, 끝]…] 또는 null
    const i = text.indexOf(word);
    if (i >= 0) return [[i, i + word.length]];
    if (word.length < 2) return null;
    for (let s = text.indexOf(word[0]); s >= 0; s = text.indexOf(word[0], s + 1)) {
      const pos = [s]; let p = s, ok = true;
      for (let k = 1; k < word.length; k++) {
        let j = -1;
        for (let g = 1; g <= GAP + 1; g++) if (text[p + g] === word[k]) { j = p + g; break; }
        if (j < 0) { ok = false; break; }
        pos.push(j); p = j;
      }
      if (ok) return pos.map((x) => [x, x + 1]);
    }
    return null;
  }

  function matcher(q, o) {
    o = o || {}; q = String(q || "").trim();
    if (!q) return { empty: true, test: () => true, any: () => true, hl: (s) => escH(s), error: null };
    const cs = !!o.caseSens;
    let re = null, error = null;
    if (o.regex || o.word) {
      let src = o.regex ? q : escRe(q);
      if (o.word) src = `(?<![\\p{L}\\p{N}_])(?:${src})(?![\\p{L}\\p{N}_])`;
      try { re = new RegExp(src, cs ? "gu" : "giu"); } catch (e) { error = e.message; re = null; }
    }
    const words = q.split(/\s+/).filter(Boolean).map((w) => (cs ? w : w.toLowerCase()));
    function spans(str) {
      const s = String(str ?? ""); if (!s) return null;
      if (error) return null;
      if (re) {
        const out = []; re.lastIndex = 0; let m;
        while ((m = re.exec(s))) { if (!m[0]) { re.lastIndex++; continue; } out.push([m.index, m.index + m[0].length]); if (out.length > 300) break; }
        return out.length ? out : null;
      }
      const t = cs ? s : s.toLowerCase(), out = [];
      for (const w of words) { const f = fuzzyFind(t, w); if (!f) return null; out.push(...f); }
      return out;
    }
    const test = (str) => !!spans(str);
    const any = (vals) => test(vals.filter((v) => v != null && v !== "").map(String).join("\n"));  // 낱말이 여러 칸에 나뉘어 있어도 맞는다
    const hl = (str) => {
      const s = String(str ?? ""), sp = spans(s); if (!sp) return escH(s);
      sp.sort((a, b) => a[0] - b[0]);
      let out = "", p = 0;
      for (const [a, b] of sp) { if (a < p) continue; out += escH(s.slice(p, a)) + "<mark>" + escH(s.slice(a, b)) + "</mark>"; p = b; }
      return out + escH(s.slice(p));
    };
    return { empty: false, test, any, hl, error, re };
  }

  const TG = [["caseSens", "Aa", "대소문자 구분"], ["word", "ab", "단어 단위"], ["regex", ".*", "정규식"]];
  let cssDone = false;
  function toggles(host, key, onChange) {
    if (!cssDone) {
      cssDone = true;
      const st = document.createElement("style");
      st.textContent = ".ns-tg{display:inline-flex;gap:2px;align-items:center}.ns-tg button{border:0;background:transparent;border-radius:6px;padding:2px 6px;font:12px/1.4 Consolas,monospace;color:var(--ink2,#555);cursor:pointer;min-width:26px}.ns-tg button:hover{background:rgba(0,0,0,.06)}.ns-tg button.on{background:var(--p,#A91F24);color:#fff}.ns-tg button[data-k=word]{text-decoration:underline;text-underline-offset:2px}";
      document.head.appendChild(st);
    }
    const o = load(key);
    host.classList.add("ns-tg");
    host.innerHTML = TG.map(([k, l, t]) => `<button type="button" data-k="${k}" class="${o[k] ? "on" : ""}" title="${t}" aria-label="${t}" aria-pressed="${!!o[k]}">${l}</button>`).join("");
    host.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-k]"); if (!b) return;
      const k = b.dataset.k; o[k] = !o[k];
      b.classList.toggle("on", o[k]); b.setAttribute("aria-pressed", String(!!o[k]));
      save(key, o); if (onChange) onChange({ ...o });
    });
    return () => ({ ...o });
  }
  /** 질의에서 번호 지정(#4 · #4-6 · #4,5,7-10, 여러 토큰 가능)을 떼어 낸다 → { nums: Set(번호), text: 나머지 낱말 }. 번호의 뜻(슬라이드·요청 id)은 쓰는 쪽이 정한다 */
  function split(q) {
    const nums = new Set(), words = [];
    for (const w of String(q || "").split(/\s+/).filter(Boolean)) {
      if (/^#\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*,?$/.test(w)) {
        for (const part of w.slice(1).split(",").filter(Boolean)) {
          const [a, b] = part.split("-").map(Number), lo = Math.min(a, b ?? a), hi = Math.max(a, b ?? a);
          for (let i = lo; i <= Math.min(hi, lo + 999); i++) nums.add(i);
        }
      } else words.push(w);
    }
    return { nums, text: words.join(" ") };
  }
  window.NexaSearch = { matcher, toggles, split, options: load };
})();
