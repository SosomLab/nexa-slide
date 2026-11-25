// page-render.js 의 규칙(스타일 풀기 · 목록 머리 기호 · 쪽 상자 · 문단 CSS)이 서버 page_doc.py 와 같은지 - node studio/tests/page_render_check.js
//   page_doc.py 로 같은 입력을 풀게 한 뒤(파이썬을 자식으로 실행) 결과를 비교한다. DOM 은 쓰지 않는다(그리기는 화면 시험이 본다).
const { spawnSync } = require("child_process");
const path = require("path");
require("../nexa-text.js"); require("../page-render.js");
const P = globalThis.NexaPage;
let fails = 0, n = 0;
const J = JSON.stringify;
function eq(name, got, want) { n++; if (J(got) !== J(want)) { fails++; console.log(`FAIL ${name}\n     기대 ${J(want)}\n     실제 ${J(got)}`); } }

const L = (id, kind, level = 0, extra = {}) => ({ id, type: "p", list: { kind, level, ...extra }, runs: [] });
const blocks = [L("a", "number"), L("b", "number"), L("c", "number", 1), L("d", "number", 1), L("e", "number", 2), L("f", "number"), L("g", "number", 1),
  { id: "x", type: "p", runs: [] }, L("h", "number"), L("i", "bullet"), L("j", "bullet", 1), L("k", "check"), L("l", "check", 0, { done: true }), L("m", "number", 0, { restart: true }),
  ...Array.from({ length: 30 }, (_, k) => L("z" + k, "number", k < 28 ? 1 : 2))];
const doc = { kind: "page", page: { size: "B5", orient: "landscape", margin: { t: 10, r: 12, b: 14, l: 16 } },
  styles: { body: { font: "body", size: 10.5, line: 1.6, after: 6 }, h1: { name: "제목 1", based: "body", size: 20, bold: true, before: 12 }, h2: { based: "h1", size: 15 }, loop1: { based: "loop2" }, loop2: { based: "loop1", size: 9 } }, blocks };

// 서버 규칙으로 같은 것을 계산(자식 파이썬 - 스크립트 파일로 부른다. Windows pyenv 의 python 은 .bat 래퍼라 -c 여러 줄이 깨진다)
const r = spawnSync(process.env.NEXA_PYTHON || "python", [path.join(__dirname, "page_rules_dump.py")], { input: J(doc), encoding: "utf8", shell: process.platform === "win32" && !process.env.NEXA_PYTHON });
let ref = null;
try { ref = JSON.parse(r.stdout); } catch (e) { console.log("FAIL 서버 규칙을 불러오지 못했다: " + (r.stderr || r.error || r.stdout).toString().slice(0, 300)); fails++; }
if (ref) {
  eq("목록 머리 기호 - 서버와 같다", P.markers(blocks), ref.markers);
  eq("쪽 상자 - 서버와 같다", P.pageBox(doc), ref.box);
  for (const k of ["body", "h1", "h2", "nope"]) eq(`스타일 풀기 ${k} - 서버와 같다`, P.styleOf(doc, k), ref.styles[k]);
}
eq("번호 꼴 - 1. a. i. 돌려 쓰기", [P.numberLabel(3, 0), P.numberLabel(27, 1), P.numberLabel(4, 2), P.numberLabel(12, 3), P.numberLabel(2, 4)], ["3.", "aa.", "iv.", "12.", "b."]);
eq("스타일 풀기 - 도는 기준은 멈춘다", P.styleOf(doc, "loop1"), { size: 9 });
const ctx = { font: (f) => "F:" + f, color: (c) => "C:" + c };
eq("문단 CSS - 제목(상속·굵게·간격)", P.blockCss(doc, { style: "h2", align: "center" }, ctx), { fontFamily: "F:body", fontSize: "15pt", fontWeight: "700", lineHeight: "1.6", marginTop: "12pt", marginBottom: "6pt", textAlign: "center" });
eq("문단 CSS - 목록 들여쓰기(단계마다)", [P.blockCss(doc, L("q", "bullet", 0)).paddingLeft, P.blockCss(doc, L("q", "bullet", 2)).paddingLeft, P.blockCss(doc, { indent: 10, list: { kind: "number", level: 1 } }).paddingLeft], ["6mm", "18mm", "22mm"]);
eq("문단 CSS - 본문 기본", P.blockCss(doc, {}), { fontFamily: "body", fontSize: "10.5pt", lineHeight: "1.6", marginTop: "0pt", marginBottom: "6pt" });
console.log(fails ? `\n실패 ${fails}` : `\n전부 통과 (${n}사례)`);
process.exit(fails ? 1 : 0);
