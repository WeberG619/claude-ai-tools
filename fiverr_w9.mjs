// Handle Fiverr W-9 declaration and identity verification
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Click "Declare your status" link for W-9
  console.log("=== W-9 Declaration ===");
  let r = await eval_(`
    const link = Array.from(document.querySelectorAll('a, button, span'))
      .find(el => el.textContent.trim() === 'Declare your status');
    if (link) {
      const rect = link.getBoundingClientRect();
      link.click();
      return JSON.stringify({
        clicked: true,
        href: link.href || '',
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return JSON.stringify({ clicked: false });
  `);
  console.log("Declare status:", r);
  await sleep(3000);

  // Check what appeared
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  console.log("After click:", r);
  const page = JSON.parse(r);
  console.log("\nURL:", page.url);

  // Check if a modal or new page appeared
  r = await eval_(`
    // Check for modals
    const modals = Array.from(document.querySelectorAll('[class*="modal"], [role="dialog"], [class*="overlay"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent?.trim()?.substring(0, 200)
      }));

    // Check for radio buttons or checkboxes
    const formEls = Array.from(document.querySelectorAll('input[type="radio"], input[type="checkbox"], select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        type: el.type,
        name: el.name || '',
        value: el.value || '',
        id: el.id || '',
        label: el.labels?.[0]?.textContent?.trim()?.substring(0, 50) || '',
        checked: el.checked,
        y: Math.round(el.getBoundingClientRect().y)
      }));

    // Buttons
    const btns = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 200)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        tag: el.tagName,
        href: el.href || '',
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2)
      }))
      .filter(b => b.text.length > 0);

    return JSON.stringify({ modals, formEls, btns: btns.slice(0, 15) });
  `);
  console.log("\nPage elements:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
