// Select Basic (FREE) option on PPH fast-track page
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
  console.log("URL:", await eval_(`return location.href`));

  // Find the Basic/FREE option and click it
  let r = await eval_(`
    const buttons = Array.from(document.querySelectorAll('a, button, [role="button"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 60),
        href: el.href || '',
        class: (el.className?.toString() || '').substring(0, 80),
        rect: { x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }
      }));

    // Find the "Basic" or "FREE" button
    const basicBtn = buttons.find(b =>
      b.text.toLowerCase().includes('basic') ||
      b.text.toLowerCase().includes('free') ||
      b.href.includes('basic') ||
      b.href.includes('free')
    );

    return JSON.stringify({ allButtons: buttons.filter(b => b.text.length > 1).slice(0, 15), basicBtn });
  `);
  console.log("Buttons:", r);

  const info = JSON.parse(r);

  if (info.basicBtn) {
    console.log(`\nClicking: "${info.basicBtn.text}" at (${info.basicBtn.rect.x}, ${info.basicBtn.rect.y})`);
    await eval_(`
      const btn = Array.from(document.querySelectorAll('a, button, [role="button"]'))
        .find(el => {
          const text = el.textContent.trim().toLowerCase();
          return el.offsetParent !== null && (text.includes('basic') || text.includes('free'));
        });
      if (btn) btn.click();
    `);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body?.innerText?.substring(0, 1000)
      });
    `);
    console.log("After click:", r);
  } else {
    console.log("\nNo Basic/Free button found. Available buttons:");
    info.allButtons.forEach(b => console.log(`  "${b.text}" (${b.tag}) href=${b.href?.substring(0, 60)}`));

    // Try clicking the second option (Basic is usually second)
    console.log("\nLooking for selectable options...");
    r = await eval_(`
      // Look for radio buttons or option cards
      const options = Array.from(document.querySelectorAll('[class*="option"], [class*="card"], [class*="plan"], [class*="choice"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          class: (el.className?.toString() || '').substring(0, 80),
          text: el.textContent.trim().substring(0, 100),
          rect: { x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                  y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }
        }));

      return JSON.stringify(options.slice(0, 10));
    `);
    console.log("Options:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
