// Get full details on the best matching jobs
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    const nav = async (url) => { await send('Page.navigate', { url }); await sleep(5000); };
    ws.addEventListener('open', () => resolve({ ws, send, ev, nav, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  const jobUrls = [
    { label: '1. Revit 2025 add-in (C# - 5hrs ago)', url: 'https://www.upwork.com/jobs/Revit-2025-add_~022021630179255436296/' },
    { label: '2. Plugin Dev - ArchiCAD/AutoCAD - Windows Pipes (8min ago)', url: 'https://www.upwork.com/jobs/Plugin-Developer-NET-Python-ArchiCAD-AutoCAD-Image-Streaming-via-Windows-Pipes_~022021708919476426386/' },
    { label: '3. Architect/draftsman plan modification ($200 fixed)', url: 'https://www.upwork.com/jobs/Architect-draftsman-for-plan-modification_~022021708319268979720/' },
    { label: '4. Conversion of STEP Files to Revit ($30K+ client)', url: 'https://www.upwork.com/jobs/Conversion-STEP-Files-Revit-Files_~022021662627526474202/' },
    { label: '5. BIM File Creation Specialist', url: 'https://www.upwork.com/jobs/BIM-File-Creation-Specialist-Needed_~022021695853171177946/' },
  ];

  for (const job of jobUrls) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(job.label);
    console.log('='.repeat(60));

    await c.nav(job.url);
    await sleep(3000);

    const details = await c.ev(`
      (() => {
        const body = document.body.innerText;
        // Get just the job description area (skip nav, footer)
        const mainContent = document.querySelector('main, [role="main"], .job-details, [class*="job-detail"]');
        const text = mainContent ? mainContent.innerText : body;
        return text.substring(0, 3000);
      })()
    `);
    console.log(details);

    // Get proposals count and client info
    const meta = await c.ev(`
      (() => {
        const text = document.body.innerText;
        const proposalMatch = text.match(/(\\d+)\\s*(to\\s*\\d+)?\\s*proposals?/i);
        const connectMatch = text.match(/(\\d+)\\s*Connects?/i);
        const hireRateMatch = text.match(/(\\d+)%\\s*hire/i);
        return JSON.stringify({
          proposals: proposalMatch ? proposalMatch[0] : 'unknown',
          connects: connectMatch ? connectMatch[0] : 'unknown',
          hireRate: hireRateMatch ? hireRateMatch[0] : 'unknown'
        });
      })()
    `);
    console.log('\nMeta:', meta);
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
