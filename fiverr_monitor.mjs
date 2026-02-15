// Monitor Fiverr inbox for new messages from Jamie C.
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
  console.log("Monitoring Fiverr inbox for Jamie C.'s reply...\n");

  const MAX_CHECKS = 60; // 60 checks x 10s = 10 minutes
  const INTERVAL = 10000; // 10 seconds

  let lastMessageCount = 0;
  let lastBody = "";

  for (let i = 0; i < MAX_CHECKS; i++) {
    try {
      // Check the current conversation for new messages
      const r = await eval_(`
        // Get all message bubbles in the conversation
        const msgs = Array.from(document.querySelectorAll('[class*="message-body"], [class*="MessageBody"], [class*="msg-body"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent?.trim()?.substring(0, 200));

        // Fallback: look for all text blocks that look like messages
        const bodyText = document.body?.innerText || '';

        // Check if there's a new message from Jamie (not from "Me")
        const jamieMessages = [];
        const allText = bodyText.split('\\n');
        let isJamie = false;
        for (let j = 0; j < allText.length; j++) {
          const line = allText[j].trim();
          if (line === 'Jamie C.' && j > 0) isJamie = true;
          if (line === 'Me') isJamie = false;
          if (isJamie && line.length > 5 && !line.startsWith('Feb') && line !== 'Jamie C.' && line !== 'A') {
            jamieMessages.push(line);
          }
        }

        // Get the conversation text after our last message
        const ourMsg = 'What project do you have in mind?';
        const idx = bodyText.indexOf(ourMsg);
        const afterOurMsg = idx !== -1 ? bodyText.substring(idx + ourMsg.length).trim() : '';

        return JSON.stringify({
          jamieMessages,
          afterOurMsg: afterOurMsg.substring(0, 500),
          totalBodyLength: bodyText.length,
          hasNewContent: afterOurMsg.length > 50
        });
      `);

      const data = JSON.parse(r);

      if (data.hasNewContent && data.afterOurMsg !== lastBody) {
        console.log(`\n*** NEW MESSAGE DETECTED (check #${i+1}) ***`);
        console.log("Jamie's messages:", JSON.stringify(data.jamieMessages));
        console.log("After our message:", data.afterOurMsg);
        lastBody = data.afterOurMsg;

        // Get the full conversation for context
        const fullConv = await eval_(`
          const body = document.body?.innerText || '';
          // Find the chat section
          const chatStart = body.indexOf('Hello there');
          if (chatStart !== -1) {
            return body.substring(chatStart, chatStart + 2000);
          }
          return body.substring(0, 2000);
        `);
        console.log("\nFull conversation:\n" + fullConv);

        // Write result to file for the main process to read
        break;
      }

      // Also check if the conversation list shows an unread badge
      const unread = await eval_(`
        const badge = document.querySelector('[class*="unread"], [class*="badge"]');
        if (badge && badge.textContent?.trim()?.length > 0 && badge.textContent?.trim() !== '1') {
          return badge.textContent.trim();
        }
        // Check if Jamie's message preview changed
        const preview = Array.from(document.querySelectorAll('*'))
          .find(el => el.textContent?.includes('Jamie C.') && el.getBoundingClientRect().height < 80);
        return preview?.textContent?.trim()?.substring(0, 100) || 'no preview';
      `);

      if (i % 6 === 0) { // Log every minute
        const mins = Math.round(i * INTERVAL / 60000);
        console.log(`[${mins}m] Checking... no new message yet. Preview: ${typeof unread === 'string' ? unread.substring(0, 60) : unread}`);
      }

    } catch (e) {
      console.log(`[Check #${i+1}] Error: ${e.message.substring(0, 80)}`);
      // Connection might have dropped, try to reconnect
      break;
    }

    await sleep(INTERVAL);
  }

  console.log("\nMonitoring ended.");
  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
