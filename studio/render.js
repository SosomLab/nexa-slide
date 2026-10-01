/* 요소 모델 → HTML(절대 위치) 순수 렌더러 — 썸네일·캔버스·검증 페이지 공용.
   export_pptx.py 와 같은 규칙으로 그린다. 한쪽을 고치면 다른 쪽(common.py·export_pptx.py)도 고친다.
     - 좌표·크기 px(1280×720), 글자 size px (PPT pt = px × 0.75)
     - 줄마다 한 단락, 줄 높이 = size × lineHeight (PPT "정확히" 줄 간격)
     - 인라인: **굵게**, ==강조==, [[토큰|색 글자]], {page}
     - plan: [[글자]] = warn 강조, [[ok:글자]] = ok 강조 (배경·글자색·굵게만 — 폭 불변) */
(function (root) {
  "use strict";
  let T = null; // tokens.json

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function setTokens(t) { T = t; }
  function color(v, dflt) {
    if (!v) return dflt || null;
    let x = v;
    for (let i = 0; i < 5; i++) {
      if (typeof x === "string" && x[0] === "#") return x.length === 7 ? x.toUpperCase() : (dflt || "#000000");
      if (T && T.colors && x in T.colors) x = T.colors[x]; else return dflt || "#000000";
    }
    return dflt || "#000000";
  }
  function radius(v, w, h) {
    if (v === undefined || v === null || v === 0 || v === "0" || v === "") return 0;
    let r = typeof v === "string" ? (T && T.radius && v in T.radius ? T.radius[v] : parseFloat(v)) : v;
    r = Number(r) || 0;
    return Math.max(0, Math.min(r, Math.min(w, h) / 2));
  }
  // style="…" 속성 안에 들어가므로 큰따옴표를 작은따옴표로 바꾼다
  /** PPT 줄 배치 보정(px): PowerPoint 는 여분 줄 높이를 위 75%·아래 25%로 둔다 — tokens.pptTextShift */
  const shift = (k, s, lh) => {
    const c = T && T.pptTextShift && T.pptTextShift[k === "mono" ? "mono" : "body"];
    return c ? +(s * (c[0] * lh + c[1])).toFixed(2) : 0;
  };
  const font = (k) => (T && T.fonts && T.fonts[k || "body"] ? T.fonts[k || "body"].css : "'Malgun Gothic', sans-serif").replace(/"/g, "'");

  // ---------- 인라인 강조 ----------
  const MARK = /\*\*(.+?)\*\*|==(.+?)==|\[\[([#\w-]+)\|(.+?)\]\]/g;
  function runs(text, page) {
    let s = String(text == null ? "" : text);
    if (page != null) s = s.split("{page}").join(String(page));
    const out = []; let pos = 0, m;
    MARK.lastIndex = 0;
    while ((m = MARK.exec(s))) {
      if (m.index > pos) out.push([s.slice(pos, m.index), {}]);
      if (m[1] !== undefined) out.push([m[1], { bold: true }]);
      else if (m[2] !== undefined) out.push([m[2], { bold: true, color: "primary" }]);
      else out.push([m[4], { color: m[3] }]);
      pos = MARK.lastIndex;
    }
    if (pos < s.length) out.push([s.slice(pos), {}]);
    return out.length ? out : [["", {}]];
  }
  const plain = (s) => runs(s).map((r) => r[0]).join("");

  // ---------- 코드 하이라이트 (concept.html hlSQL() 이식 — common.py hl_sql 과 같은 결과) ----------
  // 역할: k 예약어·타입·함수(굵게) · tb 테이블·CTE · al 테이블 별칭(기울임) · ca 결과 컬럼 별칭(기울임)
  //       st 문자열 · nu 숫자 · co 주석 · bi 바인드 · null 일반
  const SQL_KW = new Set(("select from where and or not in exists join left right full outer inner cross on as group by order having union all with recursive " +
    "case when then else end between like is null distinct insert into values update set delete merge using matched connect prior start table desc asc over " +
    "partition fetch first rows only create index primary key foreign references constraint default level nocycle siblings search depth breadth cycle to").split(" "));
  const SQL_TYPE = new Set("varchar varchar2 number date text char integer int timestamp clob blob boolean".split(" "));
  const WS = /^\s+$/;
  function hlSQL(src) {
    const re = /(--[^\n]*|\/\*[\s\S]*?\*\/)|('(?:[^']|'')*')|(:[A-Za-z_]\w*)|(\b\d+(?:\.\d+)?\b)|("[^"]+"|[A-Za-z_][\w$#]*)|(\s+|[^\s])/g;
    const toks = []; let m;
    while ((m = re.exec(src))) toks.push(m[1] ? ["co", m[0]] : m[2] ? ["st", m[0]] : m[3] ? ["bi", m[0]] : m[4] ? ["nu", m[0]] : m[5] ? ["id", m[0]] : ["p", m[0]]);
    const tables = new Set(), aliases = new Set();
    const next = (i) => { for (let j = i + 1; j < toks.length; j++) if (!WS.test(toks[j][1])) return toks[j]; return null; };
    const pass = () => {
      let prev = "", expect = false;
      return toks.map(([t, v], i) => {
        if (t !== "id") {
          if (!(t === "p" && (WS.test(v) || v === "."))) expect = false;
          if (t === "p" && v === ",") prev = prev === "_t" ? "from" : prev;
          return [v, t === "p" ? null : t];
        }
        const low = v.toLowerCase(), nx = next(i);
        if (SQL_TYPE.has(low)) { prev = low; return [v, "k"]; }
        if (SQL_KW.has(low)) { if (low !== "recursive") prev = low; expect = false; return [v, "k"]; }
        if (nx && nx[1] === "(" && !["with", "_t"].includes(prev)) { prev = ""; return [v, "k"]; }
        if (nx && nx[1] === ".") return [v, aliases.has(low) ? "al" : "tb"];
        if (["from", "join", "into", "update", "with", "table", "using", "merge"].includes(prev)) { tables.add(low); prev = "_t"; expect = true; return [v, "tb"]; }
        if (expect && prev === "_t") { aliases.add(low); expect = false; prev = ""; return [v, "al"]; }
        if (prev === "as") { prev = ""; return [v, tables.has(low) ? "tb" : "ca"]; }
        if (tables.has(low)) return [v, "tb"];
        if (aliases.has(low)) return [v, "al"];
        prev = ""; return [v, null];
      });
    };
    pass();         // 1차: 테이블·별칭 수집
    return pass();  // 2차: 색 입히기
  }
  const PY_KW = new Set("def return import from as for in if elif else while with try except finally class lambda and or not is None True False yield pass break continue raise async await".split(" "));
  function hlPython(src) {
    const re = /(#[^\n]*)|('[^'\n]*'|"[^"\n]*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+|[^\s])/g;
    const out = []; let m;
    while ((m = re.exec(src))) out.push([m[0], m[1] ? "co" : m[2] ? "st" : m[3] ? "nu" : m[4] ? (PY_KW.has(m[0]) ? "k" : null) : null]);
    return out;
  }
  /** code 요소 → 표시 줄 [{n, focus, gap, runs:[[글자, 역할]]}] — start·focus·show(구간 발췌, 사이는 ⋮) */
  function codeLines(el) {
    const src = String(el.text == null ? "" : el.text);
    const toks = el.lang === "python" ? hlPython(src) : hlSQL(src);
    const lines = [[]];
    for (const [v, role] of toks) {
      v.split("\n").forEach((p, i) => { if (i) lines.push([]); if (p) lines[lines.length - 1].push([p, role]); });
    }
    const start = parseInt(el.start || 1, 10) || 1, focus = new Set((el.focus || []).map(Number)), show = el.show && el.show.length ? el.show : null;
    const out = []; let gap = false;
    lines.forEach((ln, i) => {
      const n = start + i;
      if (show && !show.some(([a, b]) => n >= a && n <= b)) {
        if (!gap) { out.push({ n: "⋮", focus: false, gap: true, runs: [] }); gap = true; }
        return;
      }
      gap = false;
      out.push({ n: String(n), focus: focus.has(n), gap: false, runs: ln });
    });
    return out;
  }
  const CODE_GUTTER_W = 48, CODE_PAD_Y = 12;
  function codeStyle(role) {
    const cs = (T && T.codeStyle) || {};
    return cs[role || "ink"] || cs.ink || ["code-ink", false, false];
  }

  // ---------- plan 강조 ----------
  const HL_ROLE = { warn: ["primary-container", "primary"], ok: ["lab-container", "lab"] };
  function planRuns(line) {
    const rx = /\[\[(?:(warn|ok):)?(.+?)\]\]/g; const out = []; let pos = 0, m;
    while ((m = rx.exec(line))) {
      if (m.index > pos) out.push([line.slice(pos, m.index), null]);
      out.push([m[2], m[1] || "warn"]);
      pos = rx.lastIndex;
    }
    if (pos < line.length) out.push([line.slice(pos), null]);
    return out;
  }

  // ---------- 표 격자 (common.py table_grid 와 같은 규칙) ----------
  const NUM = /^[\s*+\-]?[\d,.\s%:]*\d[\d,.\s%KMG]*$/;
  function tableGrid(el) {
    const isPlan = el.type === "plan-table";
    let cols, n, tw, cw = 0, body = [];
    if (isPlan) {
      cols = el.columns || []; body = el.rows || []; n = body.length + 1;
      const hasNote = body.some((r) => r.note);
      cw = hasNote ? (el.calloutW || 0) : 0;
      tw = el.w - (cw ? cw + 24 : 0);
    } else {
      const rows = el.rows || []; cols = rows[0] || []; n = rows.length; tw = el.w;
    }
    const nc = Math.max(1, cols.length);
    let ratios = (el.colW && el.colW.length ? el.colW.slice() : []);
    while (ratios.length < nc) ratios.push(1);
    ratios = ratios.slice(0, nc);
    const tot = ratios.reduce((a, b) => a + b, 0) || 1;
    const colW = ratios.map((r) => (tw * r) / tot);
    const rowH = Array.from({ length: n }, () => el.h / Math.max(1, n));
    const headFill = el.headFill || "surface-container-high", headColor = el.headColor || "on-surface";
    const fonts = el.colFont || [], aligns = el.align || [];
    const cells = [];
    if (isPlan) {
      const op = el.opCol == null ? 1 : el.opCol;
      const auto = [];
      for (let j = 0; j < nc; j++) {
        const vals = body.map((r) => (r.cells && j < r.cells.length ? String(r.cells[j]) : ""));
        auto.push(j !== op && vals.some((v) => v.trim()) && vals.every((v) => !v.trim() || NUM.test(v)) ? "right" : "left");
      }
      cells.push(cols.map((c, j) => ({ text: String(c), fill: headFill, color: headColor, bold: true, font: "body", align: aligns[j] || auto[j] })));
      for (const r of body) {
        const rc = (r.cells || []).slice(); while (rc.length < nc) rc.push("");
        const hl = r.hl || {};
        const row = [];
        for (let j = 0; j < nc; j++) {
          let t = String(rc[j]);
          if (j === op) t = "  ".repeat(parseInt(r.depth || 0, 10)) + t;
          const role = hl[j] || hl[String(j)];
          const [fill, col] = HL_ROLE[role] || [null, el.color || "on-surface"];
          row.push({ text: t, fill, color: col, bold: !!role, font: "mono", align: aligns[j] || auto[j] });
        }
        cells.push(row);
      }
    } else {
      (el.rows || []).forEach((r, i) => {
        const rc = r.slice(); while (rc.length < nc) rc.push("");
        const hd = (el.header !== false) && i === 0;
        cells.push(rc.slice(0, nc).map((t, j) => ({
          text: String(t), fill: hd ? headFill : null, color: hd ? headColor : (el.color || "on-surface"), bold: hd,
          align: aligns[j] || "left", font: hd ? "body" : (fonts[j] || "body"),
        })));
      });
    }
    const callouts = [];
    if (isPlan && cw) {
      const size = el.size || 15;
      body.forEach((r, i) => {
        if (!r.note) return;
        const roles = Object.values(r.hl || {});
        const role = roles.includes("warn") ? "warn" : roles.includes("ok") ? "ok" : null;
        let [fill, col] = HL_ROLE[role] || ["surface-container", "on-surface-variant"];
        if (role && T && T.colors["on-" + fill]) col = "on-" + fill;
        const lines = String(r.note).split("\n").length;
        const bh = Math.max(rowH[0] - 8, lines * size * 1.5 + 12);
        const cy = el.y + rowH[0] * (i + 1) + rowH[0] / 2;
        callouts.push({ row: i + 1, text: r.note, fill, color: col, line: role ? HL_ROLE[role][1] : "outline-variant",
          x: el.x + tw + 24, y: cy - bh / 2, w: cw, h: bh, cy, tx: el.x + tw });
      });
    }
    return { x: el.x, y: el.y, tw, colW, rowH, cells, rule: el.rule || "surface-container-high", size: el.size || 16, callouts };
  }

  function bulletRows(el) {
    const gap = el.gap == null ? 14 : el.gap, sub = el.subGap == null ? 6 : el.subGap, rows = [];
    for (let it of el.items || []) {
      if (typeof it === "string") it = { text: it };
      const subs = it.sub || [];
      rows.push([it.text || "", 0, subs.length ? sub : gap]);
      subs.forEach((s, k) => rows.push([s, 1, k < subs.length - 1 ? sub : gap]));
    }
    return rows;
  }

  // ---------- HTML 조각 ----------
  function spanRuns(text, page, base, bold) {
    return runs(text, page).map(([t, st]) => {
      if (!t) return "";
      const c = st.color ? color(st.color) : base;
      const b = st.bold !== undefined ? st.bold : bold;
      return `<span style="color:${c};font-weight:${b ? 700 : 400}">${esc(t)}</span>`;
    }).join("");
  }
  function padOf(el, d) {
    let p = el.pad == null ? (d || 0) : el.pad;
    if (typeof p === "number") return [p, p, p, p];
    p = p.slice(); while (p.length < 4) p.push(0);
    return p;
  }
  const JUST = { top: "flex-start", middle: "center", bottom: "flex-end" };
  const HJUST = { left: "flex-start", center: "center", right: "flex-end" };

  /** 글자 단락들(한 줄 = 한 단락) */
  function textLines(el, page, o) {
    const size = +el.size || 20, lh = +(el.lineHeight || o.lh), L = size * lh;
    const base = color(el.color || "on-surface"), bold = el.bold !== undefined ? !!el.bold : !!o.bold;
    const align = el.align || o.align, wrap = el.wrap !== undefined ? el.wrap : o.wrap;
    const sh = shift(el.font, size, lh);
    return String(el.text == null ? "" : el.text).split("\n").map((line) => {
      const inner = spanRuns(line, page, base, bold) || "&#8203;";
      return wrap
        ? `<div class="rs-p" style="position:relative;top:${sh}px;line-height:${L}px;height:auto;min-height:${L}px;text-align:${align}">${inner}</div>`
        : `<div class="rs-p rs-nw" style="position:relative;top:${sh}px;line-height:${L}px;height:${L}px;justify-content:${HJUST[align] || "flex-start"}">${inner}</div>`;
    }).join("");
  }

  function boxStyle(el, kind) {
    const w = el.w, h = el.h;
    let r = 0;
    if (kind === "ellipse") r = "50%";
    else if (kind === "pill") r = Math.min(w, h) / 2 + "px";
    else r = radius(el.radius, w, h) + "px";
    let s = `border-radius:${r};`;
    if (el.fill) s += `background:${color(el.fill)};`;
    if (el.stroke) s += `box-shadow:inset 0 0 0 ${el.strokeWidth || 1}px ${color(el.stroke)};`;
    return s;
  }

  function elBox(el, page) {
    const t = el.type, [pt, pr, pb, pl] = padOf(el);
    const shape = t === "text" ? "rect" : t;
    const isShape = t !== "text" || el.fill;
    const valign = el.valign || (t === "text" ? "top" : "middle");
    const o = { lh: (t === "text" ? 1.4 : 1.2), bold: t === "pill", align: t === "pill" || t === "ellipse" ? "center" : "left", wrap: t === "text" || t === "rect" };
    const hasText = el.text != null && String(el.text) !== "";
    return `<div class="rs-box" style="${isShape ? boxStyle(el, shape) : ""}padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:${JUST[valign]};font-family:${font(el.font)};font-size:${+el.size || 20}px">${hasText ? textLines(el, page, o) : ""}</div>`;
  }

  function elImage(el) {
    return `<img class="rs-img" src="${esc(root.RENDER_BASE || "/")}${esc(el.src)}" alt="" draggable="false">`;
  }

  /** 선·화살표: 요소 상자(x,y,w,h) 기준 SVG. 화살 머리 = 선 두께 × 5 (PPT 'lg') */
  function lineSvg(el, ox, oy) {
    const x1 = el.x1 - ox, y1 = el.y1 - oy, x2 = el.x2 - ox, y2 = el.y2 - oy;
    const w = +el.width || 2, c = color(el.color || "on-surface");
    const head = el.head || (el.type === "arrow" ? "end" : "none");
    const hl = w * 5, hw = w * 5;
    const len = Math.hypot(x2 - x1, y2 - y1) || 1, ux = (x2 - x1) / len, uy = (y2 - y1) / len;
    let ax = x1, ay = y1, bx = x2, by = y2, polys = "";
    const tri = (tx, ty, dx, dy) => {
      const bx0 = tx - dx * hl, by0 = ty - dy * hl, nx = -dy * hw / 2, ny = dx * hw / 2;
      return `<polygon points="${tx},${ty} ${bx0 + nx},${by0 + ny} ${bx0 - nx},${by0 - ny}" fill="${c}"/>`;
    };
    if (head === "end" || head === "both") { bx = x2 - ux * hl * 0.9; by = y2 - uy * hl * 0.9; polys += tri(x2, y2, ux, uy); }
    if (head === "start" || head === "both") { ax = x1 + ux * hl * 0.9; ay = y1 + uy * hl * 0.9; polys += tri(x1, y1, -ux, -uy); }
    const dash = el.dash === "dot" ? `stroke-dasharray="${w} ${w}"` : el.dash && el.dash !== "solid" ? `stroke-dasharray="${w * 4} ${w * 3}"` : "";
    return `<line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="${c}" stroke-width="${w}" ${dash}/>${polys}`;
  }
  function elLine(el) {
    const m = 20; // 화살 머리가 상자 밖으로 나가도 보이게
    return `<svg class="rs-svg" style="left:${-m}px;top:${-m}px" width="${Math.max(1, el.w) + 2 * m}" height="${Math.max(1, el.h) + 2 * m}">${lineSvg(el, el.x - m, el.y - m)}</svg>`;
  }

  /** 곡선(꺾은선 근사): points = 요소 상자 기준 [[x,y],…], head = end/none — 화살 머리는 마지막 선분 방향 */
  function elCurve(el) {
    const m = 20, pts = el.points || [], w = +el.width || 2, c = color(el.color || "on-surface");
    const dash = el.dash === "dot" ? `stroke-dasharray="${w} ${w}"` : el.dash && el.dash !== "solid" ? `stroke-dasharray="${w * 4} ${w * 3}"` : "";
    if (pts.length < 2) return "";
    const P = pts.map(([x, y]) => [x + m, y + m]);
    let polys = "";
    if ((el.head || "end") !== "none") {
      const [ax, ay] = P[P.length - 2], [bx, by] = P[P.length - 1];
      const len = Math.hypot(bx - ax, by - ay) || 1, ux = (bx - ax) / len, uy = (by - ay) / len, hl = w * 5, hw = w * 5;
      const b0x = bx - ux * hl, b0y = by - uy * hl, nx = -uy * hw / 2, ny = ux * hw / 2;
      polys = `<polygon points="${bx},${by} ${b0x + nx},${b0y + ny} ${b0x - nx},${b0y - ny}" fill="${c}"/>`;
      P[P.length - 1] = [bx - ux * hl * 0.9, by - uy * hl * 0.9];
    }
    return `<svg class="rs-svg" style="left:${-m}px;top:${-m}px" width="${Math.max(1, el.w) + 2 * m}" height="${Math.max(1, el.h) + 2 * m}">` +
      `<polyline points="${P.map((q) => q.join(",")).join(" ")}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linejoin="round" ${dash}/>${polys}</svg>`;
  }

  function elTable(el, page) {
    const g = tableGrid(el);
    let html = "", y = 0;
    const size = g.size;
    g.cells.forEach((row, i) => {
      let x = 0;
      const isHead = i === 0 && (el.type === "plan-table" || el.header !== false);
      row.forEach((c, j) => {
        const w = g.colW[j], h = g.rowH[i];
        const bb = isHead ? "" : `border-bottom:1px solid ${color(g.rule)};`;
        html += `<div class="rs-cell" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;${c.fill ? `background:${color(c.fill)};` : ""}${bb}justify-content:${HJUST[c.align] || "flex-start"};font-family:${font(c.font)};font-size:${size}px;line-height:${size * 1.4}px;text-align:${c.align}">` +
          `<div class="rs-ct" style="position:relative;top:${shift(c.font, size, 1.4)}px">${spanRuns(c.text, page, color(c.color), c.bold) || "&#8203;"}</div></div>`;
        x += w;
      });
      y += g.rowH[i];
    });
    for (const co of g.callouts) {
      const lx = co.tx + 4 - el.x, ly = co.cy - el.y;
      html += `<div class="rs-cell" style="left:${lx}px;top:${ly - 1}px;width:${co.x - co.tx - 4}px;height:2px;background:${color(co.line)}"></div>`;
      const box = { type: "text", x: 0, y: 0, w: co.w, h: co.h, text: co.text, size, lineHeight: 1.5, fill: co.fill, color: co.color, radius: "r-s", pad: [6, 14, 6, 14], valign: "middle" };
      html += `<div class="rs-cell" style="left:${co.x - el.x}px;top:${co.y - el.y}px;width:${co.w}px;height:${co.h}px;display:block">${elBox(box, page)}</div>`;
    }
    return html;
  }

  /** plan: 실행계획 원문(고정폭) + [[강조]] — 배경·글자색·굵게만(폭 불변) */
  function elPlan(el) {
    const size = +el.size || 14, lh = +(el.lineHeight || 1.5), L = size * lh;
    const [pt, pr, pb, pl] = padOf(el, [16, 18, 16, 18]);
    const base = color(el.color || "on-surface");
    const body = String(el.text || "").split("\n").map((ln) => planRuns(ln).map(([t, role]) => {
      if (!role) return `<span style="color:${base}">${esc(t)}</span>`;
      const [bg, fg] = HL_ROLE[role] || HL_ROLE.warn;
      return `<span style="background:${color(bg)};color:${color(fg)};font-weight:700">${esc(t)}</span>`;
    }).join("")).map((h) => `<div class="rs-p rs-pre" style="position:relative;top:${shift("mono", size, lh)}px;line-height:${L}px;height:${L}px">${h || "&#8203;"}</div>`).join("");
    return `<div class="rs-box" style="${boxStyle({ ...el, fill: el.fill || "surface-container", radius: el.radius == null ? "r-m" : el.radius }, "rect")}padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:flex-start;font-family:${font("mono")};font-size:${size}px">${body}</div>`;
  }

  /** code: DBeaver 라이트 — 줄 번호 여백 + 강조 줄 면 + 역할별 색·굵게·기울임 (export_pptx.do_code 와 같은 배치) */
  function elCode(el) {
    const size = +el.size || 15, lh = +(el.lineHeight || 1.6), L = size * lh, gw = el.gutterW || CODE_GUTTER_W;
    const r = radius(el.radius == null ? "r-m" : el.radius, el.w, el.h);
    const lines = codeLines(el);
    let html = `<div class="rs-code" style="border-radius:${r}px;background:${color("code-bg")};box-shadow:inset 0 0 0 1px ${color("surface-container-high")};font-family:${font("mono")};font-size:${size}px">`;
    html += `<div class="rs-abs" style="left:0;top:0;width:${gw}px;height:100%;background:${color("code-gutter-bg")}"></div>`;
    const sh = shift("mono", size, lh);
    lines.forEach((ln, i) => {
      const top = CODE_PAD_Y + i * L;
      if (ln.focus) html += `<div class="rs-abs" style="left:${gw}px;top:${top}px;right:0;height:${L}px;background:${color("code-focus")}"></div>`;
      const gc = ln.focus ? color("on-surface") : color("code-gutter");
      html += `<div class="rs-abs rs-pre" style="left:0;top:${top + sh}px;width:${gw - 12}px;height:${L}px;line-height:${L}px;text-align:right;color:${gc};font-weight:${ln.focus ? 700 : 400}">${esc(ln.n)}</div>`;
      const body = ln.runs.map(([t, role]) => {
        const [c, b, it] = codeStyle(role);
        return `<span style="color:${color(c)};font-weight:${b ? 700 : 400};font-style:${it ? "italic" : "normal"}">${esc(t)}</span>`;
      }).join("");
      html += `<div class="rs-abs rs-pre" style="left:${gw + 14}px;top:${top + sh}px;right:0;height:${L}px;line-height:${L}px">${body || "&#8203;"}</div>`;
    });
    return html + "</div>";
  }

  function elBullets(el, page) {
    const size = +el.size || 20, sub = +el.subSize || 17, lh = +(el.lineHeight || 1.55);
    const [pt, pr, pb, pl] = padOf(el);
    const rows = bulletRows(el).map(([t, lvl, after]) => {
      const sz = lvl ? sub : size, marL = lvl ? 48 : 28, hang = lvl ? 20 : 28;
      const base = color(lvl ? el.subColor || "on-surface-variant" : el.color || "on-surface");
      const bc = color(lvl ? el.subColor || "on-surface-variant" : el.dot || "primary");
      const bu = `<span class="rs-bu" style="width:${hang}px;font-size:${lvl ? 100 : 60}%;color:${bc}">${lvl ? "–" : "●"}</span>`;
      return `<div class="rs-p" style="position:relative;top:${shift("body", sz, lh)}px;font-size:${sz}px;line-height:${sz * lh}px;padding-left:${marL}px;text-indent:${-hang}px;padding-bottom:${after}px">${bu}${spanRuns(t, page, base, false)}</div>`;
    }).join("");
    return `<div class="rs-box" style="padding:${pt}px ${pr}px ${pb}px ${pl}px;justify-content:${JUST[el.valign || "top"]};font-family:${font("body")}">${rows}</div>`;
  }

  function lineBox(el) {
    // 선 요소의 x,y,w,h 를 끝점에서 다시 계산(편집 중 어긋남 방지)
    if (el.x1 == null) return el;
    return { ...el, x: Math.min(el.x1, el.x2), y: Math.min(el.y1, el.y2), w: Math.abs(el.x2 - el.x1), h: Math.abs(el.y2 - el.y1) };
  }

  function renderElement(el0, page) {
    const el = (el0.type === "line" || el0.type === "arrow") ? lineBox(el0) : el0;
    let inner = "";
    switch (el.type) {
      case "rect": case "ellipse": case "pill": case "text": inner = elBox(el, page); break;
      case "image": inner = elImage(el); break;
      case "line": case "arrow": inner = elLine(el); break;
      case "curve": inner = elCurve(el); break;
      case "table": case "plan-table": inner = elTable(el, page); break;
      case "code": inner = elCode(el); break;
      case "plan": inner = elPlan(el); break;
      case "bullets": inner = elBullets(el, page); break;
      default: inner = `<div class="rs-box" style="outline:1px dashed red">? ${esc(el.type)}</div>`;
    }
    return `<div class="rs-el" data-id="${esc(el.id)}" data-type="${esc(el.type)}" style="left:${el.x}px;top:${el.y}px;width:${el.w}px;height:${el.h}px">${inner}</div>`;
  }

  function sorted(els) {
    return (els || []).map((e, i) => [e, i]).sort((a, b) => ((a[0].z || 0) - (b[0].z || 0)) || (a[1] - b[1])).map((x) => x[0]);
  }

  /** 슬라이드 → HTML 문자열 (1280×720, 축소는 호출자가 transform 으로) */
  function renderSlide(slide, page) {
    const bg = color(slide.bg || "surface");
    return `<div class="rs-slide" style="background:${bg}">${sorted(slide.elements).map((e) => renderElement(e, page)).join("")}</div>`;
  }

  /** 렌더러용 CSS (토큰 → CSS 변수 포함) */
  function css() {
    const vars = T ? Object.keys(T.colors).map((k) => `--${k}:${color(k)};`).join("") : "";
    return `:root{${vars}}
.rs-slide{position:relative;width:1280px;height:720px;overflow:hidden;font-family:${font("body")};color:${color("on-surface")};-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;font-kerning:none;font-variant-ligatures:none}
.rs-el{position:absolute;box-sizing:border-box}
.rs-box{position:absolute;inset:0;box-sizing:border-box;display:flex;flex-direction:column;overflow:visible}
.rs-p{white-space:pre-wrap;word-break:keep-all;overflow-wrap:break-word;margin:0;flex:none}
.rs-nw{display:flex;white-space:pre;align-items:center}
.rs-pre{white-space:pre}
.rs-code{position:absolute;inset:0;overflow:hidden}
.rs-abs{position:absolute;box-sizing:border-box}
.rs-bu{display:inline-block;text-indent:0;line-height:0}
.rs-img{position:absolute;inset:0;width:100%;height:100%;display:block;user-select:none}
.rs-svg{position:absolute;overflow:visible;pointer-events:none}
.rs-cell{position:absolute;box-sizing:border-box;display:flex;align-items:center;padding:0 14px;overflow:visible}
.rs-cell>.rs-ct{white-space:pre-wrap;word-break:keep-all;flex:1}`;
  }

  const api = { setTokens, color, radius, runs, plain, hlSQL, hlPython, codeLines, planRuns, tableGrid, bulletRows, renderElement, renderSlide, css, esc, lineBox };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Render = api;
})(typeof window !== "undefined" ? window : globalThis);
