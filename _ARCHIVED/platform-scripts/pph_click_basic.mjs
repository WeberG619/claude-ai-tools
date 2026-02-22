// Click the Basic (FREE) option on PPH fast-track page
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected");

  // Get the full page structure around the Basic/FREE option
  let r = await eval_(`
    // Find all elements that contain "Basic" or "FREE" text
    const elements = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return el.offsetParent !== null &&
               el.children.length === 0 &&
               (text === 'Basic' || text === 'FREE' || text === 'Free');
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        class: (el.className?.toString() || '').substring(0, 80),
        parentTag: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 80),
        grandparentTag: el.parentElement?.parentElement?.tagName,
        grandparentClass: (el.parentElement?.parentElement?.className?.toString() || '').substring(0, 80),
        rect: {
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        },
        clickable: el.tagName === 'A' || el.tagName === 'BUTTON' || el.closest('a') || el.closest('button')
      }));

    // Also look for clickable containers around these
    const containers = Array.from(document.querySelectorAll('a, button, [role="button"], [class*="card"], [class*="option"], [class*="plan"]'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return el.offsetParent !== null &&
               (text.includes('Basic') || text.includes('FREE')) &&
               !text.includes('Search') &&
               el.getBoundingClientRect().y > 200;  // Below header
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 100),
        href: el.href || '',
        class: (el.className?.toString() || '').substring(0, 80),
        rect: {
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }
      }));

    return JSON.stringify({ textElements: elements, containers });
  `);
  console.log("Page elements:", r);

  const info = JSON.parse(r);

  // Find the best clickable element for "Basic" / "FREE"
  let target = null;

  // First try: container that has "Basic" and is a link/button
  if (info.containers.length > 0) {
    target = info.containers.find(c => c.text.includes('Basic'));
    if (!target) target = info.containers[0];
  }

  // If no container, look for the text element's parent
  if (!target && info.textElements.length > 0) {
    const basicEl = info.textElements.find(e => e.text === 'Basic' || e.text === 'FREE');
    if (basicEl) {
      target = { ...basicEl, text: `${basicEl.text} (text element)` };
    }
  }

  if (target) {
    console.log(`\nClicking: "${target.text}" at (${target.rect.x}, ${target.rect.y})`);

    // If it's a link, click via JS
    if (target.href) {
      await eval_(`window.location.href = ${JSON.stringify(target.href)}`);
    } else {
      // Click via CDP coordinates
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: target.rect.x, y: target.rect.y,
        button: "left", clickCount: 1
      });
      await sleep(50);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: target.rect.x, y: target.rect.y,
        button: "left", clickCount: 1
      });
    }
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body?.innerText?.substring(0, 1000)
      });
    `);
    console.log("\nAfter click:", r);
  } else {
    console.log("\nCouldn't find Basic/FREE option. Full page text:");
    r = await eval_(`return document.body?.innerText?.substring(0, 2000)`);
    console.log(r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
