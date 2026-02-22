const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(30);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("prolific") || t.url?.includes("auth.prolific"));
  if (!tab) tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (!tab) { console.log("No tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Click "Sign up" link
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    const signup = links.find(a => a.textContent.trim().includes('Sign up'));
    if (signup) {
      signup.click();
      return 'clicked: ' + signup.href;
    }
    return 'not found';
  `);
  console.log("Sign up:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Check form
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type, name: i.name, id: i.id,
      placeholder: i.placeholder?.substring(0, 50) || '',
      text: i.tagName === 'BUTTON' ? i.textContent.trim().substring(0, 30) : ''
    })).slice(0, 30));
  `);
  console.log("\nForm:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\fiverr_newgig.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
