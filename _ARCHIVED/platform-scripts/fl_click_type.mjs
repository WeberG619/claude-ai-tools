// Find and click "Earn money freelancing" on Freelancer.com
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");

  // Get ALL clickable/interactive elements on the page
  let r = await eval_(`
    const all = Array.from(document.querySelectorAll('*')).filter(el => {
      if (!el.offsetParent && el.tagName !== 'BODY') return false;
      const style = window.getComputedStyle(el);
      return style.cursor === 'pointer' || el.tagName === 'A' || el.tagName === 'BUTTON' ||
             el.getAttribute('role') === 'button' || el.getAttribute('tabindex') ||
             el.onclick || el.getAttribute('ng-click') || el.getAttribute('data-action');
    });
    return JSON.stringify(all.map(el => ({
      tag: el.tagName,
      text: el.textContent.trim().substring(0, 60),
      class: (el.className || '').toString().substring(0, 100),
      role: el.getAttribute('role'),
      href: el.getAttribute('href'),
      cursor: window.getComputedStyle(el).cursor
    })).filter(el => el.text.length > 0));
  `);
  console.log("Clickable elements:", r);

  // Try clicking by text match with any element
  console.log("\nClicking 'Earn money freelancing'...");
  r = await eval_(`
    // Find element containing exactly this text
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while (node = walker.nextNode()) {
      if (node.textContent.trim() === 'Earn money freelancing') {
        // Click the parent element
        let target = node.parentElement;
        // Walk up to find the clickable container
        for (let i = 0; i < 5; i++) {
          if (target) {
            target.click();
            target = target.parentElement;
          }
        }
        return 'clicked parent chain of text node';
      }
    }
    return 'text node not found';
  `);
  console.log("  ", r);
  await sleep(3000);

  // Check state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 600)
    });
  `);
  console.log("\nState:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
