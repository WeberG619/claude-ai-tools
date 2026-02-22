// Find the right Gmail account and verify Upwork email
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
  // Try different Gmail account indexes
  let { ws, send, eval_ } = await connectToPage("mail.google.com");

  for (let accountIdx = 0; accountIdx <= 3; accountIdx++) {
    console.log(`\n=== Trying Gmail account /u/${accountIdx}/ ===`);
    await eval_(`window.location.href = 'https://mail.google.com/mail/u/${accountIdx}/#search/from%3Aupwork'`);
    await sleep(5000);

    ws.close();
    await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("mail.google.com"));

    let r = await eval_(`
      return JSON.stringify({
        url: location.href,
        title: document.title,
        account: document.title.match(/- (.+?) -/)?.[1] || document.title
      });
    `);
    console.log("Account:", r);
    const info = JSON.parse(r);

    if (info.account.includes('weberg619') || info.title.includes('weberg619')) {
      console.log("Found weberg619 account!");

      // Wait for search results
      await sleep(3000);

      // Find the Upwork verify email
      r = await eval_(`
        const rows = Array.from(document.querySelectorAll('tr'))
          .filter(el => el.textContent.includes('Upwork') || el.textContent.includes('Verify'))
          .map(el => ({
            text: el.textContent.trim().substring(0, 80),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(rows.slice(0, 3));
      `);
      console.log("Email rows:", r);
      const rows = JSON.parse(r);

      if (rows.length > 0) {
        await clickAt(send, rows[0].x, rows[0].y);
        await sleep(5000);

        // Find verify link
        r = await eval_(`
          const links = Array.from(document.querySelectorAll('a'))
            .filter(el => {
              const href = el.href || '';
              return href.includes('upwork') && (href.includes('verify') || href.includes('confirm') || href.includes('token'));
            })
            .map(el => ({
              text: el.textContent.trim().substring(0, 50),
              href: el.href.substring(0, 200),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(links);
        `);
        console.log("Verify links:", r);
        const links = JSON.parse(r);

        if (links.length > 0) {
          // Click the first verify link
          console.log(`Clicking: "${links[0].text}" at (${links[0].x}, ${links[0].y})`);
          await clickAt(send, links[0].x, links[0].y);
          await sleep(10000);

          // Check tabs
          const tabsRes = await fetch(`${CDP_HTTP}/json`);
          const tabs = await tabsRes.json();
          console.log("\nTabs after verify click:");
          for (const t of tabs) {
            if (t.type === "page") {
              console.log(`  ${t.title?.substring(0, 50)} | ${t.url.substring(0, 80)}`);
            }
          }
        } else {
          // Try broader search
          r = await eval_(`
            const allLinks = Array.from(document.querySelectorAll('a'))
              .filter(el => el.href && (el.href.includes('upwork') || el.textContent.toLowerCase().includes('verify')))
              .map(el => ({ text: el.textContent.trim().substring(0, 40), href: el.href.substring(0, 120) }));
            return JSON.stringify(allLinks.slice(0, 10));
          `);
          console.log("All relevant links:", r);
        }
      }
      break;
    }

    if (info.url.includes('AccountChooser') || info.url.includes('signin')) {
      console.log("Account not logged in, skipping...");
      // Navigate back
      await eval_(`window.location.href = 'https://mail.google.com/mail/u/0/'`);
      await sleep(3000);
      ws.close();
      await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("mail.google.com"));
      break;
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
