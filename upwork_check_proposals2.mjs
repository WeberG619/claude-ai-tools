// Find and check proposals
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
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  // Try the proposals & offers page via nav
  console.log('=== FINDING PROPOSALS LINK ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/find-work/proposals'`);
  await sleep(5000);

  let url = await c.ev('window.location.href');
  console.log('URL:', url);

  let text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 5000)`);

  if (text.includes('404') || text.includes("can't find")) {
    // Try alternate URLs
    console.log('Trying alternate URL...');
    await c.ev(`window.location.href = 'https://www.upwork.com/nx/proposals/'`);
    await sleep(5000);
    url = await c.ev('window.location.href');
    console.log('URL:', url);
    text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 5000)`);
  }

  if (text.includes('404') || text.includes("can't find")) {
    console.log('Trying another URL...');
    await c.ev(`window.location.href = 'https://www.upwork.com/ab/proposals/search'`);
    await sleep(5000);
    url = await c.ev('window.location.href');
    console.log('URL:', url);
    text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 5000)`);
  }

  if (text.includes('404') || text.includes("can't find")) {
    // Navigate via the nav menu
    console.log('Navigating via menu...');
    await c.ev(`window.location.href = 'https://www.upwork.com/nx/find-work/'`);
    await sleep(5000);

    // Look for Proposals link in nav
    const navLinks = await c.ev(`
      (() => {
        var links = document.querySelectorAll('a');
        var result = [];
        for (var i = 0; i < links.length; i++) {
          var t = links[i].textContent.trim();
          if (t.includes('Proposal') || t.includes('proposal') || t.includes('Offer') || t.includes('Submit')) {
            result.push({ text: t.substring(0, 60), href: links[i].href.substring(0, 120) });
          }
        }
        return JSON.stringify(result);
      })()
    `);
    console.log('Nav links:', navLinks);

    // Click Proposals and offers from nav
    const clickResult = await c.ev(`
      (() => {
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
          if (links[i].textContent.trim().includes('Proposals') && links[i].href) {
            var href = links[i].href;
            window.location.href = href;
            return 'Navigating to: ' + href;
          }
        }
        return 'No proposals link found';
      })()
    `);
    console.log(clickResult);
    await sleep(5000);

    url = await c.ev('window.location.href');
    console.log('URL:', url);
    text = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 5000)`);
  }

  console.log('\n=== PAGE CONTENT ===');
  console.log(text);

  // Also check notifications
  console.log('\n=== CHECKING NOTIFICATIONS ===');
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/find-work/best-matches'`);
  await sleep(5000);

  // Look for notification count
  const notifs = await c.ev(`
    (() => {
      var badges = document.querySelectorAll('.nav-notifications .badge, [class*="notification"] [class*="badge"], [class*="notification"] [class*="count"]');
      var result = [];
      for (var i = 0; i < badges.length; i++) {
        result.push(badges[i].textContent.trim());
      }
      // Also get the notification bell text
      var notifBtn = document.querySelector('[class*="notification"]');
      return JSON.stringify({
        badges: result,
        notifText: notifBtn ? notifBtn.textContent.trim().substring(0, 40) : 'none'
      });
    })()
  `);
  console.log('Notifications:', notifs);

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
