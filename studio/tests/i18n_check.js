// i18n 검사 - 언어 파일(studio/i18n/*.js) 문법 + 사전 중복 키 + 엔진(i18n.js) 로드 + 대표 문구 번역. 실패하면 종료 코드 1. (docs/dev/i18n.md)
const fs = require("fs"), vm = require("vm"), path = require("path");
const STUDIO = path.join(__dirname, "..");
const files = fs.readdirSync(path.join(STUDIO, "i18n")).filter((f) => f.endsWith(".js")).sort().map((f) => path.join(STUDIO, "i18n", f));
let bad = 0;
for (const f of [...files, path.join(STUDIO, "i18n.js")]) new vm.Script(fs.readFileSync(f, "utf8"), { filename: f });
console.log("syntax ok", files.map((f) => path.basename(f)).join(" "));
const w = { addEventListener() {}, location: { search: "?lang=en" }, navigator: { language: "ko" }, localStorage: { getItem: () => null, setItem() {} },
  document: { body: null, addEventListener() {}, documentElement: {} }, confirm() {}, prompt() {}, alert() {}, MutationObserver: class { observe() {} }, CustomEvent: class {}, WeakMap, URLSearchParams };
w.window = w; vm.createContext(w);
for (const f of files) vm.runInContext(fs.readFileSync(f, "utf8"), w);
vm.runInContext(fs.readFileSync(path.join(STUDIO, "i18n.js"), "utf8"), w);
for (const [lang, loc] of Object.entries(w.NEXA_LOCALES)) console.log("lang", lang, "keys", Object.keys(loc.dict).length, "patterns", loc.patterns.length);
// 중복 키 - 모든 언어 파일의 "키": "값" 리터럴을 세어 둘 이상이면 중복(한 파일 안이든 파일 사이든)
const cnt = new Map();
for (const f of files) for (const m of fs.readFileSync(f, "utf8").matchAll(/"((?:[^"\\]|\\.)*)": "(?:[^"\\]|\\.)*"/g)) cnt.set(m[1], (cnt.get(m[1]) || 0) + 1);
const dups = [...cnt].filter(([, n]) => n > 1).map(([k]) => k);
console.log("dups", dups);
if (dups.length) bad = 1;
for (const s of ["세션 없음 · 마지막 · claude haiku · 10/14 17:41 · 사용자 중지", "슬라이드 3 전체에 대한 요청 - 예: 이 표를 두 장으로 나눠 줘 (Enter = 남기기, Shift+Enter = 줄바꿈)", "슬라이드 1 · s01 · 레이아웃 cover",
  "덱 전체 ERROR 0 · WARNING 0 · 템플릿 lecture · 최소 default 11pt", "archive · lecture 바탕", "board-decision · 템플릿 brief", "요청 3개 보내기", "변경1", "템플릿: 강의 교재 — Material v2", "Claude Code: 설치됨 · 로그인됨 2.1.300 · Codex CLI: 미설치 (미확인)"]) {
  const v = w.I18N.t(s); console.log(" ", s, "→", v); if (v === s) bad = 1;
}
if (w.I18N.options().length < 3) bad = 1;
process.exit(bad);
