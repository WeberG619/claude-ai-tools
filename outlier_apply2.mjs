const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Click APPLY NOW button
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('a, button'))
      .find(el => el.textContent.trim() === 'APPLY NOW' && el.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), href: btn.href || '' });
    }
    return 'not found';
  `);
  console.log("APPLY NOW button:", r);

  if (r !== 'not found') {
    const info = JSON.parse(r);
    if (info.href) {
      await eval_(`window.location.href = '${info.href}'`);
    } else {
      await sleep(300);
      // Get fresh coords
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('a, button'))
          .find(el => el.textContent.trim() === 'APPLY NOW' && el.offsetParent !== null);
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      `);
      const pos = JSON.parse(r);
      await clickAt(send, pos.x, pos.y);
    }
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("outlier"));

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);

    r = await eval_(`
      const body = document.body.innerText;
      return body.substring(0, 6000);
    `);
    console.log("\nPage content:");
    console.log(r);

    // Check for Google sign in or form fields
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          type: el.type,
          name: el.name,
          placeholder: el.placeholder,
          id: el.id
        }));
      const btns = Array.from(document.querySelectorAll('a, button'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50)
        .map(el => ({ text: el.textContent.trim(), href: el.href || '', tag: el.tagName }));
      return JSON.stringify({ inputs, buttons: btns.slice(0, 15) }, null, 2);
    `);
    console.log("\nForm elements:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
