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

  // Scroll to bottom to see the Generalist section
  await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(1000);

  // Find the English Writing opportunity - look for all elements containing that text
  let r = await eval_(`
    const allEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        return text.startsWith('English Writing and Content Reviewing') && el.children.length < 5;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 80),
        class: (el.className || '').substring(0, 60),
        href: el.href || el.closest('a')?.href || '',
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect())),
        clickable: el.tagName === 'A' || el.tagName === 'BUTTON' || el.style.cursor === 'pointer',
        parent: el.parentElement?.tagName,
        parentHref: el.parentElement?.href || el.parentElement?.closest('a')?.href || ''
      }));
    return JSON.stringify(allEls, null, 2);
  `);
  console.log("English Writing elements:");
  console.log(r);

  // Also check if items are links/cards
  r = await eval_(`
    // Look for card/list-item containers near "Generalist"
    const generalistSection = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent.trim() === 'Generalist');
    if (generalistSection) {
      const parent = generalistSection.parentElement;
      const next = generalistSection.nextElementSibling || parent?.nextElementSibling;
      if (next) {
        return JSON.stringify({
          nextTag: next.tagName,
          nextClass: next.className?.substring(0, 60),
          nextHTML: next.outerHTML.substring(0, 500),
          nextChildren: Array.from(next.querySelectorAll('a')).map(a => ({ href: a.href, text: a.textContent.trim().substring(0, 60) }))
        }, null, 2);
      }
    }
    return 'generalist section not found';
  `);
  console.log("\nGeneralist section:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
