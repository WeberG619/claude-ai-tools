// Find and click edit for location, then fix city
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Find all clickable elements near "Buffalo, ID" text
  let r = await eval_(`
    // Find all buttons/links with edit-related content or near the location
    const allBtns = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          href: el.href || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          title: el.title || '',
          class: (el.className || '').substring(0, 60),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          w: Math.round(rect.width),
          h: Math.round(rect.height)
        };
      });
    return JSON.stringify(allBtns, null, 2);
  `);
  console.log("All clickable elements:");
  console.log(r);

  // Also find where "Buffalo" text is
  r = await eval_(`
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const results = [];
    while (walker.nextNode()) {
      if (walker.currentNode.textContent.includes('Buffalo')) {
        const parent = walker.currentNode.parentElement;
        const rect = parent.getBoundingClientRect();
        results.push({
          text: walker.currentNode.textContent.trim().substring(0, 60),
          parentTag: parent.tagName,
          parentClass: (parent.className || '').substring(0, 60),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
    }
    return JSON.stringify(results, null, 2);
  `);
  console.log("\nBuffalo text locations:");
  console.log(r);

  // Check for any edit pencil icons (SVG icons that are clickable)
  r = await eval_(`
    const svgBtns = Array.from(document.querySelectorAll('button svg, a svg, [role="button"] svg'))
      .filter(el => el.closest('button, a, [role="button"]').offsetParent !== null)
      .map(el => {
        const btn = el.closest('button, a, [role="button"]');
        const rect = btn.getBoundingClientRect();
        return {
          btnTag: btn.tagName,
          btnText: btn.textContent.trim().substring(0, 30),
          ariaLabel: btn.getAttribute('aria-label') || '',
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          w: Math.round(rect.width),
          h: Math.round(rect.height)
        };
      });
    return JSON.stringify(svgBtns, null, 2);
  `);
  console.log("\nSVG icon buttons:");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
