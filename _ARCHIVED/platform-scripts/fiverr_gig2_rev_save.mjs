// Set revisions and save pricing
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  await eval_(`window.scrollTo(0, 200)`);
  await sleep(500);

  // Get revision dropdown positions (visible only, y > 0)
  let r = await eval_(`
    const drops = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 0 && rect.y < 2000 &&
               !el.className.includes('duration') && el.textContent.trim() === 'Select';
      })
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(drops);
  `);
  console.log("Revision dropdowns:", r);
  const revDrops = JSON.parse(r);

  for (let i = 0; i < revDrops.length; i++) {
    console.log(`\nClicking revision ${i} at (${revDrops[i].x}, ${revDrops[i].y})`);
    await clickAt(send, revDrops[i].x, revDrops[i].y);
    await sleep(1000);

    // Find the "Unlimited" option or highest number
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('.table-select-option, [class*="select-option"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 0 && rect.height > 5;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 20),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    console.log("Options:", r);
    const options = JSON.parse(r);

    const unlimited = options.find(o => o.text.includes('UNLIMITED') || o.text.includes('Unlimited') || o.text.includes('unlimited'));
    if (unlimited) {
      console.log(`Selecting: "${unlimited.text}"`);
      await clickAt(send, unlimited.x, unlimited.y);
    } else if (options.length > 0) {
      // Select last option (usually highest number)
      const last = options[options.length - 1];
      console.log(`Selecting last: "${last.text}"`);
      await clickAt(send, last.x, last.y);
    }
    await sleep(500);
  }

  // Verify delivery times are set
  r = await eval_(`
    const deliveries = Array.from(document.querySelectorAll('.select-penta-design.pkg-duration-input.table-select'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(deliveries);
  `);
  console.log("\nDelivery times:", r);

  // Verify revisions
  r = await eval_(`
    const revs = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && !el.className.includes('duration'))
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(revs);
  `);
  console.log("Revisions:", r);

  // Verify prices
  r = await eval_(`
    const prices = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value);
    return JSON.stringify(prices);
  `);
  console.log("Prices:", r);

  // Scroll to Save & Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(800);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    console.log(`\nClicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 600)
      });
    `);
    const result = JSON.parse(r);
    console.log("URL:", result.url);
    console.log("Body:", result.body.substring(0, 400));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
