// i18n.js 문법 + 사전 중복 키 검사 + 번역 몇 개
const fs = require("fs"), vm = require("vm");
const f = require("path").join(__dirname, "..", "i18n.js");
new vm.Script(fs.readFileSync(f, "utf8"), { filename: require("path").join(__dirname, "..", "i18n.js") }); console.log("syntax ok");
const w = { addEventListener() {}, location: { search: "?lang=en" }, navigator: { language: "ko" }, localStorage: { getItem: () => null, setItem() {} },
  document: { body: null, addEventListener() {}, documentElement: {} }, confirm() {}, prompt() {}, alert() {}, MutationObserver: class { observe() {} }, CustomEvent: class {}, WeakMap, URLSearchParams };
w.window = w; vm.createContext(w); vm.runInContext(fs.readFileSync(f, "utf8"), w);
const keys = Object.keys(w.I18N.dict); console.log("keys", keys.length);
const src = fs.readFileSync(f, "utf8"); const m = src.match(/const EN = \{([\s\S]*?)\n  \};/);
const all = [...m[1].matchAll(/"((?:[^"\\]|\\.)*)": "/g)].map((x) => x[1]); const seen = new Set(), dup = [];
for (const k of all) { if (seen.has(k)) dup.push(k); seen.add(k); } console.log("dups", dup);
for (const s of ["세션 없음 · 마지막 · claude haiku · 10/14 17:41 · 사용자 중지", "슬라이드 3 전체에 대한 요청 - 예: 이 표를 두 장으로 나눠 줘 (Enter = 남기기, Shift+Enter = 줄바꿈)", "Slide 1 · s01 · 레이아웃 cover", "덱 전체 ERROR 0 · WARNING 0 · 템플릿 lecture · 최소 default 11pt", "archive · lecture 바탕", "board-decision · 템플릿 brief", "요청 3개 보내기"]) console.log(" ", s, "→", w.I18N.t(s));
