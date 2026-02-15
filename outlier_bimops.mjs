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
  // Navigate Google auth page back to Outlier login
  let { ws, send, eval_ } = await connectToPage("accounts.google.com");

  // Go back to Outlier login page
  await eval_(`window.location.href = 'https://app.outlier.ai/en/expert/login'`);
  await sleep(5000);
  ws.close(); await sleep(1000);

  // Reconnect to outlier
  ({ ws, send, eval_ } = await connectToPage("outlier"));

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Click Continue with Google again
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(el => el.textContent.includes('Continue with Google') && el.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Google button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    await sleep(6000);

    // Check tabs
    const tabs = await (await fetch(CDP_HTTP + "/json")).json();
    console.log("\nTabs:");
    tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    // Find Google account chooser
    const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
    if (googleTab) {
      ws.close(); await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("accounts.google.com"));

      r = await eval_(`return document.body.innerText.substring(0, 2000)`);
      console.log("\nGoogle page:", r);

      // Click on weber@bimopsstudio.com account specifically
      r = await eval_(`
        // Find the account item with bimopsstudio
        const items = Array.from(document.querySelectorAll('li, [data-email], [data-identifier]'));
        const bimItem = items.find(el => el.textContent.includes('bimopsstudio'));
        if (bimItem) {
          bimItem.click();
          return 'clicked bimopsstudio';
        }
        // Try finding by data-email attribute
        const dataItems = Array.from(document.querySelectorAll('[data-email]'));
        const bimData = dataItems.find(el => el.getAttribute('data-email').includes('bimopsstudio'));
        if (bimData) {
          bimData.click();
          return 'clicked bimopsstudio data-email';
        }
        // Try any clickable element with that text
        const allEls = Array.from(document.querySelectorAll('*'))
          .filter(el => el.textContent.includes('bimopsstudio') && el.offsetParent !== null && el.children.length < 5);
        if (allEls.length > 0) {
          return JSON.stringify(allEls.map(el => ({
            tag: el.tagName,
            text: el.textContent.trim().substring(0, 60),
            rect: JSON.parse(JSON.stringify(el.getBoundingClientRect()))
          })));
        }
        return 'bimopsstudio not found';
      `);
      console.log("\nBimops click:", r);

      // If we got elements, click the one that looks like an account selector
      if (r.startsWith('[')) {
        const els = JSON.parse(r);
        // Find the one that's a reasonable size (account item)
        const item = els.find(e => e.rect.height > 30 && e.rect.height < 120) || els[0];
        if (item) {
          await sleep(300);
          await clickAt(send, Math.round(item.rect.x + item.rect.width/2), Math.round(item.rect.y + item.rect.height/2));
          console.log("Clicked at:", Math.round(item.rect.x + item.rect.width/2), Math.round(item.rect.y + item.rect.height/2));
        }
      }

      await sleep(8000);

      // Check result
      ws.close(); await sleep(1000);
      const tabs2 = await (await fetch(CDP_HTTP + "/json")).json();
      console.log("\nTabs after auth:");
      tabs2.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

      // Check outlier page
      const oTab = tabs2.find(t => t.type === "page" && t.url.includes("outlier") && !t.url.includes("google"));
      if (oTab) {
        ({ ws, send, eval_ } = await connectToPage("outlier"));
        r = await eval_(`return window.location.href`);
        console.log("\nOutlier URL:", r);
        r = await eval_(`return document.body.innerText.substring(0, 4000)`);
        console.log("\nOutlier page:", r);
        ws.close();
      }
    }
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
