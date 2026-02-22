const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

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

  // First, check what the button looks like - is it in a scrollable container?
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (!btn) return 'no button found';

    // Get computed styles and parent info
    const rect = btn.getBoundingClientRect();
    const styles = window.getComputedStyle(btn);

    // Walk up parents to find scrollable containers
    let el = btn.parentElement;
    const parents = [];
    while (el) {
      const s = window.getComputedStyle(el);
      const r2 = el.getBoundingClientRect();
      if (s.overflow !== 'visible' || s.overflowY !== 'visible') {
        parents.push({
          tag: el.tagName,
          class: el.className?.substring?.(0, 50) || '',
          overflow: s.overflow,
          overflowY: s.overflowY,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          scrollTop: el.scrollTop,
          rect: { top: Math.round(r2.top), bottom: Math.round(r2.bottom), height: Math.round(r2.height) }
        });
      }
      el = el.parentElement;
    }

    return JSON.stringify({
      button: {
        text: btn.textContent.trim(),
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        display: styles.display,
        visibility: styles.visibility,
        position: styles.position,
        offsetParent: btn.offsetParent?.tagName
      },
      scrollableParents: parents,
      pageScroll: { scrollY: window.scrollY, scrollHeight: document.documentElement.scrollHeight, clientHeight: document.documentElement.clientHeight }
    }, null, 2);
  `);
  console.log("Button analysis:", r);

  // Now try scrolling the page to the very bottom
  r = await eval_(`
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise(r => setTimeout(r, 500));

    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) });
    }
    return 'not found';
  `);
  console.log("\nAfter page scroll to bottom:", r);

  // Try scrolling various parent containers
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (!btn) return 'no button';

    // Scroll all parents
    let el = btn.parentElement;
    while (el) {
      if (el.scrollHeight > el.clientHeight) {
        el.scrollTop = el.scrollHeight;
      }
      el = el.parentElement;
    }

    await new Promise(r => setTimeout(r, 500));

    // Also try focus + scrollIntoView
    btn.focus();
    btn.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(r => setTimeout(r, 500));

    const rect = btn.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) });
  `);
  console.log("\nAfter parent scroll + scrollIntoView:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
