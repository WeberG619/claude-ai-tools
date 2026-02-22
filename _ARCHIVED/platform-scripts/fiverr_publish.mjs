// Navigate back to gig publish page and publish
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

  // Check where we are
  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  // If on verification status page, click "Go back to Gig"
  if (r.includes('verification')) {
    console.log("On verification page, clicking 'Go back to Gig'...");
    r = await eval_(`
      const link = Array.from(document.querySelectorAll('a'))
        .find(a => a.textContent.trim() === 'Go back to Gig');
      if (link) {
        const rect = link.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no link' });
    `);
    const link = JSON.parse(r);
    if (!link.error) {
      await clickAt(send, link.x, link.y);
      await sleep(6000);
    }
  }

  // Check publish page
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 2000)
    });
  `);
  const page = JSON.parse(r);
  console.log("\n=== Publish Page ===");
  console.log("URL:", page.url);
  console.log("Body:", page.bodyPreview);

  // Check remaining requirements
  r = await eval_(`
    const bodyText = document.body?.innerText || '';
    return JSON.stringify({
      hasW9: bodyText.includes('Form W-9') || bodyText.includes('Declare your status'),
      hasVerify: bodyText.includes('Identity verification') && bodyText.includes('Verify'),
      hasPublishBtn: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Publish') && !b.textContent.includes('Preview')),
      hasHumanTouch: bodyText.includes('human touch')
    });
  `);
  console.log("\nStatus:", r);
  const status = JSON.parse(r);

  // Get all buttons
  r = await eval_(`
    return JSON.stringify(
      Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          disabled: el.disabled
        }))
        .filter(b => b.text.length > 0)
    );
  `);
  console.log("Buttons:", r);
  const btns = JSON.parse(r);

  // Find and click Publish
  const pubBtn = btns.find(b => b.text.includes('Publish') && !b.text.includes('Preview'));
  if (pubBtn && !pubBtn.disabled) {
    console.log(`\n=== PUBLISHING GIG at (${pubBtn.x}, ${pubBtn.y}) ===`);
    await clickAt(send, pubBtn.x, pubBtn.y);
    await sleep(10000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        bodyPreview: document.body?.innerText?.substring(0, 1500)
      });
    `);
    console.log("\nAfter publish:", r);
  } else if (pubBtn && pubBtn.disabled) {
    console.log("\nPublish button is DISABLED - requirements not met.");
  } else {
    console.log("\nNo Publish button found.");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
