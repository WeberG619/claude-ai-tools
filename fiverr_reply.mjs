// Reply to Jamie C. on Fiverr inbox
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

  // Make sure we're on the inbox with Jamie's conversation open
  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  if (!r.includes('inbox')) {
    await eval_(`window.location.href = 'https://www.fiverr.com/inbox'`);
    await sleep(4000);
  }

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
  console.log("Jamie conv:", r);
  const conv = JSON.parse(r);

  if (!conv.error) {
    await clickAt(send, conv.x, conv.y);
    await sleep(2000);
  }

  // Find the message textarea
  r = await eval_(`
    const ta = document.querySelector('textarea[placeholder*="message"], textarea[placeholder*="Type"]');
    if (ta) {
      const rect = ta.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no textarea' });
  `);
  console.log("Textarea:", r);
  const ta = JSON.parse(r);

  if (!ta.error) {
    // Click the textarea to focus
    await clickAt(send, ta.x, ta.y);
    await sleep(300);

    // Type the reply
    const reply = "Hi Jamie, I don't currently see any active orders on my account. All payments on Fiverr go through the platform's secure system. If you'd like to place an order, please use the \"Order Now\" button on my gig page and I'll get started right away!";
    await send("Input.insertText", { text: reply });
    await sleep(500);

    console.log("Typed reply. Sending...");

    // Find and click Send button
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 800)
        .map(el => ({
          text: el.textContent?.trim()?.substring(0, 30) || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          hasSvg: !!el.querySelector('svg')
        }));
      return JSON.stringify(btns);
    `);
    console.log("Buttons near input:", r);
    const btns = JSON.parse(r);

    // Click the send button (usually has an SVG icon, near the textarea)
    const sendBtn = btns.find(b => b.text.toLowerCase().includes('send') || b.ariaLabel.toLowerCase().includes('send') || b.hasSvg);
    if (sendBtn) {
      await clickAt(send, sendBtn.x, sendBtn.y);
      await sleep(2000);
      console.log("Reply sent!");

      // Verify by reading last messages
      r = await eval_(`
        const body = document.body?.innerText || '';
        const idx = body.lastIndexOf('Me');
        return idx !== -1 ? body.substring(idx, idx + 400) : 'could not find';
      `);
      console.log("\nVerification:", r);
    } else {
      console.log("No send button found!");
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
