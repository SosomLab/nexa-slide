// 페이지 쪽 나눔 계산(page-flow.js 의 plan) 시험 - PG-102. 화면(빈 자리 끼우기)은 page_ui_test.py 가 본다.
//   node page_flow_check.js
const path = require("path");
const F = require(path.join(__dirname, "..", "page-flow.js"));
let fail = 0, n = 0;
function check(name, ok, detail) { n++; if (!ok) fail++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : " :: " + detail}`); }
const J = (x) => JSON.stringify(x);
const H = 1000, G = 200;  // 쪽 본문 1000, 본문 사이 200 → 쪽 시작 0 · 1200 · 2400
/** 높이 목록 → 이어 붙인 블록들 */
function stack(list) { let y = 0; return list.map((x, i) => { const h = typeof x === "number" ? x : x.h; const it = { id: "b" + i, kind: "obj", ...(typeof x === "number" ? {} : x), top: y, bottom: y + h }; delete it.h; y += h; return it; }); }
const lines = (it, count, lh) => Array.from({ length: count }, (_, i) => ({ top: it.top + i * lh + 2, bottom: it.top + (i + 1) * lh - 2 }));
const brief = (r) => r.breaks.map((b) => `${b.id}:${b.type}${b.line !== undefined ? "@" + b.line : ""}${b.row !== undefined ? "@" + b.row : ""}:${Math.round(b.h)}`).join(" ");

{ const r = F.plan(stack([300, 300, 300]), H, G); check("1 한 쪽에 다 들어간다 - 빈 자리 없음 · 1쪽", r.breaks.length === 0 && r.pages === 1, J(r)); }
{ const r = F.plan([], H, G); check("2 빈 문서 - 1쪽", r.breaks.length === 0 && r.pages === 1, J(r)); }
{ const r = F.plan(stack([600, 600, 300]), H, G);  // 둘째가 넘친다 → 통째 다음 쪽(600 → 1200)
  check("3 넘치는 블록은 다음 쪽 머리로 - push 600 · 2쪽", brief(r) === "b1:push:600" && r.pages === 2, brief(r) + " p" + r.pages); }
{ const r = F.plan(stack([600, 600, 600, 600]), H, G);  // 600 | 600 | 600 | 600 → 쪽마다 하나
  check("4 연달아 넘친다 - 쪽마다 밀기(앞의 밀림을 반영)", brief(r) === "b1:push:600 b2:push:600 b3:push:600" && r.pages === 4, brief(r) + " p" + r.pages); }
{ const r = F.plan(stack([400, 400, 200]), H, G); check("5 쪽을 꼭 채운다(1000) - 넘침 아님", r.breaks.length === 0 && r.pages === 1, brief(r)); }
{ const items = stack([300, { h: 0, kind: "break" }, 300]); const r = F.plan(items, H, G);
  check("6 쪽 나누기 블록 - 다음 블록이 다음 쪽 머리(300 → 1200)", brief(r) === "b2:push:900" && r.pages === 2, brief(r) + " p" + r.pages); }
{ const items = stack([{ h: 0, kind: "break" }, 300]); const r = F.plan(items, H, G);
  check("7 맨 앞의 쪽 나누기 - 빈 첫 쪽", brief(r) === "b1:push:1200" && r.pages === 2, brief(r)); }
{ // 문단 나누기: 800 뒤에 줄 10개(줄 50) 문단 → 4줄(800~1000)까지 이 쪽, 5번째 줄부터 다음 쪽
  const items = stack([800, { h: 500, kind: "p" }]); const r = F.plan(items, H, G, (it) => lines(it, 10, 50));
  check("8 문단을 줄 사이에서 나눈다 - 4줄 뒤(줄 경계 1000 → 1200)", brief(r) === "b1:split@4:200" && r.pages === 2, brief(r)); }
{ // 외톨이 첫 줄: 940 뒤 문단 → 첫 줄 하나만 들어간다 → 문단째 다음 쪽
  const items = stack([940, { h: 500, kind: "p" }]); const r = F.plan(items, H, G, (it) => lines(it, 10, 50));
  check("9 첫 줄만 남으면 문단째 다음 쪽으로", brief(r) === "b1:push:260" && r.pages === 2, brief(r)); }
{ // 외톨이 끝 줄: 600 뒤 줄 9개 문단(450) → 8줄 들어가고 끝 줄만 넘어간다 → 7줄 뒤에서 나눈다
  const items = stack([600, { h: 450, kind: "p" }]); const r = F.plan(items, H, G, (it) => lines(it, 9, 50));
  check("10 끝 줄만 넘어가면 한 줄 더 데려간다 - 7줄 뒤", brief(r) === "b1:split@7:250" && r.pages === 2, brief(r)); }
{ // 쪽보다 긴 문단: 줄 50개(2500) → 20줄마다
  const items = stack([{ h: 2500, kind: "p" }]); const r = F.plan(items, H, G, (it) => lines(it, 50, 50));
  check("11 쪽보다 긴 문단 - 20줄마다 나눈다 · 3쪽", brief(r) === "b0:split@20:200 b0:split@40:200" && r.pages === 3, brief(r) + " p" + r.pages); }
{ const items = stack([900, { h: 300, kind: "p" }, 100]); const r = F.plan(items, H, G, () => []);
  check("12 줄을 잴 수 없는 문단(빈 문단 등) - 통째로 민다", brief(r) === "b1:push:300", brief(r)); }
{ // 표: 700 뒤에 행 6개(행 100) → 3행까지, 4번째 행 앞에 빈 행
  const items = stack([700, { h: 600, kind: "table" }]); const t = items[1]; t.rows = Array.from({ length: 6 }, (_, i) => ({ top: t.top + i * 100, bottom: t.top + (i + 1) * 100, ok: true }));
  const r = F.plan(items, H, G); check("13 표를 행 사이에서 나눈다 - 3행 뒤", brief(r) === "b1:row@3:200" && r.pages === 2, brief(r)); }
{ // 합친 칸이 걸친 행(3번 행 앞은 못 나눔) → 2행 뒤에서
  const items = stack([700, { h: 600, kind: "table" }]); const t = items[1]; t.rows = Array.from({ length: 6 }, (_, i) => ({ top: t.top + i * 100, bottom: t.top + (i + 1) * 100, ok: i !== 3 }));
  const r = F.plan(items, H, G); check("14 합친 칸이 걸친 행 앞에서는 나누지 않는다 - 한 행 앞에서(빈 자리 300)", brief(r) === "b1:row@2:300", brief(r)); }
{ // 첫 행도 안 들어간다 → 표째 다음 쪽
  const items = stack([950, { h: 300, kind: "table" }]); const t = items[1]; t.rows = Array.from({ length: 3 }, (_, i) => ({ top: t.top + i * 100, bottom: t.top + (i + 1) * 100, ok: true }));
  const r = F.plan(items, H, G); check("15 첫 행이 안 들어가면 표째 다음 쪽", brief(r) === "b1:push:250" && r.pages === 2, brief(r)); }
{ // 쪽보다 큰 그림: 쪽 머리에 있으면 그대로 두고(넘침), 다음 블록은 놓인 자리의 쪽에서 이어 간다
  const r = F.plan(stack([1500, 100]), H, G); check("16 쪽보다 큰 블록 - 밀지 않고, 뒤 블록은 끝나지 않는다", r.breaks.length === 0 && r.pages === 2, brief(r) + " p" + r.pages); }
{ // 밀기의 gap = 앞 블록과의 자연 간격(여백 겹침 보정용)
  const items = [{ id: "a", kind: "obj", top: 0, bottom: 600 }, { id: "b", kind: "obj", top: 620, bottom: 1100 }]; const r = F.plan(items, H, G);
  check("17 밀기는 앞 블록과의 간격을 같이 알려 준다(gap 20 · h 580)", r.breaks.length === 1 && r.breaks[0].gap === 20 && r.breaks[0].h === 580, J(r.breaks)); }
{ // 나눈 뒤의 블록들 - 밀림이 쌓인다: 800 + 문단 500(4줄 뒤 나눔 → 뒤 6줄 300 이 1200~1500) + 800 → 1500+800 = 2300 > 2200 → 다음 쪽
  const items = stack([800, { h: 500, kind: "p" }, 800]); const r = F.plan(items, H, G, (it) => lines(it, 10, 50));
  check("18 나눈 문단 뒤의 블록 - 쌓인 밀림으로 다시 계산", brief(r) === "b1:split@4:200 b2:push:900" && r.pages === 3, brief(r) + " p" + r.pages); }
{ // 머리글 행 되풀이: 머리글 30 + 행 100짜리 표 - 다음 쪽은 머리글 자리(30)만큼 덜 들어간다
  const items = stack([700, { h: 1330, kind: "table", headH: 30 }]); const t = items[1];
  t.rows = [{ top: t.top, bottom: t.top + 30, ok: true }, ...Array.from({ length: 13 }, (_, i) => ({ top: t.top + 30 + i * 100, bottom: t.top + 130 + i * 100, ok: i > 0 }))];
  const r = F.plan(items, H, G);  // 첫 쪽: 머리글 + 2행(700+30+200=930) → 3번째 행(색인 3) 앞에서. 둘째 쪽: 머리글 30 + 9행(900) = 930 → 색인 12 앞에서
  check("19 머리글 행 되풀이 - 다음 쪽은 머리글만큼 덜 들어가고 빈 행에 head 를 싣는다", brief(r) === "b1:row@3:270 b1:row@12:270" && r.breaks.every((b) => b.head === 30) && r.pages === 3, brief(r) + " " + J(r.breaks.map((b) => b.head)) + " p" + r.pages); }

console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
process.exit(fail ? 1 : 0);
