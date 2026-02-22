// Set Freelancer.com username after signup
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found: ${urlMatch}`);
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
  console.log("Connected\n");

  // Try "BIMOpsStudio" first
  const usernames = ["BIMOpsStudio", "BimOpsStudio", "WeberGouin", "bimopsstudio"];

  for (const username of usernames) {
    console.log(`Trying username: ${username}...`);
    let r = await eval_(`
      const input = document.querySelector('input[type="text"]') || document.querySelector('input:not([type="hidden"]):not([type="checkbox"])');
      if (!input) return 'input not found';
      input.focus();
      input.value = '${username}';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set to: ' + input.value;
    `);
    console.log("  ", r);
    await sleep(1500);

    // Check if there's an error (username taken)
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [class*="taken"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim())
        .filter(t => t.length > 0);
      const success = Array.from(document.querySelectorAll('[class*="success"], [class*="valid"], [class*="available"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim());
      return JSON.stringify({ errors, success });
    `);
    console.log("  Validation:", r);

    const validation = JSON.parse(r);
    if (validation.errors.length === 0 || validation.success.length > 0) {
      console.log(`\n  Username "${username}" looks available!`);

      // Click Next
      console.log("  Clicking Next...");
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim().includes('Next'));
        if (btn) { btn.click(); return 'clicked Next'; }
        return 'Next button not found';
      `);
      console.log("  ", r);
      await sleep(5000);

      // Check what's next
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          pagePreview: document.body.innerText.substring(0, 800)
        }, null, 2);
      `);
      console.log("\n  Next page:", r);
      break;
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
