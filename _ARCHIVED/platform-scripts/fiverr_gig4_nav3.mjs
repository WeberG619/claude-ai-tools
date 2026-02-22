// Find and click the CREATE A NEW GIG button (uppercase version in listing)
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
      expression: `(() => { ${expr} })()`,
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
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // List all clickable elements that mention "gig" or "create"
  let r = await eval_(`
    const items = Array.from(document.querySelectorAll('a, button, [role="button"]'))
      .filter(el => {
        const text = el.textContent.trim().toLowerCase();
        return el.offsetParent !== null && (text.includes('create') || text.includes('new gig'));
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        href: el.href || '',
        class: (el.className || '').substring(0, 60),
        rect: {
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          w: Math.round(el.getBoundingClientRect().width),
          h: Math.round(el.getBoundingClientRect().height)
        }
      }));
    return JSON.stringify(items);
  `);
  console.log("Create elements:", r);
  const items = JSON.parse(r);

  // Dismiss the max 4 gigs notification first
  r = await eval_(`
    const closeBtn = document.querySelector('[class*="notification"] [class*="close"], [class*="alert"] [class*="close"], [class*="dismiss"]');
    if (closeBtn) {
      closeBtn.click();
      return 'dismissed';
    }
    // Or just click somewhere to dismiss
    return 'no dismiss button';
  `);
  console.log("Dismiss:", r);
  await sleep(500);

  // Click the Create button
  if (items.length > 0) {
    // Prefer the one that's a link with href
    const target = items.find(i => i.href && i.href.includes('new')) || items[0];
    console.log(`\nClicking "${target.text}" (${target.tag}) at (${target.rect.x}, ${target.rect.y})`);
    await clickAt(send, target.rect.x, target.rect.y);
    await sleep(8000);

    // Check new page
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("fiverr.com"));
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        title: document.title,
        hasBot: document.body.innerText.includes('human touch'),
        body: document.body.innerText.substring(0, 300)
      });
    `);
    console.log("After click:", r);

    const state = JSON.parse(r);
    if (state.hasBot) {
      console.log("\n*** CAPTCHA DETECTED - waiting 30s for manual solve ***");
      await sleep(30000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("fiverr.com"));
      r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
      console.log("After wait:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
