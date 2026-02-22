// Create a Fiverr gig - navigate to creation page and fill in details
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

  // Navigate to new gig creation
  console.log("=== Navigating to gig creation ===");
  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs/new" });
  await sleep(5000);

  // Check what's on the page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 5000),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null || i.type === 'hidden')
        .map(i => ({
          tag: i.tagName, type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder || '',
          value: (i.value || '').substring(0, 80),
          ariaLabel: i.getAttribute('aria-label') || '',
          options: i.tagName === 'SELECT' ? Array.from(i.options).slice(0, 10).map(o => o.text.substring(0, 50) + '=' + o.value) : undefined
        }))
        .slice(0, 30),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({
          text: b.textContent?.trim().substring(0, 80) || '',
          type: b.type || ''
        }))
        .filter(b => b.text.length > 0)
        .slice(0, 20)
    });
  `);

  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Title:", state.title);
  console.log("\nInputs:");
  state.inputs.forEach(i => {
    let line = `  [${i.tag}/${i.type}] name="${i.name}" id="${i.id}" placeholder="${i.placeholder}"`;
    if (i.value) line += ` value="${i.value}"`;
    if (i.ariaLabel) line += ` aria="${i.ariaLabel}"`;
    if (i.options) line += ` opts=[${i.options.join(', ')}]`;
    console.log(line);
  });
  console.log("\nButtons:");
  state.buttons.forEach(b => console.log(`  "${b.text}" type=${b.type}`));
  console.log("\nPage text:");
  console.log(state.preview.substring(0, 3000));

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
