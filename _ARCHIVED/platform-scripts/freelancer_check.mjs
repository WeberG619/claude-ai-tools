const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching: ${urlMatch}`);
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
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");

  // Check current state
  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Check if logged in - go to dashboard
  await eval_(`window.location.href = 'https://www.freelancer.com/dashboard'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

  r = await eval_(`return window.location.href`);
  console.log("Dashboard URL:", r);

  r = await eval_(`
    const main = document.querySelector('main') || document.body;
    return main.innerText.substring(0, 3000);
  `);
  console.log("\nPage content:");
  console.log(r);

  // Check bids/membership info
  r = await eval_(`
    const text = document.body.innerText;
    const bidMatch = text.match(/bids?.*?(\\d+)/i);
    return JSON.stringify({
      hasBids: bidMatch ? bidMatch[0] : 'unknown',
      isLoggedIn: !text.includes('Log In') && !text.includes('Sign Up'),
      url: location.href
    });
  `);
  console.log("\nStatus:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
