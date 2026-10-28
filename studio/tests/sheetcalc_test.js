// 시트 수식 계산기(화면, sheetcalc.js) 시험 - sheetcalc_test.py 와 같은 사례 파일(sheetcalc_cases.json). 두 곳이 같은 값을 내야 한다.
const fs = require("fs"), path = require("path");
const C = require(path.join(__dirname, "..", "sheetcalc.js"));
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, "sheetcalc_cases.json"), "utf8"));
const same = (a, b) => (typeof a === "number" && typeof b === "number" ? Math.abs(a - b) < 1e-9 : a === b);
const fails = [];
let ok = 0;
for (const [f, want] of spec.cases) {
  const doc = { sheets: JSON.parse(JSON.stringify(spec.sheets)) };
  doc.sheets[0].cells[spec.at] = { f };
  C.recalc(doc);
  const got = doc.sheets[0].cells[spec.at].v;
  if (same(got, want)) ok++; else { fails.push(f); console.log(`FAIL ${f} → ${JSON.stringify(got)} (기대 ${JSON.stringify(want)})`); }
}
const cyc = { sheets: [{ id: "t01", name: "S", cells: { A1: { f: "=B1+1" }, B1: { f: "=A1+1" } } }] };
C.recalc(cyc);
if (cyc.sheets[0].cells.A1.v !== "#REF!") { fails.push("순환 참조"); console.log("FAIL 순환 참조 →", cyc.sheets[0].cells.A1.v); }
console.log(`사례 ${spec.cases.length}개 중 ${ok}개 같음`);
console.log("\n실패:", fails.length ? fails.join(", ") : "없음");
process.exit(fails.length ? 1 : 0);
