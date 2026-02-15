const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  // Find the "Begin This Starter Assessment" button specifically
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Begin This Starter Assessment'));
    if (btn) {
      btn.scrollIntoView({ behavior: 'instant', block: 'center' });
      await new Promise(r => setTimeout(r, 300));
      // Get the inner text element for more precise clicking
      const innerSpans = Array.from(btn.querySelectorAll('*'));
      for (const el of innerSpans) {
        if (el.textContent.trim() === 'Begin This Starter Assessment' && el.children.length === 0) {
          const rect = el.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), source: 'span' });
        }
      }
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height - 15), source: 'btn-bottom' });
    }
    return 'not found';
  `);
  console.log("Begin button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("CDP clicked at", pos.x, pos.y);
    await sleep(2000);

    // Check if page changed
    r = await eval_(`return window.location.href`);
    console.log("URL after CDP click:", r);

    // If still on projects page, try JS click on the button itself
    if (r.includes('/workers/projects')) {
      console.log("Still on projects page, trying JS click...");
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('Begin This Starter Assessment'));
        if (btn) {
          // Try finding a link inside the button
          const link = btn.querySelector('a');
          if (link) { link.click(); return 'clicked link inside button'; }

          // Try clicking directly
          btn.click();
          return 'clicked button via JS';
        }
        return 'button not found';
      `);
      console.log("JS click result:", r);
      await sleep(5000);

      r = await eval_(`return window.location.href`);
      console.log("URL after JS click:", r);
    }

    // If still stuck, check all links and forms on the page
    if (r && r.includes('/workers/projects')) {
      r = await eval_(`
        // Check for forms
        const forms = document.querySelectorAll('form');
        const formInfo = Array.from(forms).map(f => ({ action: f.action, method: f.method }));

        // Check for data attributes on the Begin button
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('Begin This Starter Assessment'));
        let btnAttrs = {};
        if (btn) {
          for (const attr of btn.attributes) {
            btnAttrs[attr.name] = attr.value;
          }
          // Check parent elements
          let parent = btn.parentElement;
          let parentInfo = [];
          while (parent && parentInfo.length < 3) {
            parentInfo.push({ tag: parent.tagName, classes: parent.className?.substring(0, 60), href: parent.href || '' });
            parent = parent.parentElement;
          }
          return JSON.stringify({ forms: formInfo, btnAttrs, parentInfo, btnHTML: btn.outerHTML.substring(0, 300) });
        }
        return JSON.stringify({ forms: formInfo });
      `);
      console.log("\nPage structure:", r);
    }

    r = await eval_(`return document.body.innerText.substring(0, 6000)`);
    console.log("\nPage content:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
