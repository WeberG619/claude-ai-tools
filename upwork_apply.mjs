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
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");

  // Go to the job page
  await eval_(`window.location.href = 'https://www.upwork.com/jobs/Script-Writer_~022020713926735326507/'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Look for "Buy Connects" or "Apply Now" buttons/links
  r = await eval_(`
    const allLinks = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null)
      .filter(el => {
        const t = el.textContent.toLowerCase();
        return t.includes('buy') || t.includes('apply') || t.includes('connect') || t.includes('proposal') || t.includes('submit');
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 100),
        href: el.href || '',
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect()))
      }));
    return JSON.stringify(allLinks, null, 2);
  `);
  console.log("\\nAction buttons/links:");
  console.log(r);

  // Also check current connects count
  r = await eval_(`
    const text = document.body.innerText;
    const connectsMatch = text.match(/Available Connects:\\s*(\\d+)/i);
    const requiredMatch = text.match(/Required Connects.*?:\\s*(\\d+)/i);
    return JSON.stringify({
      available: connectsMatch ? connectsMatch[1] : 'unknown',
      required: requiredMatch ? requiredMatch[1] : 'unknown'
    });
  `);
  console.log("\\nConnects info:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
