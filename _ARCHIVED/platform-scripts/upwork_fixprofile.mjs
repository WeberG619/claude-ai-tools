// Fix city in profile settings after submission
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

  // Navigate to contact info settings
  console.log("Navigating to contact info settings...");
  await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
  await sleep(5000);

  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  console.log("Reconnected\n");

  let r = await eval_(`return JSON.stringify({
    url: location.href,
    bodySnippet: document.body.innerText.substring(0, 1000)
  })`);
  const page = JSON.parse(r);
  console.log("URL:", page.url);
  console.log("Body:", page.bodySnippet);

  // Check for inputs
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type,
        placeholder: el.placeholder || '',
        value: el.value,
        name: el.name || '',
        id: el.id || '',
        label: el.labels?.[0]?.textContent?.trim() || ''
      }));
    return JSON.stringify(inputs, null, 2);
  `);
  console.log("\nInputs:", r);

  // Check for buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 50),
        href: el.href || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(btns, null, 2);
  `);
  console.log("\nButtons/links:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
