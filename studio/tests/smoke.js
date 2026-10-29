// 헤드리스 Chrome 클릭 스모크 - CDP(원격 디버깅)로 페이지를 열고 단계(JS 식)를 차례로 실행하며 콘솔 오류·예외를 모은다.
//   node smoke.js <시나리오.json> [<시나리오.json> ...]   시나리오 = {base, login?: {id, password}, pages: [{url, wait?, steps: [{name, js, wait?}]}]}
//   js 는 페이지 안에서 평가되는 식(await 가능) - 결과가 false 면 FAIL. 콘솔 error/예외가 하나라도 있으면 그 페이지 FAIL.
//   js 안에서 until(() => 조건, 최대ms=5000) 을 쓸 수 있다 - 조건이 참이 될 때까지 50ms 마다 다시 본다(고정 setTimeout 대신, 참이 되면 바로 넘어간다).
//   시나리오가 여럿이면 Chrome 은 한 번만 띄우고 시나리오마다 새 브라우저 컨텍스트(저장소·쿠키 분리)에서 돈다.
//   각 시나리오 뒤에 "## RESULT <파일 이름> OK|FAIL <실패 수>" 줄을 찍는다. 종료 코드는 하나라도 실패면 1.
//   page.wait 은 진입 뒤 대기의 상한이다 - 네트워크가 조용해지면(진행 중 요청 0 이 250ms) 그보다 일찍 넘어간다.
const fs = require("fs"), path = require("path"), { spawn } = require("child_process");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333 + Math.floor(Math.random() * 2000);  // 실행마다 다른 디버그 포트 - 앞선 실행의 Chrome 이 남아 있으면 그 창에 붙어 엉뚱한 상태로 시작하던 것
const FILES = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UNTIL = "const until = async (f, ms = 5000) => { const t0 = Date.now(); for (;;) { let v; try { v = await f(); } catch (e) { v = false; } if (v) return v; if (Date.now() - t0 > ms) return false; await new Promise((r) => setTimeout(r, 50)); } };";

async function main() {
  const prof = fs.mkdtempSync(path.join(require("os").tmpdir(), "nx-smoke-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, "--window-size=1400,1000", "about:blank"], { stdio: "ignore" });
  let total = 0;
  try {
    let ver;
    for (let i = 0; i < 100 && !ver; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); } catch (e) { /* 아직 안 떴다 */ } if (!ver) await sleep(200); }
    if (!ver) throw new Error("Chrome 디버그 포트가 열리지 않았다");
    const ws = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let id = 0; const pending = {}; const handlers = {};
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; return; }
      if (d.sessionId && handlers[d.sessionId]) handlers[d.sessionId](d);
    };
    const send = (method, params = {}, sessionId) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params, ...(sessionId ? { sessionId } : {}) })); });
    for (const f of FILES) {
      const t0 = Date.now(); const fails = await runScenario(f, send, handlers);
      total += fails;
      console.log(`\n## RESULT ${path.basename(f)} ${fails ? "FAIL" : "OK"} ${fails} ${((Date.now() - t0) / 1000).toFixed(1)}초`);
    }
    ws.close();
  } finally {
    // Windows 는 자식 프로세스까지 끝낸다(chrome.kill 만으로는 브라우저 프로세스가 남아 다음 실행을 느리게 하거나 포트를 쥔다)
    if (process.platform === "win32") { try { require("child_process").spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { stdio: "ignore" }); } catch (e) { /* 무시 */ } }
    chrome.kill();
  }
  console.log(total ? `\n실패 ${total}` : "\n전부 통과");
  process.exit(total ? 1 : 0);
}

async function runScenario(file, bsend, handlers) {
  const sc = JSON.parse(fs.readFileSync(file, "utf8"));
  let fails = 0;
  const ctx = (await bsend("Target.createBrowserContext", { disposeOnDetach: true })).result.browserContextId;
  const tgt = (await bsend("Target.createTarget", { url: "about:blank", browserContextId: ctx, width: 1400, height: 1000 })).result.targetId;
  const sid = (await bsend("Target.attachToTarget", { targetId: tgt, flatten: true })).result.sessionId;
  const send = (method, params = {}) => bsend(method, params, sid);
  const errors = []; const inflight = new Map(); let lastNet = Date.now();
  // 콘솔 오류로 치지 않는 것 - 기본 목록 + 시나리오의 ignoreErrors(정규식 글) - 예: 일부러 틀린 그림 주소
  // fontfile·wsfonts = 이 PC 에 없는 글꼴(Pretendard 등)의 404 - 대체 글꼴로 그려지는 환경 차이라 오류가 아니다(배포 시험이 늘 smoke·editor 실패로 보이던 원인)
  const IGNORE = new RegExp("favicon|net::ERR_ABORTED|api\/engine\/notice|api\/image|api\/fontfile\/|wsfonts" + (sc.ignoreErrors ? "|" + sc.ignoreErrors : ""));
  handlers[sid] = (d) => {
    const p = d.params;
    if (d.method === "Runtime.consoleAPICalled" && (p.type === "error")) errors.push("console.error: " + p.args.map((a) => a.value || a.description || "").join(" "));
    else if (d.method === "Runtime.exceptionThrown") errors.push("exception: " + (p.exceptionDetails.exception?.description || p.exceptionDetails.text));
    else if (d.method === "Log.entryAdded" && p.entry.level === "error" && !IGNORE.test(p.entry.text + " " + (p.entry.url || ""))) errors.push("log: " + p.entry.text + " " + (p.entry.url || ""));
    // 네트워크 조용함 판단 - SSE(EventSource)·스트리밍은 끝나지 않으므로 세지 않는다
    else if (d.method === "Network.requestWillBeSent" && p.type !== "EventSource") { inflight.set(p.requestId, Date.now()); lastNet = Date.now(); }
    else if (d.method === "Network.loadingFinished" || d.method === "Network.loadingFailed") { if (inflight.delete(p.requestId)) lastNet = Date.now(); }
  };
  const evalJs = async (js) => {
    const r = await send("Runtime.evaluate", { expression: `(async () => { ${UNTIL} ${js.includes("return") ? js : "return (" + js + "\n)"}\n})()`, awaitPromise: true, returnByValue: true });
    if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
    return r.result.result.value;
  };
  // 네트워크가 조용해질 때까지(진행 중 요청이 5초 넘게 걸린 것은 오래 붙는 연결로 보고 뺀다) - 최대 ms
  const settle = async (ms) => {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) {
      const now = Date.now();
      const busy = [...inflight.values()].some((t) => now - t < 5000);
      if (!busy && now - lastNet >= 250) return;
      await sleep(50);
    }
  };
  try {
    await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable"); await send("Network.enable");
    // 이동 뒤 새 문서가 다 읽히고(readyState) 편집기면 슬라이드가 그려질 때까지 기다린다 - 최대 20초. 해시만 바뀌는 같은 문서 이동은 표시로 알아본다
    const nav = async (url) => {
      try { await evalJs("window.__nxOld = 1"); } catch (e) { /* about:blank */ }
      const r = await send("Page.navigate", { url });
      const sameDoc = !(r.result && r.result.loaderId);
      if (sameDoc) await sleep(300);
      for (let i = 0; i < 200; i++) {
        let ready = false;
        try { ready = await evalJs(`${sameDoc ? "" : "!window.__nxOld && "}document.readyState === "complete" && (!document.querySelector("#host") || !!document.querySelector("#host .rs-slide, #host .empty, #host .rs-el"))`); } catch (e) { ready = false; }
        if (ready) break;
        await sleep(100);
      }
    };
    if (sc.login) {
      await nav(sc.base + "/login");
      const ok = await evalJs(`(await fetch("/api/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(${JSON.stringify(sc.login)})})).ok`);
      console.log(ok ? "로그인 OK" : "로그인 FAIL"); if (!ok) fails++;
    }
    for (const p of sc.pages) {
      errors.length = 0;
      const t0 = Date.now(); await nav(sc.base + p.url); await sleep(150); await settle(p.wait || 1500);
      console.log(`\n== ${p.url} (진입 ${((Date.now() - t0) / 1000).toFixed(1)}초)`);
      for (const s of p.steps || []) {
        let v, err = null;
        try { v = await evalJs(s.js); } catch (e) { err = e.message; }
        if (s.wait) await sleep(s.wait);
        if (s.shot) {  // 단계 뒤 화면을 PNG 로 남긴다(사람이 보는 점검용) - {shot: "<파일 경로>"}
          try { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(s.shot, Buffer.from(r.result.data, "base64")); console.log(`     화면 → ${s.shot}`); } catch (e) { console.log(`     화면 저장 실패: ${e.message}`); }
        }
        const ok = !err && v !== false && !(typeof v === "string" && !s.dump);  // 단계가 돌려준 글은 실패 사유(dump 단계만 결과 글)
        if (!ok) fails++;
        console.log(`${ok ? "OK  " : "FAIL"} ${s.name}${err ? " - " + err : v === false ? "" : typeof v === "string" && (s.dump || v.length < 200) ? " → " + v : ""}`);
      }
      await sleep(300); await settle(1000);  // 마지막 단계가 부른 요청(늦춰 저장 포함)의 실패·예외가 콘솔에 닿을 시간
      if (errors.length) { fails++; console.log("FAIL 콘솔 오류:", errors.slice(0, 8)); } else console.log("OK   콘솔 오류 없음");
    }
  } finally {
    delete handlers[sid];
    await bsend("Target.disposeBrowserContext", { browserContextId: ctx });
  }
  return fails;
}
main().catch((e) => { console.error(e); process.exit(2); });
