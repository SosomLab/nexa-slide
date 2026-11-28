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

{ // 각주: 쪽 1000 중 블록 3개(300) - 둘째에 각주 100(구분선 20) → 본문이 쓸 수 있는 끝 = 880, 셋째(600~900)는 다음 쪽
  const items = stack([300, { h: 300, fn: 100 }, 300]); const r = F.plan(items, H, G, null, { sep: 20 });
  check("20 각주 자리만큼 본문이 덜 들어간다 - 셋째 블록이 다음 쪽 · 1쪽에 120 내줌", brief(r) === "b2:push:600" && r.pages === 2 && r.notes[0] === 120 && !r.notes[1], brief(r) + " " + J(r.notes)); }
{ // 각주가 달린 블록 자신이 각주까지는 못 들어가면 블록째 다음 쪽(각주는 참조와 같은 쪽)
  const items = stack([700, { h: 250, fn: 100 }]); const r = F.plan(items, H, G, null, { sep: 20 });
  check("21 각주가 달린 블록 - 각주까지 안 들어가면 다음 쪽으로 · 각주는 그 쪽에", brief(r) === "b1:push:500" && r.notes[1] === 120 && !r.notes[0], brief(r) + " " + J(r.notes)); }
{ // 문단 줄 단위: 800 뒤 줄 10개(50) 문단 - 2번째 줄에 각주 60(+20) → 쓸 수 있는 끝 920 → 2줄만(900), 3번째 줄부터 다음 쪽
  const items = stack([800, { h: 500, kind: "p", fn: 60 }]); const r = F.plan(items, H, G, (it) => lines(it, 10, 50).map((l, i) => (i === 1 ? { ...l, fn: 60 } : l)), { sep: 20 });
  check("22 문단 - 각주가 달린 줄까지 놓고 남는 자리만큼만 줄을 둔다(2줄 뒤)", brief(r) === "b1:split@2:300" && r.notes[0] === 80, brief(r) + " " + J(r.notes)); }
{ // 각주 줄이 이 쪽에 못 들어가면 그 줄부터 다음 쪽 - 각주도 다음 쪽
  const items = stack([800, { h: 500, kind: "p", fn: 150 }]); const r = F.plan(items, H, G, (it) => lines(it, 10, 50).map((l, i) => (i === 2 ? { ...l, fn: 150 } : l)), { sep: 20 });
  check("23 문단 - 각주가 안 들어가는 줄은 다음 쪽으로(각주도 그 쪽)", brief(r) === "b1:split@2:300" && !r.notes[0] && r.notes[1] === 170, brief(r) + " " + J(r.notes)); }
{ // 표 행의 각주
  const items = stack([700, { h: 600, kind: "table", fn: 90 }]); const t = items[1]; t.rows = Array.from({ length: 6 }, (_, i) => ({ top: t.top + i * 100, bottom: t.top + (i + 1) * 100, ok: true, fn: i === 0 ? 90 : 0 }));
  const r = F.plan(items, H, G, null, { sep: 10 });  // 1행(700~800)에 각주 100 → 끝 900 → 2행까지, 3번째 행 앞에서
  check("24 표 - 행의 각주 자리만큼 행이 덜 들어간다(2행 뒤)", brief(r) === "b1:row@2:300" && r.notes[0] === 100, brief(r) + " " + J(r.notes)); }
{ const r = F.plan(stack([300, 300, 300]), H, G, null, { sep: 20 }); check("25 각주가 없으면 전과 같다 · notes 비어 있음", r.breaks.length === 0 && Object.keys(r.notes).length === 0, J(r)); }

{ // 다단: 2단 구역에 400짜리 블록 5개(단 높이 1000) - 단마다 2개: [0,1] 1단 · [2,3] 2단(위로 끌어올림 -800) · [4] 다음 쪽 1단
  const items = stack([400, 400, 400, 400, 400]).map((x) => ({ ...x, cols: 2 })); const r = F.plan(items, H, G);
  check("26 2단 - 넘치는 블록은 다음 단 머리로(음수 밀기) · 마지막 단이 차면 다음 쪽 첫 단", brief(r) === "b2:push:-800 b4:push:400" && J(r.place) === J({ b0: 0, b1: 0, b2: 1, b3: 1, b4: 0 }) && r.pages === 2, brief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 1단 머리(200) 뒤에 2단 본문: 2단 구역은 머리 아래(200)에서 시작 - 단 높이 800
  const items = stack([200, { h: 500, cols: 2 }, { h: 500, cols: 2 }, { h: 500, cols: 2 }]); const r = F.plan(items, H, G);
  // b1 200~700(1단) · b2 700~1200 넘침 → 2단 머리 200 으로(-500) · b3 자연 1200 → 2단에서 700~1200 넘침 → 다음 쪽 1단 머리(1200)
  check("27 1단 → 2단 - 새 구역은 앞 구역 끝에서 시작하고 다음 쪽부터는 쪽 머리에서", brief(r) === "b2:push:-500 b3:push:500" && J(r.place) === J({ b1: 0, b2: 1, b3: 0 }) && r.pages === 2, brief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 2단 → 1단: 1단 구역은 가장 아래까지 내려간 단의 끝에서 시작
  const items = stack([{ h: 600, cols: 2 }, { h: 600, cols: 2 }, { h: 300, cols: 2 }, 100]); const r = F.plan(items, H, G);
  // b0 0~600(1단) · b1 → 2단 0~600 · b2 → 2단 600~900 · b3(1단 구역) 는 max(600, 900) = 900 에서 시작: 자연 1500 + (-600) = 900 → 밀기 없음
  check("28 2단 → 1단 - 가장 긴 단의 끝에서 이어진다", brief(r) === "b1:push:-600" && J(r.place) === J({ b0: 0, b1: 1, b2: 1 }) && r.pages === 1, brief(r) + " " + J(r.place)); }
{ // 2단 → 1단인데 뒤 단이 더 짧다: 1단 구역은 앞 단의 끝(800)으로 내려가야 한다
  const items = stack([{ h: 800, cols: 2 }, { h: 300, cols: 2 }, 100]); const r = F.plan(items, H, G);
  check("29 2단 → 1단 - 뒤 단이 짧으면 앞 단 끝까지 내린다", brief(r) === "b1:push:-800 b2:push:500" && r.pages === 1, brief(r)); }
{ // 단 나누기
  const items = stack([{ h: 100, cols: 2 }, { h: 0, kind: "colbreak", cols: 2 }, { h: 100, cols: 2 }, { h: 0, kind: "colbreak", cols: 2 }, { h: 100, cols: 2 }]); const r = F.plan(items, H, G);
  check("30 단 나누기 - 다음 블록이 다음 단 머리(마지막 단이면 다음 쪽)", brief(r) === "b2:push:-100 b4:push:1100" && r.place.b2 === 1 && r.place.b4 === 0 && r.pages === 2, brief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 다단 구역 안의 쪽 나누기 - 다음 쪽 첫 단
  const items = stack([{ h: 100, cols: 2 }, { h: 0, kind: "break", cols: 2 }, { h: 100, cols: 2 }]); const r = F.plan(items, H, G);
  check("31 다단 구역의 쪽 나누기 - 다음 쪽 첫 단 머리", brief(r) === "b2:push:1100" && r.place.b2 === 0 && r.pages === 2, brief(r) + " " + J(r.place)); }
{ const r = F.plan(stack([600, 600, 300]), H, G); check("32 1단 문서는 전과 같다 · place 비어 있음", brief(r) === "b1:push:600" && Object.keys(r.place).length === 0, brief(r) + J(r.place)); }

// 다단 구역의 문단을 단 경계에서 나눈다(opt.colSplit - PG-101 2차). colsplit = 그 줄부터의 꼬리를 보이는 곳만 옮긴다(dcol 단 · dy 세로), 뒤 블록이 그 이동을 위 여백으로 받는다
const CS = { colSplit: true };
const cbrief = (r) => r.breaks.map((b) => b.type === "colsplit" ? `${b.id}:colsplit@${b.line}:${b.dcol}:${Math.round(b.dy)}${b.page ? ":p" : ""}` : `${b.id}:${b.type}:${Math.round(b.h)}${b.page ? ":p" : ""}`).join(" ");
const two = (list) => stack(list).map((x) => ({ ...x, cols: 2 }));
{ // 800 뒤 줄 10개 문단 - 4줄은 이 단(800~1000), 5번째 줄부터 다음 단 머리(0). 줄 4 의 자연 위치 1002 → dy -1002. 뒤 블록은 그 이동(-1002)을 받아 꼬리 아래(298)에 놓인다
  const r = F.plan(two([800, { h: 500, kind: "p" }, 300]), H, G, (it) => lines(it, 10, 50), CS);
  check("33 다단 문단 나눔 - 넘치는 줄부터 다음 단 머리로(colsplit) · 뒤 블록이 이동을 받는다", cbrief(r) === "b1:colsplit@4:1:-1002 b2:push:-1002" && J(r.place) === J({ b0: 0, b1: 0, b2: 1 }) && r.pages === 1, cbrief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 마지막 단에서 넘치면 꼬리는 다음 쪽 첫 단: 900 | 800(2단으로 -900) | 문단(2단 800~1000 에 4줄, 나머지는 다음 쪽 1200)
  const r = F.plan(two([900, 800, { h: 500, kind: "p" }, 100]), H, G, (it) => lines(it, 10, 50), CS);
  check("34 마지막 단의 문단 - 꼬리는 다음 쪽 첫 단(dcol -1 · 쪽 넘김) · 2쪽", cbrief(r) === "b1:push:-900 b2:colsplit@4:-1:198:p b3:push:198" && r.place.b2 === 1 && r.place.b3 === 0 && r.pages === 2, cbrief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 외톨이 첫 줄: 940 뒤 문단 → 한 줄만 들어간다 → 나누지 않고 문단째 다음 단으로
  const r = F.plan(two([940, { h: 500, kind: "p" }]), H, G, (it) => lines(it, 10, 50), CS);
  check("35 첫 줄만 남으면 나누지 않고 문단째 다음 단", cbrief(r) === "b1:push:-940" && r.place.b1 === 1, cbrief(r) + " " + J(r.place)); }
{ // 끝 줄만 넘어가면 한 줄 더 데려간다: 550 뒤 줄 10개 → 9줄이 들어가고 끝 줄만 넘침 → 8줄에서 나눔
  const r = F.plan(two([550, { h: 500, kind: "p" }]), H, G, (it) => lines(it, 10, 50), CS);
  check("36 끝 줄만 넘어가면 한 줄 더 데려간다(@8)", cbrief(r) === "b1:colsplit@8:1:-952", cbrief(r)); }
{ // 단보다 긴 문단: 900 뒤 줄 40개(2000) → 1단 2줄 · 2단 20줄 · 다음 쪽 1단 18줄. 둘째 조각의 dy 는 문단 안에서 쌓인 값(-1002 + 200)
  const r = F.plan(two([900, { h: 2000, kind: "p" }, 100]), H, G, (it) => lines(it, 40, 50), CS);
  check("37 단보다 긴 문단 - 세 자리에 걸친다(colsplit 둘 · dy 는 쌓인 값) · 뒤 블록은 모두 합친 이동", cbrief(r) === "b1:colsplit@2:1:-1002 b1:colsplit@22:0:-802:p b2:push:-802" && r.pages === 2 && r.place.b2 === 0, cbrief(r) + " " + J(r.place) + " p" + r.pages); }
{ // 끄면 전과 같다 - 통째로 다음 단
  const r = F.plan(two([800, { h: 500, kind: "p" }, 300]), H, G, (it) => lines(it, 10, 50));
  check("38 colSplit 을 끄면 전과 같다(문단째 다음 단)", cbrief(r) === "b1:push:-800" && r.place.b1 === 1, cbrief(r)); }
{ // 각주가 달린 문단 · nosplit · 줄을 잴 수 없는 문단은 나누지 않는다
  const a = F.plan(two([800, { h: 500, kind: "p", fn: 40 }]), H, G, (it) => lines(it, 10, 50), CS);
  const b = F.plan(two([800, { h: 500, kind: "p", nosplit: true }]), H, G, (it) => lines(it, 10, 50), CS);
  const c = F.plan(two([800, { h: 500, kind: "p" }]), H, G, () => [], CS);
  check("39 각주 문단 · nosplit · 줄을 못 재는 문단은 통째로", [a, b, c].every((r) => cbrief(r) === "b1:push:-800"), [a, b, c].map(cbrief).join(" | ")); }
{ // 나눈 문단 뒤에 구역이 1단으로 바뀐다 - 가장 아래까지 내려간 단(1단 1000)의 끝에서 시작. 뒤 블록은 이월분과 구역 이동을 한 번의 밀기로 받는다
  const items = two([800, { h: 500, kind: "p" }]).concat([{ id: "z", kind: "obj", top: 1300, bottom: 1400 }]);
  const r = F.plan(items, H, G, (it) => lines(it, 10, 50), CS);
  // 1단 구역은 가장 아래까지 내려간 단(첫 단에 남긴 4번째 줄의 끝 998)에서 시작한다 - z(높이 100)는 998 에 놓으면 쪽을 넘쳐 다음 쪽 머리(1200)로.
  //   z 의 자연 위치 1300 → 1200: 이월 -1002 + 구역 이동 +700 + 쪽 넘김 +202 = -100 을 밀기 하나로
  check("40 나눈 문단 뒤 1단 구역 - 나눈 문단이 남긴 단의 끝 아래에서 시작(넘치면 다음 쪽) · 밀기는 하나로 합쳐진다", r.breaks.filter((x) => x.id === "z").length === 1 && cbrief(r) === "b1:colsplit@4:1:-1002 z:push:-100:p" && r.pages === 2, cbrief(r) + " p" + r.pages); }
{ // 같은 상황에서 뒤 블록이 작으면(높이 2) 그 단의 끝 바로 아래(998)에 놓인다 - 이월 -1002 + 구역 이동 +700 = -302
  const items = two([800, { h: 500, kind: "p" }]).concat([{ id: "z", kind: "obj", top: 1300, bottom: 1302 }]);
  const r = F.plan(items, H, G, (it) => lines(it, 10, 50), CS);
  check("42 나눈 문단 뒤 1단 구역 - 작은 블록은 남긴 단의 끝 바로 아래", cbrief(r) === "b1:colsplit@4:1:-1002 z:push:-302" && r.pages === 1, cbrief(r) + " p" + r.pages); }
{ // 1단 문서에는 영향 없음
  const r = F.plan(stack([800, { h: 500, kind: "p" }]), H, G, (it) => lines(it, 10, 50), CS);
  check("41 1단 문서는 colSplit 을 켜도 전과 같다(줄 사이 빈 자리)", brief(r) === "b1:split@4:200", brief(r)); }
console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
process.exit(fail ? 1 : 0);
