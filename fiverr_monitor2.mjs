// Verify reply sent, check Jamie's profile, and monitor for response
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // First verify the full conversation
  console.log("=== Full Conversation ===");
  let r = await eval_(`
    const body = document.body?.innerText || '';
    const chatStart = body.indexOf('Hello there');
    const chatEnd = body.indexOf('Create an offer');
    if (chatStart !== -1 && chatEnd !== -1) {
      return body.substring(chatStart, chatEnd);
    }
    return body.substring(chatStart, chatStart + 2000);
  `);
  console.log(r);

  // Get Jamie's profile info from the sidebar
  console.log("\n=== Jamie's Profile ===");
  r = await eval_(`
    const sidebar = document.body?.innerText || '';
    const aboutIdx = sidebar.indexOf('About\\nJamie');
    if (aboutIdx !== -1) {
      return sidebar.substring(aboutIdx, aboutIdx + 500);
    }
    // Try to get the right panel info
    const fromIdx = sidebar.indexOf('From\\n\\nUnited States');
    if (fromIdx !== -1) {
      return sidebar.substring(fromIdx - 50, fromIdx + 300);
    }
    return 'profile not found in sidebar';
  `);
  console.log(r);

  // Now monitor for her next response
  console.log("\n=== Monitoring for Jamie's response ===");
  const MAX_CHECKS = 90; // 90 x 10s = 15 minutes
  const INTERVAL = 10000;

  let lastConvLength = 0;

  // Get baseline
  r = await eval_(`
    const body = document.body?.innerText || '';
    const chatStart = body.indexOf('Hello there');
    const chatEnd = body.indexOf('Create an offer');
    return (chatEnd !== -1) ? body.substring(chatStart, chatEnd).length : body.length;
  `);
  lastConvLength = parseInt(r) || 0;
  console.log(`Baseline conversation length: ${lastConvLength}`);

  for (let i = 0; i < MAX_CHECKS; i++) {
    try {
      r = await eval_(`
        const body = document.body?.innerText || '';
        const chatStart = body.indexOf('Hello there');
        const chatEnd = body.indexOf('Create an offer');
        const chat = (chatEnd !== -1) ? body.substring(chatStart, chatEnd) : '';

        // Count messages from Jamie after our last reply
        const ourReply = "Order Now";
        const afterIdx = chat.indexOf(ourReply);
        const afterOur = afterIdx !== -1 ? chat.substring(afterIdx + ourReply.length) : '';

        const hasNewJamie = afterOur.includes('Jamie C.');

        return JSON.stringify({
          chatLength: chat.length,
          hasNewJamie,
          afterOurReply: afterOur.trim().substring(0, 500),
          chat: chat.substring(chat.length - 600)
        });
      `);

      const data = JSON.parse(r);

      if (data.hasNewJamie || data.chatLength > lastConvLength + 20) {
        console.log(`\n*** NEW MESSAGE from Jamie (check #${i+1}) ***`);
        console.log("New content:", data.afterOurReply);
        console.log("\nRecent conversation:", data.chat);
        lastConvLength = data.chatLength;

        // Don't break - keep monitoring in case there are more messages
        await sleep(3000); // Brief pause then continue
        continue;
      }

      if (i % 6 === 0) {
        const mins = Math.round(i * INTERVAL / 60000);
        console.log(`[${mins}m] No new message yet...`);
      }

    } catch (e) {
      console.log(`Error at check #${i+1}: ${e.message.substring(0, 80)}`);
      break;
    }

    await sleep(INTERVAL);
  }

  console.log("\nMonitoring ended.");
  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
