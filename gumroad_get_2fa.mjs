// Check Gmail tab for Gumroad 2FA code
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
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();

  // First, check if there's a Gumroad email in the Gmail tab
  const gmailTab = pages.find(p => p.url.includes('mail.google.com'));
  if (gmailTab) {
    console.log('Found Gmail tab, checking for Gumroad email...');
    const c = await connect(gmailTab.webSocketDebuggerUrl);
    await sleep(500);

    // Search for Gumroad in Gmail
    await c.ev(`window.location.href = 'https://mail.google.com/mail/u/0/#search/gumroad'`);
    await sleep(5000);

    const results = await c.ev(`document.body.innerText.substring(0, 2000)`);
    console.log('Gmail search results:', results.substring(0, 500));

    // Check if we see any email with a token/code
    const token = await c.ev(`
      (() => {
        var body = document.body.innerText;
        // Look for 6-digit codes
        var match = body.match(/\\b(\\d{6})\\b/);
        if (match) return match[1];
        // Look for token patterns
        match = body.match(/token[:\\s]+([A-Za-z0-9]{6,})/i);
        if (match) return match[1];
        return 'none';
      })()
    `);
    console.log('Token found:', token);
    c.close();
  }

  // Also try resending the token and checking IMAP again
  const gumTab = pages.find(p => p.url.includes('gumroad.com'));
  if (gumTab) {
    console.log('\nGumroad 2FA page...');
    const c = await connect(gumTab.webSocketDebuggerUrl);

    // Click resend
    const resend = await c.ev(`
      (() => {
        var els = document.querySelectorAll('a, button');
        for (var i = 0; i < els.length; i++) {
          if (els[i].textContent.trim().includes('Resend')) {
            els[i].click();
            return 'Clicked resend';
          }
        }
        return 'no resend button';
      })()
    `);
    console.log(resend);
    c.close();
  }

  console.log('\nWaiting 10s for email...');
  await sleep(10000);

  // Check IMAP
  console.log('Done. The 2FA code will need to be entered from the email.');
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
