/* nexa-slide VBA 실행 Worker - 시트 화면(sheet.js)이 VBA 사용자 함수 계산을 여기로 보낸다(NexaVBA.client).
   문서에 든 코드가 화면을 멈추지 못하게 계산을 따로 돌리고, 답이 없으면 화면 쪽이 이 Worker 를 끝낸다.
   메시지: {type: "init", modules} · {type: "call", id, name, args(NexaVBA.pack)} → {id, v} | {id, err: {kind, msg}} */
importScripts("vba.js", "sheetcalc.js");
const state = { c: null }, host = { sheetFn: NexaCalc.sheetFn(NexaVBA, null) };
postMessage({ type: "ready" });  // 화면 쪽 감시는 이때부터
onmessage = (e) => {
  const r = NexaVBA.serve(state, e.data, host);
  if (r) postMessage(r);
};
