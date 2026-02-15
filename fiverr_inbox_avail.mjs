// Read inbox message and find availability setting
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Click on Jamie C. conversation
  console.log("=== Opening Jamie C. message ===");
  let r = await eval_(`
    const conv = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent?.includes('Jamie C.') && el.getBoundingClientRect().width > 100 && el.getBoundingClientRect().height < 100 && el.offsetParent !== null);
    if (conv) {
      const rect = conv.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Jamie C.:", r);
  const jamie = JSON.parse(r);

  if (!jamie.error) {
    await clickAt(send, jamie.x, jamie.y);
    await sleep(3000);

    // Read the conversation
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 3000)
      });
    `);
    const conv = JSON.parse(r);
    console.log("URL:", conv.url);
    console.log("\nConversation:", conv.body);

    // Get message details
    r = await eval_(`
      const messages = Array.from(document.querySelectorAll('[class*="message"], [class*="chat"], [class*="bubble"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.getBoundingClientRect().height < 200)
        .map(el => ({
          text: el.textContent.trim().substring(0, 200),
          y: Math.round(el.getBoundingClientRect().y),
          class: (el.className?.toString() || '').substring(0, 60)
        }));
      return JSON.stringify(messages.slice(0, 10));
    `);
    console.log("\nMessage elements:", r);
  }

  // Now go to profile settings to find availability toggle
  console.log("\n=== Going to Profile Settings for Availability ===");
  r = await eval_(`
    const settingsLink = Array.from(document.querySelectorAll('a'))
      .find(a => a.href?.includes('account-settings') || a.href?.includes('sellers') && a.href?.includes('edit'));
    if (settingsLink) return settingsLink.href;
    return null;
  `);
  console.log("Settings link:", r);

  // Navigate to profile edit page
  await eval_(`window.location.href = 'https://www.fiverr.com/sellers/weberg619/edit'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 3000)
    });
  `);
  const profile = JSON.parse(r);
  console.log("\nProfile URL:", profile.url);

  if (profile.isError) {
    console.log("Bot detection on profile page");
  } else {
    console.log("Profile:", profile.body);

    // Look for availability/online status toggle
    r = await eval_(`
      const toggles = Array.from(document.querySelectorAll('[role="switch"], input[type="checkbox"], [class*="toggle"], [class*="switch"], [class*="availability"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          type: el.type || '',
          role: el.getAttribute('role') || '',
          checked: el.checked ?? el.getAttribute('aria-checked'),
          label: el.labels?.[0]?.textContent?.trim()?.substring(0, 50) || '',
          nearText: el.parentElement?.textContent?.trim()?.substring(0, 80) || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(toggles);
    `);
    console.log("\nToggles on profile:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
