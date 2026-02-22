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

  // Scroll down to the English Writing item
  await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(1000);

  // Get fresh coordinates
  let r = await eval_(`
    const el = Array.from(document.querySelectorAll('div'))
      .find(el => el.className.includes('cursor-pointer') && el.textContent.includes('English Writing and Content Reviewing'));
    if (el) {
      el.scrollIntoView({ block: 'center' });
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Element position:", r);
  await sleep(500);

  if (r !== 'not found') {
    // Get updated position after scrollIntoView
    r = await eval_(`
      const el = Array.from(document.querySelectorAll('div'))
        .find(el => el.className.includes('cursor-pointer') && el.textContent.includes('English Writing and Content Reviewing'));
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const pos = JSON.parse(r);
    console.log("Clicking at:", pos);
    await clickAt(send, pos.x, pos.y);
    await sleep(3000);

    // Check if page changed or modal opened
    r = await eval_(`return window.location.href`);
    console.log("\nURL after click:", r);

    r = await eval_(`
      const body = document.body.innerText;
      return body.substring(0, 6000);
    `);
    console.log("\nPage content after click:");
    console.log(r);

    // Check for any apply/sign up buttons
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('a, button'))
        .filter(el => el.offsetParent !== null)
        .filter(el => {
          const t = el.textContent.toLowerCase().trim();
          return t.length > 0 && t.length < 50 && (
            t.includes('apply') || t.includes('sign') || t.includes('google') ||
            t.includes('register') || t.includes('join') || t.includes('create') ||
            t.includes('log in') || t.includes('login')
          );
        })
        .map(el => ({
          text: el.textContent.trim(),
          href: el.href || '',
          tag: el.tagName
        }));
      return JSON.stringify(btns, null, 2);
    `);
    console.log("\nAction buttons:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
