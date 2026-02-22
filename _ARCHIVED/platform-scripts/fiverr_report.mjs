// Report and block scammer - try message hover and profile page
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

  // Approach 1: Hover over Jamie's phishing message to reveal report icon
  console.log("=== Hovering over Jamie's messages ===");
  let r = await eval_(`
    // Find the phishing message element
    const msgs = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('projectfiv') && el.children.length === 0 && el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 60),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 60)
      }));
    return JSON.stringify(msgs);
  `);
  console.log("Phishing messages:", r);
  const msgs = JSON.parse(r);

  if (msgs.length > 0) {
    const msg = msgs[0];
    // Hover over the message
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: msg.x, y: msg.y });
    await sleep(1500);

    // Check for any new elements
    r = await eval_(`
      const newEls = Array.from(document.querySelectorAll('[class*="action"], [class*="report"], [class*="flag"], [class*="spam"], [class*="hover"], [class*="options"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 0)
        .map(el => ({
          text: el.textContent?.trim()?.substring(0, 40) || '',
          class: (el.className?.toString() || '').substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(newEls);
    `);
    console.log("Hover elements:", r);
  }

  // Approach 2: Navigate to Jamie's profile page and find Report
  console.log("\n=== Jamie's profile page ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/anna_39610ogm'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch'),
      body: (document.body?.innerText || '').substring(0, 2000)
    });
  `);
  let state = JSON.parse(r);
  console.log("URL:", state.url);

  if (!state.isError) {
    console.log("Body:", state.body);

    // Look for report button on profile
    r = await eval_(`
      const reportEls = Array.from(document.querySelectorAll('a, button, span'))
        .filter(el => {
          const t = (el.textContent?.trim() || '').toLowerCase();
          return (t.includes('report') || t.includes('block') || t.includes('flag')) && el.offsetParent !== null;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          tag: el.tagName,
          href: el.href || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(reportEls);
    `);
    console.log("Report elements:", r);
    const reportEls = JSON.parse(r);

    if (reportEls.length > 0) {
      const reportBtn = reportEls[0];
      console.log(`\nClicking "${reportBtn.text}" at (${reportBtn.x}, ${reportBtn.y})`);
      await clickAt(send, reportBtn.x, reportBtn.y);
      await sleep(3000);

      // Handle report dialog
      r = await eval_(`
        return JSON.stringify({
          body: (document.body?.innerText || '').substring(0, 2000),
          modals: Array.from(document.querySelectorAll('[class*="modal"], [role="dialog"], [class*="overlay"]'))
            .filter(el => el.offsetParent !== null && el.textContent?.trim()?.length > 10)
            .map(el => el.textContent?.trim()?.substring(0, 300))
        });
      `);
      console.log("Report dialog:", r);

      // Look for spam/phishing option and select it
      r = await eval_(`
        const options = Array.from(document.querySelectorAll('input[type="radio"], label, button, [class*="option"], li'))
          .filter(el => {
            const t = (el.textContent?.trim() || '').toLowerCase();
            return (t.includes('spam') || t.includes('phish') || t.includes('scam') || t.includes('suspicious') || t.includes('fraud') || t.includes('inappropriate')) && el.offsetParent !== null;
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 60),
            tag: el.tagName,
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(options);
      `);
      console.log("Report options:", r);
      const options = JSON.parse(r);

      if (options.length > 0) {
        await clickAt(send, options[0].x, options[0].y);
        await sleep(1000);

        // Submit
        r = await eval_(`
          const submit = Array.from(document.querySelectorAll('button'))
            .find(b => {
              const t = b.textContent.trim().toLowerCase();
              return (t.includes('submit') || t.includes('report') || t.includes('send') || t.includes('confirm')) && b.offsetParent !== null;
            });
          if (submit) {
            const rect = submit.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: submit.textContent.trim() });
          }
          return JSON.stringify({ error: 'no submit' });
        `);
        const submit = JSON.parse(r);
        if (!submit.error) {
          console.log(`Clicking "${submit.text}"`);
          await clickAt(send, submit.x, submit.y);
          await sleep(2000);
          console.log("REPORTED!");
        }
      }
    }

    // Now look for Block button
    r = await eval_(`
      const blockEls = Array.from(document.querySelectorAll('a, button, span'))
        .filter(el => {
          const t = (el.textContent?.trim() || '').toLowerCase();
          return t.includes('block') && el.offsetParent !== null;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(blockEls);
    `);
    console.log("\nBlock elements:", r);
    const blockEls = JSON.parse(r);

    if (blockEls.length > 0) {
      await clickAt(send, blockEls[0].x, blockEls[0].y);
      await sleep(2000);
      // Confirm
      r = await eval_(`
        const confirm = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim().toLowerCase().includes('block') || b.textContent.trim().toLowerCase().includes('confirm'));
        if (confirm) { confirm.click(); return 'BLOCKED'; }
        return 'no confirm needed or already blocked';
      `);
      console.log(r);
    }
  } else {
    console.log("Page blocked or profile not found");
    // Try Fiverr's contact support to report
    console.log("\nProfile not accessible. The scammer can be reported via Fiverr Help Center.");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
