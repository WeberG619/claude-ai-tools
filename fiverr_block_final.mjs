// Final attempt - find three-dot menu on profile, or use Fiverr report system
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // We're on the anna profile page - look for ALL small clickable icons
  console.log("=== All small buttons/icons on profile page ===");
  let r = await eval_(`
    const smallBtns = Array.from(document.querySelectorAll('button, a, [role="button"], svg'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.width > 0 && rect.width < 60 && rect.y > 60 && rect.y < 400;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent?.trim()?.substring(0, 30) || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        title: el.title || '',
        class: (el.className?.toString() || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width)
      }));
    return JSON.stringify(smallBtns);
  `);
  console.log("Small buttons:", r);
  const smallBtns = JSON.parse(r);

  // Click "More about me" which might have a dropdown with Report/Block
  const moreBtn = smallBtns.find(b => b.text.includes('More about me'));
  if (moreBtn) {
    console.log(`\nClicking "More about me" at (${moreBtn.x}, ${moreBtn.y})`);
    await clickAt(send, moreBtn.x, moreBtn.y);
    await sleep(2000);

    r = await eval_(`
      return JSON.stringify({
        body: (document.body?.innerText || '').substring(0, 2000)
      });
    `);
    console.log("After More about me:", r);

    // Look for Report/Block in the expanded view
    r = await eval_(`
      const els = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const t = (el.textContent?.trim() || '').toLowerCase();
          return (t === 'report' || t === 'block' || t === 'block this user' || t === 'report this user' || t.includes('report user') || t.includes('block user')) && el.offsetParent !== null && el.children.length === 0;
        })
        .map(el => ({
          text: el.textContent.trim(),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(els);
    `);
    console.log("Report/Block in expanded:", r);
  }

  // Try the Fiverr API with proper CSRF token
  console.log("\n=== Trying block via Fiverr API ===");
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        // Get CSRF token from meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.content : '';

        // Try blocking via the manage_contacts API
        const res = await fetch('/manage_contacts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRF-Token': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: 'username=anna_39610ogm&action=block',
          credentials: 'include'
        });
        const text = await res.text();
        resolve(JSON.stringify({ status: res.status, csrf: csrfToken ? 'found' : 'missing', body: text.substring(0, 300) }));
      } catch(e) {
        resolve(JSON.stringify({ error: e.message }));
      }
    });
  `);
  console.log("Block API:", r);

  // Try another API endpoint
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.content : '';

        // Try the blocked_users endpoint
        const res = await fetch('/api/v1/users/anna_39610ogm/block', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'include'
        });
        const text = await res.text();
        resolve(JSON.stringify({ status: res.status, body: text.substring(0, 300) }));
      } catch(e) {
        resolve(JSON.stringify({ error: e.message }));
      }
    });
  `);
  console.log("Block API v2:", r);

  // Also try report
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.content : '';

        const res = await fetch('/report/user/anna_39610ogm', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ reason: 'spam_phishing', description: 'Sent phishing link pretending to be an order: projectfiv-overview.help' }),
          credentials: 'include'
        });
        const text = await res.text();
        resolve(JSON.stringify({ status: res.status, body: text.substring(0, 300) }));
      } catch(e) {
        resolve(JSON.stringify({ error: e.message }));
      }
    });
  `);
  console.log("Report API:", r);

  // Navigate to Fiverr support ticket
  console.log("\n=== Opening Fiverr Support ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/support_tickets/new'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 1500)
    });
  `);
  state = JSON.parse(r);
  console.log("Support URL:", state.url);
  if (!state.isError) {
    console.log("Support page:", state.body);
  } else {
    console.log("Bot detection on support page");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
