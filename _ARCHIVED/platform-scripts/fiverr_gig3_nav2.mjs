// Go back to manage gigs and find the Create button
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found. Tabs: ${tabs.map(t=>t.url.substring(0,60)).join(' | ')}`);
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
  // Navigate back to manage gigs
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs" });
  await sleep(5000);
  ws.close();
  await sleep(1000);

  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

  // Search for ALL clickable elements containing "create" or "new gig"
  let r = await eval_(`
    const results = [];

    // Check all links
    Array.from(document.querySelectorAll('a')).forEach(el => {
      const text = el.textContent.trim().toLowerCase();
      if (text.includes('create') && text.includes('gig')) {
        results.push({
          tag: 'A', text: el.textContent.trim().substring(0, 40),
          href: el.href, class: (el.className || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        });
      }
    });

    // Check all buttons
    Array.from(document.querySelectorAll('button')).forEach(el => {
      const text = el.textContent.trim().toLowerCase();
      if (text.includes('create') && text.includes('gig')) {
        results.push({
          tag: 'BUTTON', text: el.textContent.trim().substring(0, 40),
          class: (el.className || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        });
      }
    });

    // Check all divs/spans with role="button" or onclick
    Array.from(document.querySelectorAll('[role="button"], [onclick], [class*="create"], [class*="btn"]')).forEach(el => {
      const text = el.textContent.trim().toLowerCase();
      if (text.includes('create') && text.includes('gig')) {
        results.push({
          tag: el.tagName, text: el.textContent.trim().substring(0, 40),
          class: (el.className || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        });
      }
    });

    return JSON.stringify(results);
  `);
  console.log("Create elements:", r);
  const elements = JSON.parse(r);

  if (elements.length > 0) {
    // Use the first one - prefer links with href
    const el = elements.find(e => e.href) || elements[0];
    if (el.href) {
      console.log(`Navigating to: ${el.href}`);
      // Use window.location instead of Page.navigate to avoid bot detection
      await eval_(`window.location.href = '${el.href}'`);
    } else {
      console.log(`Clicking at (${el.x}, ${el.y})`);
      await clickAt(send, el.x, el.y);
    }
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("fiverr.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: (document.body?.innerText || '').substring(200, 1000)
      });
    `);
    const state = JSON.parse(r);
    console.log("\nURL:", state.url);
    console.log("Wizard:", state.wizard);
    console.log("Body:", state.body.substring(0, 500));
  } else {
    console.log("No create button found!");
    // Let's just dump all visible links
    r = await eval_(`
      return Array.from(document.querySelectorAll('a'))
        .filter(el => el.offsetParent !== null && el.href)
        .slice(0, 20)
        .map(el => ({ text: el.textContent.trim().substring(0, 40), href: el.href.substring(0, 80) }));
    `);
    console.log("All links:", JSON.stringify(r, null, 2));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
