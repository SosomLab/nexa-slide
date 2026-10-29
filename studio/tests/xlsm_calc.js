// xlsm_crosscheck.py 도우미 - 문서 JSON 을 화면 계산기(sheetcalc.js)로 다시 계산해 쓴다(macros.modules 가 있으면 VBA 실행기 vba.js 도).
//   node xlsm_calc.js <입력.json> <출력.json>   → stderr 에 VBA 컴파일 오류
const fs = require("fs"), path = require("path");
const C = require(path.join(__dirname, "..", "sheetcalc.js"));
const V = require(path.join(__dirname, "..", "vba.js"));
const [, , inp, out] = process.argv;
const doc = JSON.parse(fs.readFileSync(inp, "utf8"));
const mods = (doc.macros || {}).modules;
if (mods && mods.length) {
  const vb = V.compile(mods);
  for (const e of vb.errors) console.error(`VBA ${e.module}:${e.line} ${e.msg}`);
  C.setVba(vb, V);
  for (const t of doc.sheets || []) for (const c of Object.values(t.cells || {})) if (c && typeof c === "object" && c.f) delete c.v;  // 엑셀 저장값을 지우고 실제로 계산(VBA 함수 칸도)
}
C.recalc(doc);
fs.writeFileSync(out, JSON.stringify(doc));
