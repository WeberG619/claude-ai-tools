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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");

  // Check membership/bids info
  await eval_(`window.location.href = 'https://www.freelancer.com/membership'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  r = await eval_(`
    const body = document.body.innerText;
    return body.substring(0, 4000);
  `);
  console.log("\\nMembership page:");
  console.log(r);

  // Now search for jobs we can bid on - data entry, writing, transcription
  await eval_(`window.location.href = 'https://www.freelancer.com/jobs/data-entry/?w=f&ngsw-bypass='`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

  r = await eval_(`
    const body = document.body.innerText;
    return body.substring(0, 6000);
  `);
  console.log("\\n\\n========== DATA ENTRY JOBS ==========");
  console.log(r);

  // Search for content writing
  await eval_(`window.location.href = 'https://www.freelancer.com/jobs/content-writing/?w=f&ngsw-bypass='`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

  r = await eval_(`
    const body = document.body.innerText;
    return body.substring(0, 6000);
  `);
  console.log("\\n\\n========== CONTENT WRITING JOBS ==========");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
