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
      S.saving = false;
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
  root.NexaDoc = { saver };
  if (typeof module !== "undefined" && module.exports) module.exports = root.NexaDoc;
})(typeof window !== "undefined" ? window : globalThis);
