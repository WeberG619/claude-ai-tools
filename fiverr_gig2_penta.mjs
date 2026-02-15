// Click penta-design custom dropdowns for delivery time and revisions
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

async function selectPentaDropdown(send, eval_, dropX, dropY, targetText, label) {
  console.log(`\n[${label}] Clicking dropdown at (${dropX}, ${dropY})`);
  await clickAt(send, dropX, dropY);
  await sleep(1000);

  // Look for the opened options list - penta dropdowns typically show options below
  let r = await eval_(`
    // After clicking, look for option items that appeared
    const options = Array.from(document.querySelectorAll('[class*="option"], [class*="penta-list"] li, [class*="select-option"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.height > 5 && rect.y > ${dropY} - 10 &&
               Math.abs(rect.x - ${dropX}) < 200;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 30),
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(options.slice(0, 20));
  `);
  console.log(`  Options: ${r.substring(0, 300)}`);
  let options = JSON.parse(r);

  if (options.length === 0) {
    // Try broader search for items that contain day/number text
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('li, [role="option"], [class*="item"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          const text = el.textContent.trim();
          return el.offsetParent !== null && rect.height > 10 && rect.height < 50 &&
                 rect.y > ${dropY} - 20 && rect.y < ${dropY} + 400 &&
                 text.length > 0 && text.length < 30;
        })
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items.slice(0, 20));
    `);
    console.log(`  Broader search: ${r.substring(0, 300)}`);
    options = JSON.parse(r);
  }

  if (options.length === 0) {
    // Check if dropdown opened at all - look for any new visible container
    r = await eval_(`
      // Check for open dropdown container
      const containers = Array.from(document.querySelectorAll('[class*="open"], [class*="expanded"], [class*="active"], [class*="show"]'))
        .filter(el => {
          const cls = el.className?.toString() || '';
          return (cls.includes('select') || cls.includes('dropdown') || cls.includes('penta')) &&
                 el.offsetParent !== null && el.getBoundingClientRect().height > 50;
        })
        .map(el => ({
          class: (el.className?.toString() || '').substring(0, 80),
          text: el.textContent?.trim()?.substring(0, 200) || '',
          h: Math.round(el.getBoundingClientRect().height),
          y: Math.round(el.getBoundingClientRect().y)
        }));
      return JSON.stringify(containers);
    `);
    console.log(`  Open containers: ${r.substring(0, 300)}`);
  }

  // Select the target option
  if (options.length > 0) {
    const match = options.find(o => o.text.includes(targetText)) ||
                  options.find(o => o.text.toLowerCase().includes(targetText.toLowerCase())) ||
                  options[0];
    console.log(`  Selecting: "${match.text}" at (${match.x}, ${match.y})`);
    await clickAt(send, match.x, match.y);
    await sleep(500);
    return true;
  }
  return false;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to delivery time area
  await eval_(`window.scrollTo(0, 200)`);
  await sleep(500);

  // Get fresh positions of penta-design dropdowns
  let r = await eval_(`
    const drops = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        class: (el.className?.toString() || '').substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        isDuration: (el.className?.toString() || '').includes('duration'),
        isTable: (el.className?.toString() || '').includes('table-select')
      }));
    return JSON.stringify(drops);
  `);
  console.log("Penta design dropdowns:", r);
  const drops = JSON.parse(r);

  // Delivery time dropdowns (pkg-duration-input class)
  const deliveryDrops = drops.filter(d => d.isDuration);
  const deliveryDays = ["3 Day", "2 Day", "1 Day"];

  console.log("=== Delivery Times ===");
  for (let i = 0; i < deliveryDrops.length; i++) {
    await selectPentaDropdown(send, eval_, deliveryDrops[i].x, deliveryDrops[i].y, deliveryDays[i], `Delivery ${i}`);
  }

  // Revision dropdowns (table-select, not duration, text="Select")
  const revDrops = drops.filter(d => d.isTable && !d.isDuration && d.text === 'Select');
  console.log("\n=== Revisions ===");
  for (let i = 0; i < revDrops.length; i++) {
    await selectPentaDropdown(send, eval_, revDrops[i].x, revDrops[i].y, "Unlimited", `Revision ${i}`);
  }

  // Check prices
  r = await eval_(`
    const prices = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value);
    return JSON.stringify(prices);
  `);
  console.log("\nPrices:", r);

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
