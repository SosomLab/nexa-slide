// 문서 종류 등록부(화면) - 슬라이드 · 시트 · 페이지. 서버 kinds 와 같은 이름을 쓴다(docs/dev/page-editor/design.md 4절).
//   NexaKinds.of(d) → 종류 정보 {kind, label, icon, unit, url(id)} · url(d) 그 문서의 편집기 주소 · list(experimental) 고를 수 있는 종류들
//   d = {id, kind} - kind 가 없거나 모르는 값이면 슬라이드(예전 덱 파일에는 kind 가 없다).
(function (root) {
  "use strict";
  const enc = encodeURIComponent;
  const KINDS = {
    deck: { kind: "deck", label: "슬라이드", icon: "▭", unit: "장", ext: ["pptx", "pdf"], url: (id) => `index.html#${enc(id)}` },
    sheet: { kind: "sheet", label: "시트", icon: "▦", unit: "탭", ext: ["xlsx"], url: (id) => `sheet.html?deck=${enc(id)}` },
    page: { kind: "page", label: "페이지", icon: "¶", unit: "쪽", ext: ["docx", "pdf"], url: (id) => `page.html?deck=${enc(id)}`, experimental: true },
  };
  const of = (d) => KINDS[(d && d.kind) || "deck"] || KINDS.deck;
  root.NexaKinds = {
    KINDS, of,
    url: (d) => of(d).url(d.id),
    /** 고를 수 있는 종류 - 실험 종류는 켜져 있을 때만(experimental = /api/config 의 experimental 목록) */
    list: (experimental) => Object.values(KINDS).filter((k) => !k.experimental || (experimental || []).includes(k.kind)),
  };
})(typeof window !== "undefined" ? window : globalThis);
