// nexa-text.js 모델 연산 시험(DOM 없음) - node studio/tests/nexa_text_check.js
require("../nexa-text.js");
const T = globalThis.NexaText;
let fails = 0, n = 0;
const J = JSON.stringify;
function eq(name, got, want) { n++; if (J(got) !== J(want)) { fails++; console.log(`FAIL ${name}\n     기대 ${J(want)}\n     실제 ${J(got)}`); } }
const R = (...a) => a.map((x) => (typeof x === "string" ? { t: x } : x));

// 정규화
eq("정규화 - 빈 조각·꺼진 서식·같은 이웃", T.normalize([{ t: "가", b: false }, { t: "" }, { t: "나" }, { t: "다", b: 1 }, { t: "라", b: true, i: null }]), [{ t: "가나" }, { t: "다라", b: true }]);
eq("정규화 - 글이 없으면 []", T.normalize([{ t: "" }, null, {}]), []);
eq("길이·글", [T.length(R("ab", { t: "한글", b: 1 })), T.text(R("ab", { t: "한글", b: 1 }))], [4, "ab한글"]);
const base = [{ t: "Hello " }, { t: "big", b: true }, { t: " world", c: "accent" }];  // 0..6 · 6..9 · 9..15
// 자르기
eq("slice 가운데", T.slice(base, 4, 11), [{ t: "o " }, { t: "big", b: true }, { t: " w", c: "accent" }]);
eq("slice 범위 밖은 맞춘다", T.slice(base, -3, 99), base);
eq("split·join 왕복", T.join(...T.split(base, 7)), base);
// 넣기 - 서식 잇기
eq("넣기 - 굵은 글 안", T.insertText(base, 8, "X"), [{ t: "Hello " }, { t: "biXg", b: true }, { t: " world", c: "accent" }]);
eq("넣기 - 경계에서는 앞 글자 서식", T.insertText(base, 9, "X"), [{ t: "Hello " }, { t: "bigX", b: true }, { t: " world", c: "accent" }]);
eq("넣기 - 맨 앞은 첫 글자 서식", T.insertText([{ t: "굵", b: true }], 0, "X"), [{ t: "X굵", b: true }]);
eq("넣기 - 빈 문단", T.insertText([], 0, "가"), [{ t: "가" }]);
eq("넣기 - 서식 지정", T.insertText(base, 0, "!", { i: true }), [{ t: "!", i: true }, { t: "Hello " }, { t: "big", b: true }, { t: " world", c: "accent" }]);
eq("넣기 - 링크 끝에서는 링크를 잇지 않는다", T.insertText([{ t: "문서", link: "https://example.com", u: true }], 2, "!"), [{ t: "문서", u: true, link: "https://example.com" }, { t: "!", u: true }]);
eq("넣기 - 링크 안에서는 잇는다", T.insertText([{ t: "문서", link: "x" }], 1, "!"), [{ t: "문!서", link: "x" }]);
// 지우기·바꾸기
eq("지우기 - 조각을 넘어", T.remove(base, 5, 10), [{ t: "Hello" }, { t: "world", c: "accent" }]);
eq("지우기 - 전부", T.remove(base, 0, 15), []);
eq("지우기 - 빈 구간은 그대로", T.remove(base, 3, 3), base);
eq("바꾸기 - 고른 글의 서식으로", T.replaceText(base, 6, 9, "small"), [{ t: "Hello " }, { t: "small", b: true }, { t: " world", c: "accent" }]);
eq("바꾸기 - 빈 글이면 지우기", T.replaceText(base, 6, 9, ""), [{ t: "Hello " }, { t: " world", c: "accent" }]);
// 서식
eq("서식 걸기 - 조각을 쪼갠다", T.setMark(base, 2, 4, "i", true), [{ t: "He" }, { t: "ll", i: true }, { t: "o " }, { t: "big", b: true }, { t: " world", c: "accent" }]);
eq("서식 걸기 - 값 있는 서식", T.setMark(base, 0, 6, "c", "red"), [{ t: "Hello ", c: "red" }, { t: "big", b: true }, { t: " world", c: "accent" }]);
eq("서식 벗기기 - 이웃과 합쳐진다", T.setMark(base, 6, 9, "b", false), [{ t: "Hello big" }, { t: " world", c: "accent" }]);
eq("켜고 끄기 - 일부만 켜져 있으면 전체 켬", T.toggleMark(base, 0, 9, "b"), [{ t: "Hello big", b: true }, { t: " world", c: "accent" }]);
eq("켜고 끄기 - 전체가 켜져 있으면 끔", T.toggleMark(base, 6, 9, "b"), [{ t: "Hello big" }, { t: " world", c: "accent" }]);
eq("켜고 끄기 - 값 있는 서식(형광펜)", T.toggleMark(T.toggleMark(base, 0, 5, "hl", "yellow"), 0, 5, "hl", "yellow"), base);
eq("위 첨자를 켜면 아래 첨자가 꺼진다", T.setMark([{ t: "x2", sub: true }], 1, 2, "sup", true), [{ t: "x", sub: true }, { t: "2", sup: true }]);
eq("모르는 서식 키는 무시", T.setMark(base, 0, 3, "zz", 1), base);
eq("서식 지우기 - 링크는 남김", T.clearMarks([{ t: "가", b: true, link: "x" }, { t: "나", i: true }], 0, 2, ["link"]), [{ t: "가", link: "x" }, { t: "나" }]);
eq("공통 서식 - 구간", T.commonMarks([{ t: "ab", b: true, i: true }, { t: "cd", b: true }], 0, 4), { b: true });
eq("공통 서식 - 빈 구간은 그 자리", T.commonMarks(base, 8, 8), { b: true });
// 입력을 고치지 않는다
const frozen = J(base); T.setMark(base, 0, 15, "u", true); T.insertText(base, 3, "zz"); T.remove(base, 0, 4);
eq("입력 배열을 고치지 않는다", J(base), frozen);
// 한글·이모지(코드 단위 위치)
eq("한글 넣기", T.insertText([{ t: "가다" }], 1, "나"), [{ t: "가나다" }]);
eq("이모지 뒤 넣기(코드 단위 2)", T.text(T.insertText([{ t: "😀" }], 2, "a")), "😀a");
// 문단
const blk = { id: "b1", type: "p", style: "h1", align: "center", runs: base };
const [p1, p2] = T.splitBlock(blk, 6, "b2");
eq("문단 나누기 - 앞", p1, { id: "b1", type: "p", style: "h1", align: "center", runs: [{ t: "Hello " }] });
eq("문단 나누기 - 뒤(속성을 물려받음)", p2, { id: "b2", type: "p", style: "h1", align: "center", runs: [{ t: "big", b: true }, { t: " world", c: "accent" }] });
eq("문단 나누기 - 제목 끝에서는 다음 스타일", T.splitBlock(blk, 15, "b2", "body")[1], { id: "b2", type: "p", style: "body", align: "center", runs: [] });
eq("문단 나누기 - 제목 가운데면 스타일 유지", T.splitBlock(blk, 6, "b2", "body")[1].style, "h1");
eq("문단 잇기", T.joinBlocks(p1, p2), { block: blk, at: 6 });
eq("일반 글 → 문단들", T.plainToParagraphs("가\r\n나\n\n다"), [[{ t: "가" }], [{ t: "나" }], [], [{ t: "다" }]]);
// 성질 시험 - 무작위 연산 뒤에도 늘 정규화돼 있고 글 길이가 맞는다
let seed = 7; const rnd = (k) => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % k; };
let runs = [], model = "";
for (let k = 0; k < 400; k++) {
  const len = T.length(runs), a = rnd(len + 1), b = a + rnd(len - a + 1), op = rnd(4);
  if (op === 0) { const s = ["가", "ab", " ", "한글 "][rnd(4)]; runs = T.insertText(runs, a, s); model = model.slice(0, a) + s + model.slice(a); }
  else if (op === 1) { runs = T.remove(runs, a, b); model = model.slice(0, a) + model.slice(b); }
  else if (op === 2) runs = T.toggleMark(runs, a, b, ["b", "i", "u"][rnd(3)]);
  else runs = T.setMark(runs, a, b, "c", [null, "red", "accent"][rnd(3)]);
  if (T.text(runs) !== model || J(T.normalize(runs)) !== J(runs)) { fails++; console.log(`FAIL 성질 시험 ${k}걸음: 글 또는 정규화가 어긋남`); break; }
}
n++;
console.log(fails ? `\n실패 ${fails}` : `\n전부 통과 (${n}사례)`);
process.exit(fails ? 1 : 0);
