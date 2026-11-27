// nexa-objects.js 계산 시험(DOM 없음) - node studio/tests/nexa_objects_check.js
const path = require("path");
const O = require(path.join(__dirname, "..", "nexa-objects.js"));
let fail = 0, n = 0;
const J = JSON.stringify, R = (r) => [r.x, r.y, r.w, r.h].map((v) => Math.round(v * 100) / 100);
const eq = (name, got, want) => { n++; const ok = J(got) === J(want); if (!ok) fail++; console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : " :: " + J(got) + " ≠ " + J(want)}`); };
const r0 = { x: 100, y: 50, w: 200, h: 100 };

eq("격자 붙이기 - 8 단위 · 격자 0 이면 그대로", [O.snap(13, 8), O.snap(12, 8), O.snap(13.4, 0)], [16, 16, 13.4]);
eq("한 축으로 - 더 많이 움직인 쪽만", [O.axisLock(30, -10), O.axisLock(5, 9), O.axisLock(7, 7)], [[30, 0], [0, 9], [7, 0]]);
eq("고르기 상자 - 완전히 들어간 것만", [O.inBox({ x: 10, y: 10, w: 20, h: 20 }, { x: 0, y: 0, w: 30, h: 30 }), O.inBox({ x: 10, y: 10, w: 21, h: 20 }, { x: 0, y: 0, w: 30, h: 30 })], [true, false]);
eq("화살표 - 한 걸음·큰 걸음·다른 키", [O.nudge("ArrowLeft", false, 1, 8), O.nudge("ArrowDown", true, 0.5, 5), O.nudge("a", false, 1, 8)], [[-1, 0], [0, 5], null]);
eq("크기 se - 오른쪽 아래로 늘림(왼쪽 위 고정)", R(O.resize(r0, "se", 40, 20)), [100, 50, 240, 120]);
eq("크기 nw - 왼쪽 위로 늘림(오른쪽 아래 고정)", R(O.resize(r0, "nw", -40, -20)), [60, 30, 240, 120]);
eq("크기 e · n - 한 변만", [R(O.resize(r0, "e", 30, 99)), R(O.resize(r0, "n", 99, -10))], [[100, 50, 230, 100], [100, 40, 200, 110]]);
eq("크기 w · s - 한 변만", [R(O.resize(r0, "w", 30, 0)), R(O.resize(r0, "s", 0, -30))], [[130, 50, 170, 100], [100, 50, 200, 70]]);
eq("최소 크기 - 그보다 작아지지 않고 고정점은 그대로", [R(O.resize(r0, "se", -500, -500, { min: 4 })), R(O.resize(r0, "nw", 500, 500, { min: 4 }))], [[100, 50, 4, 4], [296, 146, 4, 4]]);
eq("선(최소 0) - 높이 0 까지", R(O.resize({ x: 0, y: 0, w: 40, h: 0 }, "se", 10, 0, { min: 0 })), [0, 0, 50, 0]);
eq("비율 유지 - 모서리(더 많이 바뀐 쪽을 따른다)", [R(O.resize(r0, "se", 100, 0, { keep: true })), R(O.resize(r0, "se", 0, 50, { keep: true }))], [[100, 50, 300, 150], [100, 50, 300, 150]]);
eq("비율 유지 - nw 모서리는 오른쪽 아래 고정", R(O.resize(r0, "nw", -100, 0, { keep: true })), [0, 0, 300, 150]);
eq("비율 유지 - 변(e)은 세로 가운데를 지킨다", R(O.resize(r0, "e", 100, 0, { keep: true })), [100, 25, 300, 150]);
eq("비율 유지 + 최소", R(O.resize(r0, "se", -1000, -1000, { keep: true, min: 10 })), [100, 50, 20, 10]);
{ const g = O.guideSnap({ x: 97, y: 200, w: 50, h: 20 }, { x: [100, 300], y: [0, 400] }, 6);
  eq("안내선 - 왼쪽이 100 에 붙는다 · 세로는 붙을 선이 없다", [g.dx, g.gx, g.dy, g.gy], [3, 100, 0, null]); }
{ const g = O.guideSnap({ x: 250, y: 388, w: 96, h: 20 }, { x: [300], y: [400] }, 6);
  eq("안내선 - 가운데(298 → 300) · 가운데(398 → 400)", [g.dx, g.gx, g.dy, g.gy], [2, 300, 2, 400]); }
{ const g = O.guideSnap({ x: 0, y: 0, w: 10, h: 10 }, { x: [100] }, 6); eq("안내선 - 멀면 붙지 않는다", [g.dx, g.gx], [0, null]); }
eq("손잡이 8방향", O.HANDLES.length, 8);
console.log(`RESULT ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
process.exit(fail ? 1 : 0);
