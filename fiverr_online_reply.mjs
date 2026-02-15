// Set online visibility and reply to Jamie C.
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

  // Step 1: Click "Personal information" to find online visibility
  console.log("=== Personal Information Settings ===");
  let r = await eval_(`
    const link = Array.from(document.querySelectorAll('a, div, button'))
      .find(el => el.textContent?.trim()?.startsWith('Personal information') && el.offsetParent !== null && el.getBoundingClientRect().height < 100);
    if (link) {
      const rect = link.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), tag: link.tagName, href: link.href || '' });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Personal info:", r);
  const pi = JSON.parse(r);

  if (!pi.error) {
    await clickAt(send, pi.x, pi.y);
    await sleep(4000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        isError: (document.body?.innerText || '').includes('human touch'),
        body: (document.body?.innerText || '').substring(0, 3000)
      });
    `);
    const page = JSON.parse(r);
    console.log("URL:", page.url);

    if (!page.isError) {
      console.log("Body:", page.body);

      // Look for online status / availability toggles
      r = await eval_(`
        const toggles = Array.from(document.querySelectorAll('[role="switch"], input[type="checkbox"], [class*="toggle"], [class*="switch"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            tag: el.tagName,
            checked: el.checked ?? el.getAttribute('aria-checked'),
            nearText: el.closest('div, label, section')?.textContent?.trim()?.substring(0, 120) || '',
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));

        // Also look for any text about "online" or "visible" or "available"
        const relevant = Array.from(document.querySelectorAll('*'))
          .filter(el => {
            const t = el.textContent?.toLowerCase() || '';
            return (t.includes('online') || t.includes('visible') || t.includes('available') || t.includes('status')) &&
              el.children.length === 0 && el.offsetParent !== null && el.textContent.trim().length < 100;
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 80),
            y: Math.round(el.getBoundingClientRect().y)
          }));

        return JSON.stringify({ toggles, relevant });
      `);
      console.log("\nToggles & relevant:", r);

      // If there's a toggle, click it
      const data = JSON.parse(r);
      if (data.toggles.length > 0) {
        for (const t of data.toggles) {
          if (t.nearText.toLowerCase().includes('online') || t.nearText.toLowerCase().includes('visible') || t.nearText.toLowerCase().includes('available')) {
            console.log(`\nClicking availability toggle at (${t.x}, ${t.y}) - checked: ${t.checked}`);
            await clickAt(send, t.x, t.y);
            await sleep(2000);
          }
        }
      }
    } else {
      console.log("Bot detection on personal info page");
    }
  }

  // Step 2: Go to inbox and reply to Jamie
  console.log("\n=== Replying to Jamie C. ===");
  await eval_(`window.location.href = 'https://www.fiverr.com/inbox'`);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      isError: (document.body?.innerText || '').includes('human touch')
    });
  `);
  let state = JSON.parse(r);

  if (!state.isError) {
    // Click on Jamie C. conversation
    r = await eval_(`
      const conv = document.querySelector('.contact.first') ||
        Array.from(document.querySelectorAll('[class*="contact"]'))
          .find(el => el.textContent?.includes('Jamie'));
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
      await sleep(3000);

      // Find the message input
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], input[type="text"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            tag: el.tagName,
            placeholder: (el.placeholder || el.getAttribute('data-placeholder') || '').substring(0, 60),
            class: (el.className?.toString() || '').substring(0, 80),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
            editable: el.contentEditable
          }));
        return JSON.stringify(inputs);
      `);
      console.log("Message inputs:", r);
      const inputs = JSON.parse(r);

      const msgInput = inputs.find(i => i.placeholder.toLowerCase().includes('type') || i.placeholder.toLowerCase().includes('message') || i.tag === 'TEXTAREA');
      if (msgInput) {
        console.log(`Clicking message input at (${msgInput.x}, ${msgInput.y})`);
        await clickAt(send, msgInput.x, msgInput.y);
        await sleep(500);

        // Type the reply
        const reply = "Hi Jamie! Thanks for reaching out. I'd be happy to help you with any data entry, Excel spreadsheet work, or data processing needs. What project do you have in mind?";
        await send("Input.insertText", { text: reply });
        await sleep(500);

        console.log("Typed reply. Looking for Send button...");

        // Find and click Send
        r = await eval_(`
          const sendBtn = Array.from(document.querySelectorAll('button, [role="button"]'))
            .find(el => {
              const text = el.textContent?.trim().toLowerCase() || '';
              const aria = (el.getAttribute('aria-label') || '').toLowerCase();
              return (text === 'send' || text.includes('send') || aria.includes('send')) && el.offsetParent !== null;
            });
          if (sendBtn) {
            const rect = sendBtn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: sendBtn.textContent?.trim()?.substring(0, 30) });
          }
          // Also look for submit button with icon
          const iconBtn = Array.from(document.querySelectorAll('button'))
            .find(el => el.querySelector('svg') && el.getBoundingClientRect().y > 500 && el.offsetParent !== null);
          if (iconBtn) {
            const rect = iconBtn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: 'icon-button' });
          }
          return JSON.stringify({ error: 'no send button' });
        `);
        console.log("Send button:", r);
        const sendBtn = JSON.parse(r);

        if (!sendBtn.error) {
          await clickAt(send, sendBtn.x, sendBtn.y);
          await sleep(2000);
          console.log("Reply sent!");

          // Verify
          r = await eval_(`
            return (document.body?.innerText || '').substring(
              Math.max(0, (document.body?.innerText || '').length - 500)
            );
          `);
          console.log("Last part of page:", r);
        }
      } else {
        console.log("No message input found. Full inputs:", JSON.stringify(inputs));
      }
    }
  } else {
    console.log("Bot detection on inbox");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
