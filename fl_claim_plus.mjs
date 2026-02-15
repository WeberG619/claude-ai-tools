// Claim free Plus membership on Freelancer
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com/dashboard");
  console.log("Connected to Freelancer dashboard\n");

  // Find and click "Claim it now for Free!" button
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('a, button'))
      .find(b => b.textContent.trim().includes('Claim it now') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim(), href: btn.href || '' });
    }
    return null;
  `);
  console.log("Claim button:", r);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("Clicked 'Claim it now for Free!'");
    await sleep(5000);

    // Check result
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 2000),
        buttons: Array.from(document.querySelectorAll('button, a'))
          .filter(b => b.offsetParent !== null)
          .map(b => ({ text: b.textContent.trim().substring(0, 60) }))
          .filter(b => b.text.length > 0 && (b.text.toLowerCase().includes('confirm') || b.text.toLowerCase().includes('claim') || b.text.toLowerCase().includes('upgrade') || b.text.toLowerCase().includes('activate') || b.text.toLowerCase().includes('start') || b.text.toLowerCase().includes('trial') || b.text.toLowerCase().includes('free')))
      });
    `);
    console.log("\nAfter click:", r);

    // If there's a confirmation button, click it
    const afterState = JSON.parse(r);
    if (afterState.buttons.length > 0) {
      console.log("Found confirmation buttons:", afterState.buttons.map(b => b.text).join(", "));

      // Click the first confirmation-type button
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button, a'))
          .filter(b => b.offsetParent !== null &&
            (b.textContent.trim().toLowerCase().includes('confirm') ||
             b.textContent.trim().toLowerCase().includes('activate') ||
             b.textContent.trim().toLowerCase().includes('start trial') ||
             b.textContent.trim().toLowerCase().includes('claim')));
        if (btns.length > 0) {
          const rect = btns[0].getBoundingClientRect();
          return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btns[0].textContent.trim() });
        }
        return null;
      `);
      if (r) {
        const cpos = JSON.parse(r);
        console.log(`Clicking confirmation: "${cpos.text}"`);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: cpos.x, y: cpos.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: cpos.x, y: cpos.y, button: "left", clickCount: 1 });
        await sleep(3000);
      }
    }

    // Final check
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 1500)
      });
    `);
    console.log("\nFinal state:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
