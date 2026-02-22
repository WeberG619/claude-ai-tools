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

  const searches = ['data entry', 'content writing', 'proofreading', 'virtual assistant'];

  for (const query of searches) {
    await eval_(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=' + encodeURIComponent('${query}') + '&sort=recency&payment_verified=1'`);
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    // Get job titles and key info
    const r = await eval_(`
      const titles = Array.from(document.querySelectorAll('h3'))
        .filter(el => el.offsetParent !== null && el.closest('section'))
        .slice(0, 8)
        .map(el => {
          const section = el.closest('section');
          const link = el.querySelector('a');
          const text = section ? section.innerText : '';
          
          // Parse key info from section text
          const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
          
          return {
            title: (link || el).textContent.trim().substring(0, 80),
            href: link ? link.href : '',
            info: lines.slice(0, 8).join(' | ').substring(0, 300)
          };
        });
      return JSON.stringify(titles);
    `);
    
    const jobs = JSON.parse(r);
    console.log(`\n=== ${query.toUpperCase()} (${jobs.length} jobs) ===`);
    jobs.forEach((j, i) => {
      console.log(`\n${i+1}. ${j.title}`);
      console.log(`   ${j.info}`);
      if (j.href) console.log(`   ${j.href}`);
    });
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
