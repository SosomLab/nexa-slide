// 헤드리스 Chrome 클릭 스모크 - CDP(원격 디버깅)로 페이지를 열고 단계(JS 식)를 차례로 실행하며 콘솔 오류·예외를 모은다.
//   node smoke.js <시나리오.json>   시나리오 = {base, login?: {id, password}, pages: [{url, steps: [{name, js, wait?}]}]}
//   js 는 페이지 안에서 평가되는 식(await 가능) - 결과가 false 면 FAIL. 콘솔 error/예외가 하나라도 있으면 그 페이지 FAIL.
const fs = require("fs"), { spawn } = require("child_process");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333 + Math.floor(Math.random() * 2000);  // 실행마다 다른 디버그 포트 - 앞선 실행의 Chrome 이 남아 있으면 그 창에 붙어 엉뚱한 상태로 시작하던 것
const sc = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let fails = 0;

async function main() {
  const prof = fs.mkdtempSync(require("path").join(require("os").tmpdir(), "nx-smoke-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, "--window-size=1400,1000", "about:blank"], { stdio: "ignore" });
  try {
    let targets;
    let t;
    for (let i = 0; i < 100 && !t; i++) { try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); t = (targets || []).find((x) => x.type === "page"); } catch (e) { /* 아직 안 떴다 */ } if (!t) await sleep(200); }
    if (!t) throw new Error("Chrome 디버그 포트에서 페이지를 찾지 못했다");
    const ws = new WebSocket(t.webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let id = 0; const pending = {}; const errors = [];
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; return; }
      if (d.method === "Runtime.consoleAPICalled" && (d.params.type === "error")) errors.push("console.error: " + d.params.args.map((a) => a.value || a.description || "").join(" "));
      if (d.method === "Runtime.exceptionThrown") errors.push("exception: " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
      if (d.method === "Log.entryAdded" && d.params.entry.level === "error" && !IGNORE.test(d.params.entry.text + " " + (d.params.entry.url || ""))) errors.push("log: " + d.params.entry.text + " " + (d.params.entry.url || ""));
    };
    // 콘솔 오류로 치지 않는 것 - 기본 목록 + 시나리오의 ignoreErrors(정규식 글) - 예: 일부러 틀린 그림 주소
    // fontfile·wsfonts = 이 PC 에 없는 글꼴(Pretendard 등)의 404 - 대체 글꼴로 그려지는 환경 차이라 오류가 아니다(배포 시험이 늘 smoke·editor 실패로 보이던 원인)
    const IGNORE = new RegExp("favicon|net::ERR_ABORTED|api\/engine\/notice|api\/image|api\/fontfile\/|wsfonts" + (sc.ignoreErrors ? "|" + sc.ignoreErrors : ""));
    const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
    const evalJs = async (js) => {
      const r = await send("Runtime.evaluate", { expression: `(async () => { ${js.includes("return") ? js : "return (" + js + ")"} })()`, awaitPromise: true, returnByValue: true });
      if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
      return r.result.result.value;
    };
    await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
    // 이동 뒤 문서가 다 읽히고(readyState) 편집기면 슬라이드가 그려질 때까지 기다린다(부하가 큰 묶음 실행에서 첫 단계가 너무 일찍 돌던 것) - 최대 20초
    const nav = async (url) => {
      await send("Page.navigate", { url }); await sleep(800);
      for (let i = 0; i < 40; i++) {
        let ready = false;
        try { ready = await evalJs(`document.readyState === "complete" && (!document.querySelector("#host") || !!document.querySelector("#host .rs-slide, #host .empty, #host .rs-el"))`); } catch (e) { ready = false; }
        if (ready) break;
        await sleep(500);
      }
      await sleep(700);
    };
    if (sc.login) {
      await nav(sc.base + "/login");
      const ok = await evalJs(`(await fetch("/api/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(${JSON.stringify(sc.login)})})).ok`);
      console.log(ok ? "로그인 OK" : "로그인 FAIL"); if (!ok) fails++;
    }
    for (const p of sc.pages) {
      errors.length = 0;
      await nav(sc.base + p.url); await sleep(p.wait || 1500);
      console.log(`\n== ${p.url}`);
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
      await sleep(500);
      if (errors.length) { fails++; console.log("FAIL 콘솔 오류:", errors.slice(0, 8)); } else console.log("OK   콘솔 오류 없음");
    }
    ws.close();
  } finally {
    // Windows 는 자식 프로세스까지 끝낸다(chrome.kill 만으로는 브라우저 프로세스가 남아 다음 실행을 느리게 하거나 포트를 쥔다)
    if (process.platform === "win32") { try { require("child_process").spawnSync("taskkill", ["/PID", String(chrome.pid), "/T", "/F"], { stdio: "ignore" }); } catch (e) { /* 무시 */ } }
    chrome.kill();
  }
  console.log(fails ? `\n실패 ${fails}` : "\n전부 통과");
  process.exit(fails ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });
