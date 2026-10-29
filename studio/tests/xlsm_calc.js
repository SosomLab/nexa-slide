// xlsm_crosscheck.py 도우미 - 문서 JSON 을 화면 계산기(sheetcalc.js)로 다시 계산해 쓴다.  node xlsm_calc.js <입력.json> <출력.json>
const fs = require("fs"), path = require("path");
const C = require(path.join(__dirname, "..", "sheetcalc.js"));
const [, , inp, out] = process.argv;
const doc = JSON.parse(fs.readFileSync(inp, "utf8"));
C.recalc(doc);
fs.writeFileSync(out, JSON.stringify(doc));
