// Navigate back to email form on Freelancer signup
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com/signup");

  // Click back again to get to email form
  console.log("Clicking back to email form...");

  // Use CDP to find the back button element and get its position for a real click
  let r = await eval_(`
    const allEls = Array.from(document.querySelectorAll('*'));
    const backBtn = allEls.find(el => {
      const style = window.getComputedStyle(el);
      return style.cursor === 'pointer' && el.offsetParent !== null &&
             (el.textContent.trim() === '<' || el.textContent.trim() === '‹' ||
              el.className?.toString()?.includes('back') || el.className?.toString()?.includes('Back') ||
              el.getAttribute('aria-label')?.includes('back'));
    });
    if (backBtn) {
      const rect = backBtn.getBoundingClientRect();
      return JSON.stringify({ found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2, tag: backBtn.tagName, class: backBtn.className?.toString() });
    }
    // Try the fl-icon or svg back arrow
    const icons = Array.from(document.querySelectorAll('fl-icon, svg, i, span'))
      .filter(el => el.offsetParent !== null && window.getComputedStyle(el).cursor === 'pointer');
    if (icons.length > 0) {
      const rect = icons[0].getBoundingClientRect();
      return JSON.stringify({ found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2, tag: icons[0].tagName, text: icons[0].textContent?.substring(0, 10) });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("  Back button:", r);

  const info = JSON.parse(r);
  if (info.found) {
    // Use CDP mouse click
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed", x: info.x, y: info.y, button: "left", clickCount: 1
    });
    await sleep(50);
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased", x: info.x, y: info.y, button: "left", clickCount: 1
    });
    console.log("  Clicked at", info.x, info.y);
  } else {
    // Try history.back()
    await eval_(`history.back()`);
    console.log("  Used history.back()");
  }

  await sleep(3000);

  // Check if we're on the email form
  r = await eval_(`
    const emailInput = document.querySelector('input[type="email"]') || document.querySelector('input[placeholder="Email"]');
    const passInput = document.querySelector('input[type="password"]');
    return JSON.stringify({
      url: location.href,
      hasEmail: !!emailInput,
      hasPass: !!passInput,
      emailValue: emailInput?.value || '',
      preview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("\n  State:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
