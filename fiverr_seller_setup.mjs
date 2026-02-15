// Set up Fiverr seller profile and navigate to gig creation
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
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Navigate to seller dashboard / start selling
  console.log("=== Navigating to seller setup ===");
  await send("Page.navigate", { url: "https://www.fiverr.com/start_selling" });
  await sleep(5000);

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 3000),
      buttons: Array.from(document.querySelectorAll('button, a[role="button"], a'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({
          text: b.textContent?.trim().substring(0, 80) || '',
          href: b.href?.substring(0, 100) || '',
          tag: b.tagName
        }))
        .filter(b => b.text.length > 0 && (
          b.text.toLowerCase().includes('become') ||
          b.text.toLowerCase().includes('start') ||
          b.text.toLowerCase().includes('create') ||
          b.text.toLowerCase().includes('seller') ||
          b.text.toLowerCase().includes('gig') ||
          b.text.toLowerCase().includes('continue') ||
          b.text.toLowerCase().includes('next') ||
          b.text.toLowerCase().includes('switch')
        ))
    });
  `);

  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Title:", state.title);
  console.log("\nRelevant buttons/links:");
  state.buttons.forEach(b => console.log(`  [${b.tag}] "${b.text}" ${b.href ? '-> ' + b.href : ''}`));
  console.log("\nPage preview:");
  console.log(state.preview.substring(0, 2000));

  // Step 2: Check if we need to click "Become a Seller" or if we're already on seller setup
  if (state.url.includes('seller_dashboard') || state.url.includes('start_selling')) {
    // Look for a CTA button
    const cta = state.buttons.find(b =>
      b.text.toLowerCase().includes('become') ||
      b.text.toLowerCase().includes('start') ||
      b.text.toLowerCase().includes('create a gig') ||
      b.text.toLowerCase().includes('continue')
    );

    if (cta) {
      console.log(`\nClicking: "${cta.text}"`);
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button, a'))
          .find(b => b.offsetParent !== null && b.textContent.trim().includes(${JSON.stringify(cta.text.substring(0, 30))}));
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
        }
        return null;
      `);

      if (r) {
        const pos = JSON.parse(r);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
        await sleep(5000);
      }
    }
  }

  // Step 3: Check new state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 4000),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({
          tag: i.tagName, type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder || '',
          value: i.type !== 'password' ? (i.value || '').substring(0, 80) : '***',
          ariaLabel: i.getAttribute('aria-label') || ''
        })),
      buttons: Array.from(document.querySelectorAll('button, a'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({
          text: b.textContent?.trim().substring(0, 80) || '',
          href: b.href?.substring(0, 100) || '',
          tag: b.tagName
        }))
        .filter(b => b.text.length > 2)
        .slice(0, 25)
    });
  `);

  const newState = JSON.parse(r);
  console.log("\n=== After navigation ===");
  console.log("URL:", newState.url);
  console.log("Title:", newState.title);
  console.log("\nInputs:", newState.inputs.length);
  newState.inputs.forEach(i => console.log(`  [${i.type}] name="${i.name}" id="${i.id}" placeholder="${i.placeholder}" value="${i.value}"`));
  console.log("\nButtons/links:");
  newState.buttons.forEach(b => console.log(`  [${b.tag}] "${b.text}" ${b.href ? '-> ' + b.href : ''}`));
  console.log("\nPage text:");
  console.log(newState.preview.substring(0, 2500));

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
