// Block and report Jamie C. (scammer) on Fiverr
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

  // Make sure we're on the inbox with Jamie's conversation
  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  if (!r.includes('inbox')) {
    await eval_(`window.location.href = 'https://www.fiverr.com/inbox'`);
    await sleep(4000);

    // Click on Jamie's conversation
    r = await eval_(`
      const conv = Array.from(document.querySelectorAll('[class*="contact"]'))
        .find(el => el.textContent?.includes('Jamie') && el.offsetParent !== null);
      if (conv) {
        const rect = conv.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const conv = JSON.parse(r);
    if (!conv.error) {
      await clickAt(send, conv.x, conv.y);
      await sleep(2000);
    }
  }

  // Look for three-dot menu, report, or block options
  console.log("=== Looking for block/report options ===");
  r = await eval_(`
    // Look for menu icons (three dots, kebab menu, etc)
    const menuBtns = Array.from(document.querySelectorAll('button, [role="button"], svg, [class*="menu"], [class*="more"], [class*="option"], [class*="action"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y < 300 && rect.x > 500 && rect.width < 60;
      })
      .map(el => ({
        tag: el.tagName,
        ariaLabel: el.getAttribute('aria-label') || '',
        title: el.title || '',
        class: (el.className?.toString() || '').substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width)
      }));

    // Also look for any "block" or "report" text
    const blockLinks = Array.from(document.querySelectorAll('a, button, span'))
      .filter(el => {
        const t = (el.textContent?.trim() || '').toLowerCase();
        return (t.includes('block') || t.includes('report') || t.includes('spam')) && el.offsetParent !== null;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));

    return JSON.stringify({ menuBtns: menuBtns.slice(0, 10), blockLinks });
  `);
  console.log("Menu/Block options:", r);
  const opts = JSON.parse(r);

  // Try clicking menu buttons to find block option
  for (const btn of opts.menuBtns) {
    if (btn.ariaLabel.toLowerCase().includes('more') || btn.ariaLabel.toLowerCase().includes('menu') || btn.ariaLabel.toLowerCase().includes('option') || btn.w < 40) {
      console.log(`\nClicking menu button at (${btn.x}, ${btn.y}) - ${btn.ariaLabel || btn.class.substring(0, 30)}`);
      await clickAt(send, btn.x, btn.y);
      await sleep(1000);

      // Check for dropdown with block/report
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('li, a, button, [role="menuitem"], [class*="option"], [class*="item"]'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.width > 50 && rect.height < 60 && rect.height > 10;
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 50),
            tag: el.tagName,
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }))
          .filter(l => l.text.length > 0 && l.text.length < 40);
        return JSON.stringify(items);
      `);
      console.log("Menu items:", r);
      const items = JSON.parse(r);

      // Look for block or report
      const blockItem = items.find(i => i.text.toLowerCase().includes('block'));
      const reportItem = items.find(i => i.text.toLowerCase().includes('report'));

      if (reportItem) {
        console.log(`\nClicking REPORT at (${reportItem.x}, ${reportItem.y})`);
        await clickAt(send, reportItem.x, reportItem.y);
        await sleep(2000);

        // Handle report dialog
        r = await eval_(`
          return JSON.stringify({
            body: (document.body?.innerText || '').substring(0, 1500),
            modals: Array.from(document.querySelectorAll('[class*="modal"], [role="dialog"]'))
              .filter(el => el.offsetParent !== null)
              .map(el => el.textContent?.trim()?.substring(0, 300))
          });
        `);
        console.log("Report dialog:", r);

        // Look for spam/phishing option
        r = await eval_(`
          const options = Array.from(document.querySelectorAll('input[type="radio"], label, [class*="option"], li, button'))
            .filter(el => {
              const t = (el.textContent?.trim() || '').toLowerCase();
              return (t.includes('spam') || t.includes('phish') || t.includes('scam') || t.includes('suspicious') || t.includes('fraud')) && el.offsetParent !== null;
            })
            .map(el => ({
              text: el.textContent.trim().substring(0, 60),
              tag: el.tagName,
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(options);
        `);
        console.log("Spam/phishing options:", r);
        const spamOpts = JSON.parse(r);

        if (spamOpts.length > 0) {
          const spam = spamOpts[0];
          console.log(`Selecting "${spam.text}" at (${spam.x}, ${spam.y})`);
          await clickAt(send, spam.x, spam.y);
          await sleep(1000);

          // Submit report
          r = await eval_(`
            const submitBtn = Array.from(document.querySelectorAll('button'))
              .find(b => b.textContent.trim().toLowerCase().includes('submit') || b.textContent.trim().toLowerCase().includes('report') || b.textContent.trim().toLowerCase().includes('send'));
            if (submitBtn) {
              const rect = submitBtn.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: submitBtn.textContent.trim() });
            }
            return JSON.stringify({ error: 'no submit' });
          `);
          const submit = JSON.parse(r);
          if (!submit.error) {
            console.log(`Clicking "${submit.text}" at (${submit.x}, ${submit.y})`);
            await clickAt(send, submit.x, submit.y);
            await sleep(2000);
            console.log("Report submitted!");
          }
        }
      }

      if (blockItem) {
        console.log(`\nClicking BLOCK at (${blockItem.x}, ${blockItem.y})`);
        await clickAt(send, blockItem.x, blockItem.y);
        await sleep(2000);

        // Confirm block if needed
        r = await eval_(`
          const confirmBtn = Array.from(document.querySelectorAll('button'))
            .find(b => {
              const t = b.textContent.trim().toLowerCase();
              return (t.includes('block') || t.includes('confirm') || t.includes('yes')) && b.offsetParent !== null;
            });
          if (confirmBtn) {
            const rect = confirmBtn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: confirmBtn.textContent.trim() });
          }
          return JSON.stringify({ error: 'no confirm' });
        `);
        const confirm = JSON.parse(r);
        if (!confirm.error) {
          console.log(`Confirming block: "${confirm.text}" at (${confirm.x}, ${confirm.y})`);
          await clickAt(send, confirm.x, confirm.y);
          await sleep(2000);
        }
        console.log("USER BLOCKED!");
      }

      if (blockItem || reportItem) break;
    }
  }

  // Final status
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 500)
    });
  `);
  console.log("\nFinal state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
