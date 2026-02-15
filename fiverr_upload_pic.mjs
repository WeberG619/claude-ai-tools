const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
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

(async () => {
  let { ws, send, eval_ } = await connectToPage("fiverr");

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Navigate to profile edit page
  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619" });
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("Profile URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nProfile page:", r);

  // Look for profile picture upload area or edit button
  r = await eval_(`
    const els = document.querySelectorAll('[class*="profile"], [class*="avatar"], [class*="photo"], img[class*="profile"], img[class*="avatar"], [data-testid*="avatar"], [data-testid*="profile"]');
    return JSON.stringify(Array.from(els).slice(0, 10).map(el => {
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        classes: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
        src: el.src?.substring(0, 80) || '',
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      };
    }));
  `);
  console.log("\nProfile/avatar elements:", r);

  // Also check for any file inputs
  r = await eval_(`
    const inputs = document.querySelectorAll('input[type="file"]');
    return JSON.stringify(Array.from(inputs).map(i => ({
      name: i.name,
      accept: i.accept,
      id: i.id
    })));
  `);
  console.log("\nFile inputs:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
