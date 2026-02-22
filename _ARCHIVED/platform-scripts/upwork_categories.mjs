// Select category on Upwork profile creation and continue
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Find category options
  let r = await eval_(`
    // Look for clickable category elements
    const categories = Array.from(document.querySelectorAll('[class*="category"], [class*="tile"], [class*="card"], button, [role="button"]'))
      .filter(el => {
        const t = el.textContent.trim();
        return el.offsetParent !== null && t.length > 3 && t.length < 40
          && (t.includes('Admin') || t.includes('Writing') || t.includes('Data') || t.includes('Engineering'));
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        class: (el.className || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(categories);
  `);
  console.log("Categories found:", r);
  const cats = JSON.parse(r);

  // Try clicking "Writing & Translation" or "Admin Support"
  const writing = cats.find(c => c.text.includes('Writing'));
  const admin = cats.find(c => c.text.includes('Admin'));

  if (writing) {
    console.log(`Clicking: "${writing.text}" at (${writing.x}, ${writing.y})`);
    await clickAt(send, writing.x, writing.y);
    await sleep(1000);
  } else if (admin) {
    console.log(`Clicking: "${admin.text}" at (${admin.x}, ${admin.y})`);
    await clickAt(send, admin.x, admin.y);
    await sleep(1000);
  }

  // Check if subcategories appeared
  r = await eval_(`
    const body = document.body.innerText;
    const allClickable = Array.from(document.querySelectorAll('[class*="tile"], [class*="category"], [class*="card"], [class*="chip"], button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 2 && el.textContent.trim().length < 50
        && el.getBoundingClientRect().y > 200)
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        class: (el.className || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify({ bodySnip: body.substring(0, 400), clickable: allClickable });
  `);
  console.log("\nAfter category click:", r);
  const after = JSON.parse(r);

  // If subcategories, select relevant ones
  if (after.clickable.length > 0) {
    // Look for Data Entry, Proofreading, Resume Writing related
    for (const target of ['Data Entry', 'Data', 'Proofreading', 'Resume', 'General', 'Other']) {
      const match = after.clickable.find(c => c.text.includes(target));
      if (match) {
        console.log(`Selecting subcategory: "${match.text}"`);
        await clickAt(send, match.x, match.y);
        await sleep(500);
      }
    }
  }

  // Click Next
  await sleep(500);
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next' });
  `);
  console.log("\nNext button:", r);
  const nextBtn = JSON.parse(r);
  if (!nextBtn.error) {
    await clickAt(send, nextBtn.x, nextBtn.y);
    await sleep(5000);
  }

  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: location.href.split('/').pop().split('?')[0],
      body: document.body.innerText.substring(0, 400)
    });
  `);
  console.log("\nNext page:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
