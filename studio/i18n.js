/* nexa-slide 표시 언어(i18n) 엔진 - 사전 기반 런타임 번역. 사전·패턴은 studio/i18n/<lang>.js(글만 있는 파일)에 있고 이 파일보다 먼저 읽힌다. 한국어 원문이 키, 사전에 없으면 한국어 그대로.
   화면 파일을 t() 로 감싸지 않고 DOM 의 글(텍스트 노드·placeholder·title·aria-label·option)을 사전으로 바꾼다.
   MutationObserver 가 뒤에 생기는 글도 바꾸므로 동적 화면(innerHTML)도 즉시 반영되고, 언어를 바꾸면 원문으로 되돌린 뒤 다시 적용한다.
     I18N.lang()              "system" | "ko" | "en"   (저장: localStorage nexa-lang, 주소 ?lang= 도 받음)
     I18N.effective()         실제 적용 언어 "ko" | "en" - system 이면 브라우저 언어(navigator.language)
     I18N.set(lang)           바꾸고 즉시 반영 · I18N.t(str) 글 하나 번역(토스트·확인 창용) · I18N.options() 선택 목록
   변수가 든 문구는 PATTERNS(정규식)과 " · " 구분 조각 번역으로 처리한다. 긴 안내문은 사전에 있는 것만 바뀐다. */
(function () {
  const KEY = "nexa-lang";
  // 언어 파일(studio/i18n/<lang>.js)이 먼저 읽혀 window.NEXA_LOCALES[lang] = { name, dict, patterns } 를 채운다. 사전·패턴은 거기에만 있다 - docs/dev/i18n.md
  const LOC = () => window.NEXA_LOCALES || {};
  const dictOf = (lang) => (LOC()[lang] && LOC()[lang].dict) || {};
  const patternsOf = (lang) => (LOC()[lang] && LOC()[lang].patterns) || [];
  const langs = () => ["ko", ...Object.keys(LOC()).filter((k) => k !== "ko")];
  // 변수가 든 문구 - [정규식, 바꿀 글]. $1… 로 잡은 값을 넣는다

  let cur = "system";
  try { cur = localStorage.getItem(KEY) || "system"; } catch (e) { /* 저장소 없음 */ }
  const q = new URLSearchParams(location.search).get("lang");
  if (q && (q === "system" || langs().includes(q))) { cur = q; try { localStorage.setItem(KEY, q); } catch (e) { /* 무시 */ } }

  const sysLang = () => ((navigator.language || "ko").toLowerCase().startsWith("ko") ? "ko" : "en");
  const effective = () => (cur === "system" ? sysLang() : cur);

  function tr1(s) {  // 글 하나(앞뒤 공백 보존)
    const lang = effective();
    if (lang === "ko" || !s) return s;
    const EN = dictOf(lang), PATTERNS = patternsOf(lang);
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s), core = m[2];
    if (!core || !/[가-힣]/.test(core)) return s;
    let out = EN[core];
    if (out === undefined && core.includes(" · ")) {  // 조각마다(정확 일치·패턴) - 조각이 하나라도 바뀌면 그 결과
      const src = core.split(" · "), parts = src.map((p) => tr1(p)); if (parts.some((p, i) => p !== src[i])) out = parts.join(" · ");
    }
    if (out === undefined) for (const [re, rep] of PATTERNS) { if (re.test(core)) { out = core.replace(re, rep); break; } }
    if (out === undefined && core.endsWith(":")) { const b = EN[core.slice(0, -1)]; if (b) out = b + ":"; }
    return out === undefined ? s : m[1] + out + m[3];
  }
  const t = (s) => tr1(String(s == null ? "" : s));
  /** 데이터 라벨 - 객체의 i18n[언어][키]가 있으면 그것, 없으면 원문을 사전으로(템플릿·시작용 내용·슬라이드 유형의 label·description 등). docs/dev/i18n.md 2절 */
  const pick = (obj, key) => { if (!obj) return ""; const l = effective(), v = obj.i18n && obj.i18n[l] && obj.i18n[l][key]; return v != null ? String(v) : t(obj[key]); };

  // ---------- DOM 적용 - 원문은 노드별로 기억해 두고 언어가 바뀌면 원문에서 다시 번역
  const ORIG = new WeakMap();
  const ATTRS = ["placeholder", "title", "aria-label"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "KBD"]);
  function applyText(node) {
    if (!ORIG.has(node)) ORIG.set(node, node.nodeValue);
    const o = ORIG.get(node), v = tr1(o);
    if (node.nodeValue !== v) node.nodeValue = v;
  }
  function applyEl(el) {
    for (const a of ATTRS) {
      if (!el.hasAttribute(a)) continue;
      const key = "__i18n_" + a;
      if (!(key in el)) el[key] = el.getAttribute(a);
      const v = tr1(el[key]);
      if (el.getAttribute(a) !== v) el.setAttribute(a, v);
    }
    if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit") && el.value) {
      if (!("__i18n_value" in el)) el.__i18n_value = el.value;
      el.value = tr1(el.__i18n_value);
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (root.parentNode && !SKIP.has(root.parentNode.tagName)) applyText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    if (root.nodeType === 1) { if (SKIP.has(root.tagName) && root.tagName !== "TEXTAREA") return; applyEl(root); if (root.tagName === "TEXTAREA") return; }
    for (const c of root.childNodes) walk(c);
  }
  let applying = false;
  function applyAll() {
    applying = true;
    try { walk(document.body); document.documentElement.lang = effective(); if (document.title) { const pre = (/^\(\d+\) /.exec(document.title) || [""])[0]; if (!document.__i18n_title) document.__i18n_title = document.title.slice(pre.length); document.title = pre + tr1(document.__i18n_title); } }
    finally { applying = false; }
  }
  // 변경 기록은 비동기로 오므로 "우리가 바꾼 것"은 값이 번역 결과와 같은지로 가려낸다(원문을 영어로 덮어쓰지 않게)
  const mo = new MutationObserver((recs) => {
    applying = true;
    try {
      for (const r of recs) {
        if (r.type === "characterData") {
          const n = r.target, o = ORIG.get(n);
          if (o !== undefined && n.nodeValue === tr1(o)) continue;
          ORIG.delete(n); if (n.parentNode && !SKIP.has(n.parentNode.tagName)) applyText(n);
        } else if (r.type === "attributes") {
          const el = r.target, key = "__i18n_" + r.attributeName;
          if (key in el && el.getAttribute(r.attributeName) === tr1(el[key])) continue;
          delete el[key]; applyEl(el);
        } else for (const n of r.addedNodes) walk(n);
      }
    } finally { applying = false; }
  });
  function start() {
    applyAll();
    mo.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);

  // confirm·prompt·alert 글도 번역(화면 코드는 그대로)
  const _confirm = window.confirm.bind(window), _prompt = window.prompt.bind(window), _alert = window.alert.bind(window);
  window.confirm = (m) => _confirm(t(m));
  window.prompt = (m, d) => _prompt(t(m), d);
  window.alert = (m) => _alert(t(m));

  function set(lang) {
    if (!(lang === "system" || langs().includes(lang))) return;
    cur = lang;
    try { localStorage.setItem(KEY, lang); } catch (e) { /* 무시 */ }
    applyAll();
    document.dispatchEvent(new CustomEvent("nexa-lang", { detail: { lang, effective: effective() } }));
  }
  const nameOf = (k) => (k === "ko" ? "한국어" : (LOC()[k] && LOC()[k].name) || k);
  const options = () => [{ value: "system", label: `System (${nameOf(sysLang())})` }, ...langs().filter((k) => k !== "ko").map((k) => ({ value: k, label: nameOf(k) })), { value: "ko", label: "한국어" }];
  window.I18N = { t, pick, set, lang: () => cur, effective, options, apply: applyAll, langs, get dict() { return dictOf(effective() === "ko" ? "en" : effective()); } };
})();
