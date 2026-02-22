// Quick check if our reply went through
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

  // Check if our reply about "no active orders" is in the conversation
  let r = await eval_(`
    const body = document.body?.innerText || '';
    return JSON.stringify({
      hasOurReply: body.includes('active orders'),
      hasOrderNow: body.includes('Order Now'),
      fullChat: body.substring(0, 3000)
    });
  `);
  const data = JSON.parse(r);
  console.log("Our reply present?", data.hasOurReply, "Order Now?", data.hasOrderNow);

  if (!data.hasOurReply) {
    console.log("\nReply didn't go through! Resending...");

    // Find textarea and type
    r = await eval_(`
      const ta = document.querySelector('textarea');
      if (ta) {
        const rect = ta.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no textarea' });
    `);
    const ta = JSON.parse(r);

    if (!ta.error) {
      await clickAt(send, ta.x, ta.y);
      await sleep(300);

      const reply = 'Hi Jamie, I don\'t see any active orders on my account. All payments on Fiverr are processed through the platform. If you\'d like to place an order, please use the "Order Now" button on my gig page and I\'ll get started right away!';
      await send("Input.insertText", { text: reply });
      await sleep(500);

      // Click send
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(el => el.getAttribute('aria-label') === 'Send');
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no send' });
      `);
      const sendBtn = JSON.parse(r);
      if (!sendBtn.error) {
        await clickAt(send, sendBtn.x, sendBtn.y);
        await sleep(2000);
        console.log("Sent!");

        // Verify
        r = await eval_(`
          const body = document.body?.innerText || '';
          return body.includes('active orders') ? 'CONFIRMED - reply visible' : 'NOT visible';
        `);
        console.log("Verification:", r);
      }
    }
  } else {
    console.log("Reply is already in the conversation. Good.");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
