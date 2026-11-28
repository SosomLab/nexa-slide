// nexa-doc.js - 문서 뼈대(공용) - 자동 저장의 상태기계. 세 편집기에 따로 있던 save()·scheduleSave() 를 하나로(PG-109 · PG-011).
//   세 편집기가 같이 쓴다(시트·슬라이드는 작업 저장·구조 변경·action 을 send 훅으로).
//   NexaDoc.saver(o) → { schedule(), save(force), cancel() }
//     o.state      S - deck · version · savedJson · dirty · saving · conflict 를 읽고 쓴다
//     o.api · setStatus · banner · toast            화면의 공용 도구(nexa-shell)
//     o.id()       문서 id · o.json() 지금 문서의 JSON 글
//     o.delay      자동 저장까지의 시간(ms, 기본 700) · o.onlyDirty 고친 것이 있을 때만 예약(페이지)
//     o.onMerged(r, body, now)   서버가 다른 저장과 합쳤을 때 - 화면에 반영(S.savedJson·S.deck 은 여기서 정한 뒤에 부른다). 선택·실행 취소 봉인은 화면 몫
//     o.beforeMerged(now)        합친 결과를 넣기 전(실행 취소 봉인 · 선택 기억) - 돌려준 값이 onMerged 의 넷째 인자
//     o.conflictText(r)          409 배너 글 · o.errorMs 저장 실패 알림 시간
//     o.guard()                  true 를 돌려주면 저장하지 않는다(미리 보기 등 - 상태 표시는 훅이 한다)
//     o.send(body, force)        서버에 보내는 방법을 바꾼다(작업 저장 POST /api/ops · 구조 작업 __struct · action 쿼리) → 응답. 없으면 병합 PUT
//     o.savedBody                true 면 보통 저장 뒤의 저장본 = 보낸 글 그대로(시트 - 계산값이 저장 사이에 바뀌어도 다음 저장이 잡는다)
//     o.mergedDeck(deck)         합친 문서를 화면에 넣기 전 손질(정규화) → 문서
//     o.onSaved(r)               보통 저장이 끝난 뒤(검사 예약 등)
//     o.stale(id)                저장하는 사이 다른 문서로 넘어갔는가(id = 보낼 때의 o.id()) - 그러면 응답을 버린다(슬라이드: 한 창에서 덱을 바꾼다)
//   save(force, extra) 의 extra 는 send 훅에 그대로 넘긴다(복원 등의 action 쿼리)
//   규칙(세 화면 공통): 충돌 중에는 저장하지 않는다(force 제외) · 저장 중이면 다시 예약 · 바뀐 것이 없으면 보내지 않는다 ·
//     병합 저장(PUT ?base=<내가 읽은 판>&merge=1) · 저장하는 사이 더 고친 것은 저장본에 넣지 않고 다시 예약한다
(function (root) {
  "use strict";
  function saver(o) {
    const S = o.state, delay = o.delay || 700;
    let timer = 0;
    const cancel = () => { clearTimeout(timer); timer = 0; };
    function schedule() { cancel(); if (!o.onlyDirty || S.dirty) timer = setTimeout(save, delay); }
    async function save(force, extra) {
      force = force === true;  // 타이머가 넘기는 인자 등은 무시
      if (o.guard && o.guard()) return;
      if (!S.deck || (S.conflict && !force)) return;
      if (S.saving) { schedule(); return; }
      const body = o.json(), sid = o.id();
      if (!force && body === S.savedJson) { S.dirty = false; o.setStatus("saved", "저장됨"); return; }
      S.saving = true; o.setStatus("dirty", "저장 중…");
      const r = o.send ? await o.send(body, force, extra)
        : await o.api("PUT", `/api/deck/${encodeURIComponent(o.id())}?base=${encodeURIComponent(S.version || "")}${force ? "&force=1" : "&merge=1"}`, JSON.parse(body));
      S.saving = false; S.savedAt = Date.now();  // 저장이 끝난 때 - 그 직전에 받은 판 정보는 낡았다(stillChanged)
      if (o.stale ? o.stale(sid) : o.id() !== sid) return;  // 저장하는 사이 다른 문서로 넘어갔다 - 이 응답(앞 문서의 판·저장본)을 지금 문서에 넣지 않는다
      if (r.ok) {
        S.version = r.data.version; S.conflict = false; o.banner(false);
        if (r.data.merged && r.data.deck) {  // 그 사이 다른 저장과 합쳐졌다 - 결과(+ 저장하는 사이 더 고친 것)를 화면에
          const now = o.json(), keep = o.beforeMerged ? o.beforeMerged(now) : undefined;
          S.savedJson = JSON.stringify(r.data.deck);
          const d = root.NexaMerge.afterSave(body, now, r.data.deck); S.deck = o.mergedDeck ? o.mergedDeck(d) : d;
          if (o.onMerged) o.onMerged(r, body, now, keep);
        } else {
          const same = !o.savedBody && o.json() === body;  // 저장하는 사이 더 고치지 않았다 - 지금 문서가 곧 저장본(키 순서까지 같게)
          if (r.data.updated) S.deck.updated = r.data.updated;
          if (same) S.savedJson = o.json(); else { const d = JSON.parse(body); if (r.data.updated) d.updated = r.data.updated; S.savedJson = JSON.stringify(d); }
          if (o.onSaved) o.onSaved(r);
        }
        S.dirty = o.json() !== S.savedJson;
        o.setStatus(S.dirty ? "dirty" : "saved", S.dirty ? "저장 대기" : "저장됨");
        if (S.dirty) schedule();
      } else if (r.status === 409) {
        S.conflict = true; o.setStatus("conflict", "충돌");
        o.banner(true, o.conflictText ? o.conflictText(r) : "저장하려는 사이 문서가 밖에서 바뀌었고 자동으로 합칠 수 없습니다. 어느 쪽을 남길까요?");
      } else { o.setStatus("error", "저장 실패"); o.toast("저장 실패: " + ((r.data && r.data.error) || r.status), o.errorMs || 6000); }
    }
    return { schedule, save, cancel };
  }
  /** 밖에서 바뀐 문서를 다시 읽기 직전의 확인(세 편집기 공통 기준) - 받아 둔 판 정보는 낡았을 수 있다: 판을 받은 뒤 처리하기까지의 사이에 내 저장이 끝나면
   *  "판이 다르다 · 저장 중 아님"이 되어 쓸데없이 다시 읽고, 그때 문서가 지워졌으면 404 가 났다. 요청을 더 보내지 않고 판단한다:
   *  저장 중·고치는 중이 아니고, 내 저장이 끝난 지 QUIET ms 가 지났을 때만 true. 방금 저장했으면 later()(다시 확인)를 QUIET 뒤로 미룬다 - 진짜 밖의 변경이면 그때 잡힌다 */
  const QUIET = 1500;
  function stillChanged(S, later, skip) {
    if (S.saving || S.dirty || (skip && skip())) return false;
    const left = QUIET - (Date.now() - (S.savedAt || 0));
    if (left > 0) { if (later) setTimeout(later, left + 50); return false; }
    return true;
  }

  /** 밖의 변경 따라가기(세 편집기 공통 기준) - 판(/api/version)을 보고 "고치는 중이면 저장해 서버에서 합치고, 아니면 다시 읽는다".
   *  판은 폴링(poll)과 실시간 연결(SSE 의 onVersion → apply) 두 길로 오고 둘 다 apply 를 거친다. 처리 중에 온 것은 마지막 하나만 남겨 이어서 한다.
   *  o.state(S: version · saving · dirty · conflict · savedAt) · o.api · o.id() · o.ready()(문서를 열었는가) · o.live()(NexaLive | null - 건강하면 폴링은 15초 안전망만)
   *  o.before(v)   판을 보기 전에 하는 화면 고유의 일(세션 표시 · 요청 · 작업 공간 · 원장) - 기다린다
   *  o.gone(v)     지워진 문서로 볼 추가 조건(슬라이드: 지우는 중인 덱). 기본 = 판이 없거나 "0" · 목록(deckIds)에 없음   · o.onGone(v)
   *  o.editing()   글·셀을 치는 중인가(그러면 저장도 다시 읽기도 미룬다) · o.save() 지금 저장(예약을 거두고) · o.reload(v) 다시 읽기 · o.after(v, gone)
   *  → { poll(force), apply(v), start(ms), stop() } */
  function follower(o) {
    const S = o.state; let pollAt = 0, applying = false, pending = null, timer = 0;
    const ready = () => (o.ready ? o.ready() : !!S.deck);
    const isGone = (v) => v.deck == null || String(v.deck) === "0" || (Array.isArray(v.deckIds) && !v.deckIds.includes(o.id())) || !!(o.gone && o.gone(v));
    async function apply(v) {
      if (!v || !ready()) return;
      if (applying) { pending = v; return; }
      applying = true;
      try {
        if (o.before) await o.before(v);
        const gone = isGone(v);
        if (gone) { if (o.onGone) o.onGone(v); }
        else if (v.deck !== S.version && !S.saving) {
          const editing = !!(o.editing && o.editing());
          // 고치는 중에 밖에서 바뀌었다 - 배너로 고르게 하지 않고, 내 저장이 서버에서 합쳐지게 바로 저장한다(치는 중이면 입력이 끝난 뒤의 저장 때)
          if (S.dirty || editing) { if (S.dirty && !editing && !S.conflict) await o.save(); }
          else if (stillChanged(S, () => poll(true), () => isGone(v))) await o.reload(v);  // 받아 둔 v 는 낡았을 수 있다 - 방금 저장했으면 잠시 뒤 다시 확인
        }
        if (o.after) await o.after(v, gone);
      } finally {
        applying = false;
        if (pending) { const n = pending; pending = null; await apply(n); }
      }
    }
    async function poll(force) {
      if (!ready()) return;
      const L = o.live ? o.live() : null;
      if (force !== true && L && L.healthy() && Date.now() - pollAt < 15000) return;
      pollAt = Date.now();
      try {
        const r = await o.api("GET", `/api/version/${encodeURIComponent(o.id())}`);
        if (!r || !r.ok) return;
        await apply(r.data);
      } catch (e) { if (o.onError) o.onError(e); }
    }
    return { poll, apply, start(ms) { clearInterval(timer); timer = setInterval(() => poll(), ms || 2000); return timer; }, stop() { clearInterval(timer); timer = 0; } };
  }

  /** 실행 취소·다시 실행 기록(세 편집기 공통 기준) - 기록은 S.undo · S.redo 에 그대로 둔다(다른 모듈·시험이 길이를 본다).
   *  항목 = 바꾸기 직전의 문서 JSON 문자열, 또는 {b: 그 JSON, sel?: 그때의 선택, a?: 그 편집 뒤의 문서(봉인)}.
   *  봉인(seal) = 남의 변경(다른 창·AI·병합 저장)을 받기 직전에 항목마다 "그 편집 뒤의 문서"를 붙여 둔다 - 그러면 되돌릴 때 문서를 통째로 옛 모습으로
   *  바꾸지 않고 내 편집만 거꾸로 얹는다(Ctrl+Z 가 남의 변경을 지우지 않는다). 다시 실행 기록은 비운다.
   *  o.state(S) · o.json() · o.max(기본 150) · o.merge3(기본 NexaMerge.merge3)
   *  o.selection()     있으면 선택을 같이 적고 되돌릴 때 돌려준다(페이지) · o.join(why, last, dt) → true 면 앞 기록에 묶는다(이어 친 글)
   *  o.beforePush(why) 기록 직전(AI 처리 중 경고 등) · o.apply(deck, sel, dir) 되돌린 문서를 화면에(dir = "undo" | "redo") · o.onChange() 단추 켜짐·꺼짐
   *  → { push(why, before), undo(), redo(), seal(now), drop(), reset(), can() } */
  function history(o) {
    const S = o.state, max = o.max || 150; let last = null;
    const jsonOf = (e) => (typeof e === "string" ? e : e.b);
    const entry = (json) => (o.selection ? { b: json, sel: o.selection() } : json);
    const changed = () => { if (o.onChange) o.onChange(); };
    /** 바꾸기 직전에 부른다. before = 미리 잡아 둔 직전 문서(끌기·글 편집 - 바뀐 것을 안 뒤에 넣는다) */
    function push(why, before) {
      const now = Date.now();
      if (before === undefined && o.beforePush) o.beforePush(why);
      const join = before === undefined && !!(o.join && last && o.join(why, last.why, now - last.at));
      last = { why, at: now };
      if (join) return false;
      S.undo.push(before === undefined ? entry(o.json()) : before); if (S.undo.length > max) S.undo.shift();
      S.redo.length = 0; changed(); return true;
    }
    function step(from, to, dir) {
      if (!from.length) return false;
      const now = o.json(), e = from.pop(); to.push(entry(now)); last = null;
      const m3 = o.merge3 || (root.NexaMerge && root.NexaMerge.merge3);
      const deck = typeof e === "object" && e.a !== undefined ? m3(JSON.parse(e.a), JSON.parse(e.b), JSON.parse(now), "ours").merged : JSON.parse(jsonOf(e));
      o.apply(deck, typeof e === "object" ? e.sel : undefined, dir); changed(); return true;
    }
    function seal(now) {
      for (let k = 0; k < S.undo.length; k++) {
        const e = S.undo[k]; if (typeof e === "object" && e.a !== undefined) continue;
        const a = k + 1 < S.undo.length ? jsonOf(S.undo[k + 1]) : now;
        S.undo[k] = typeof e === "string" ? { b: e, a } : { ...e, a };
      }
      S.redo.length = 0; last = null; changed();
    }
    return {
      push, seal, undo: () => step(S.undo, S.redo, "undo"), redo: () => step(S.redo, S.undo, "redo"),
      drop() { const e = S.undo.pop(); last = null; changed(); return e; },  // 방금 넣은 기록을 없던 일로(바뀐 것이 없었다)
      reset() { S.undo.length = 0; S.redo.length = 0; last = null; changed(); },
      can: () => ({ undo: S.undo.length > 0, redo: S.redo.length > 0 }),
    };
  }

  root.NexaDoc = { saver, stillChanged, follower, history };
  if (typeof module !== "undefined" && module.exports) module.exports = root.NexaDoc;
})(typeof window !== "undefined" ? window : globalThis);
