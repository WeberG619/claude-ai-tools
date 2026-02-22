// Fiverr identity verification flow
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

  // Select "Outside of my primary job" option
  console.log("=== Step 1: Usage Intent ===");
  let r = await eval_(`
    // Click the first option (outside primary job)
    const options = Array.from(document.querySelectorAll('[class*="option"], [class*="card"], [role="radio"], input[type="radio"]'))
      .filter(el => el.offsetParent !== null);

    // Also look for clickable text elements
    const textEls = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.trim() === 'Outside of my primary job or profession' && el.children.length === 0);

    return JSON.stringify({
      options: options.map(o => ({
        tag: o.tagName,
        text: o.textContent?.trim()?.substring(0, 50),
        class: (o.className?.toString() || '').substring(0, 60),
        y: Math.round(o.getBoundingClientRect().y),
        x: Math.round(o.getBoundingClientRect().x + o.getBoundingClientRect().width/2)
      })),
      textEls: textEls.map(t => ({
        tag: t.tagName,
        y: Math.round(t.getBoundingClientRect().y),
        x: Math.round(t.getBoundingClientRect().x + t.getBoundingClientRect().width/2),
        parentTag: t.parentElement?.tagName,
        parentClass: (t.parentElement?.className?.toString() || '').substring(0, 60)
      }))
    });
  `);
  console.log("Options:", r);

  // Click "Outside of my primary job"
  r = await eval_(`
    const el = Array.from(document.querySelectorAll('*'))
      .find(e => e.textContent?.trim()?.startsWith('Outside of my primary') && e.offsetParent !== null);
    if (el) {
      // Click the parent container which is likely the radio card
      const card = el.closest('[class*="card"]') || el.closest('[role="radio"]') || el.closest('label') || el.parentElement;
      card.click();
      return 'clicked: ' + card.tagName + '.' + (card.className?.toString() || '').substring(0, 40);
    }
    return 'not found';
  `);
  console.log("Selection:", r);
  await sleep(500);

  // Click Next
  console.log("\nClicking Next...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      btn.click();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next btn' });
  `);
  console.log("Next:", r);
  await sleep(5000);

  // Check next page
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  console.log("\n=== Next page ===");
  const nextPage = JSON.parse(r);
  console.log("URL:", nextPage.url);
  console.log("Body:", nextPage.bodyPreview);

  // Check for form fields
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type,
        name: el.name || '',
        placeholder: (el.placeholder || '').substring(0, 40),
        value: (el.value || '').substring(0, 40),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        y: Math.round(el.getBoundingClientRect().y)
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify({ inputs, btns: btns.slice(0, 10) });
  `);
  console.log("\nForm:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
