// Try editing location via profile page, not contact info settings
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Go to my profile page
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/~01e66dc9d884a0c3ca'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  let r = await eval_(`return JSON.stringify({
    url: location.href,
    bodySnippet: document.body.innerText.substring(0, 600)
  })`);
  console.log("Profile page:", r);

  // Look for edit buttons / pencil icons on the profile
  r = await eval_(`
    const editElements = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .filter(el => {
        const text = el.textContent.trim().toLowerCase();
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        return el.offsetParent !== null && (
          text.includes('edit') || aria.includes('edit') || 
          text.includes('pencil') || aria.includes('pencil') ||
          text.includes('location') || aria.includes('location')
        );
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        ariaLabel: el.getAttribute('aria-label') || '',
        href: el.href || '',
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(editElements, null, 2);
  `);
  console.log("Edit elements:", r);

  // Check location text on profile
  r = await eval_(`
    const locText = Array.from(document.querySelectorAll('*'))
      .filter(el => el.offsetParent !== null && el.children.length === 0)
      .filter(el => el.textContent.includes('Buffalo') || el.textContent.includes('Sandpoint') || el.textContent.includes(', ID'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(locText);
  `);
  console.log("Location text:", r);

  // Try: go to profile settings page
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/profile'`);
  await sleep(4000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({
    url: location.href,
    bodySnippet: document.body.innerText.substring(0, 800)
  })`);
  const profileSettings = JSON.parse(r);
  console.log("\nProfile Settings page:", profileSettings.url);
  console.log(profileSettings.bodySnippet);

  // Look for location edit on this page
  r = await eval_(`
    const editBtns = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        href: el.href || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(editBtns, null, 2);
  `);
  console.log("\nButtons/links:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
