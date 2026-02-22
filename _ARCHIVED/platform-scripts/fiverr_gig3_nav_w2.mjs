// Try navigating directly to wizard=2 (Description)
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // First, try clicking the "Description & FAQ" step in the sidebar
  let r = await eval_(`
    // Find the step 3 link in the sidebar
    const steps = Array.from(document.querySelectorAll('a, [class*="step"], [class*="nav"]'))
      .filter(el => el.textContent.trim().includes('Description') && el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 30),
        href: el.href?.substring(0, 80) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(steps);
  `);
  console.log("Description steps:", r);
  const steps = JSON.parse(r);

  // Try clicking the step
  if (steps.length > 0) {
    const step = steps[0];
    console.log(`Clicking "${step.text}" at (${step.x}, ${step.y})`);

    if (step.href) {
      await eval_(`window.location.href = '${step.href}'`);
    } else {
      await clickAt(send, step.x, step.y);
    }
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After step click:", r);
  }

  // If still on wizard=1, try direct URL navigation
  const state = JSON.parse(r);
  if (state.wizard === '1' || state.wizard === null) {
    console.log("\nTrying direct URL to wizard=2...");
    const currentUrl = state.url;
    const newUrl = currentUrl.replace('wizard=1', 'wizard=2');
    console.log("Navigating to:", newUrl);
    await eval_(`window.location.href = '${newUrl}'`);
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After direct nav:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
