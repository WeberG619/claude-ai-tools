const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(30);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("signup.live") || t.url.includes("live.com") || t.url.includes("microsoft")));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Click Month dropdown
  let r = await eval_(`
    const monthBtn = document.querySelector('#BirthMonthDropdown');
    if (monthBtn) {
      const rect = monthBtn.getBoundingClientRect();
      return JSON.stringify({found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: monthBtn.textContent.trim()});
    }
    return JSON.stringify({found: false});
  `);
  console.log("Month btn:", r);
  let monthInfo = JSON.parse(r);
  if (monthInfo.found) {
    await clickAt(send, monthInfo.x, monthInfo.y);
    await sleep(1000);

    // Find and click March in the dropdown
    r = await eval_(`
      const items = document.querySelectorAll('[role="option"], [role="menuitem"], li, .option, [data-value]');
      const march = Array.from(items).find(i => i.textContent.trim() === 'March');
      if (march) {
        march.click();
        return 'selected March';
      }
      // Try looking for any dropdown items
      const allItems = document.querySelectorAll('.dropdown-item, .menu-item, [class*="option"], [class*="listbox"] *');
      return 'not found as March. items: ' + Array.from(allItems).slice(0, 10).map(i => i.textContent.trim().substring(0, 20)).join('|');
    `);
    console.log("March:", r);
    await sleep(1000);
  }

  // Click Day dropdown
  r = await eval_(`
    const dayBtn = document.querySelector('#BirthDayDropdown');
    if (dayBtn) {
      const rect = dayBtn.getBoundingClientRect();
      return JSON.stringify({found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: dayBtn.textContent.trim()});
    }
    return JSON.stringify({found: false});
  `);
  console.log("\nDay btn:", r);
  let dayInfo = JSON.parse(r);
  if (dayInfo.found) {
    await clickAt(send, dayInfo.x, dayInfo.y);
    await sleep(1000);

    // Find and click 18
    r = await eval_(`
      const items = document.querySelectorAll('[role="option"], [role="menuitem"], li, .option, [data-value]');
      const day18 = Array.from(items).find(i => i.textContent.trim() === '18');
      if (day18) {
        day18.click();
        return 'selected 18';
      }
      return 'not found';
    `);
    console.log("18:", r);
    await sleep(1000);
  }

  // Enter year
  r = await eval_(`
    const yearInput = document.querySelector('#floatingLabelInput23, input[name="BirthYear"]');
    if (!yearInput) return 'year input not found';
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(yearInput, '1974');
    yearInput.dispatchEvent(new Event('input', { bubbles: true }));
    yearInput.dispatchEvent(new Event('change', { bubbles: true }));
    return 'year set: ' + yearInput.value;
  `);
  console.log("\nYear:", r);
  await sleep(500);

  // Verify selections
  r = await eval_(`
    return JSON.stringify({
      month: document.querySelector('#BirthMonthDropdown')?.textContent?.trim() || '',
      day: document.querySelector('#BirthDayDropdown')?.textContent?.trim() || '',
      year: document.querySelector('#floatingLabelInput23, input[name="BirthYear"]')?.value || '',
      country: document.querySelector('#countryDropdownId')?.textContent?.trim() || ''
    });
  `);
  console.log("\nVerification:", r);

  // Click Next
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => b.textContent.includes('Next'));
    if (btn) { btn.click(); return 'clicked Next'; }
    return 'Next not found';
  `);
  console.log("\nNext:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Get form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button, iframe');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null || i.tagName === 'IFRAME').map(i => ({
      tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '',
      text: i.textContent?.trim().substring(0, 60) || '',
      src: i.src?.substring(0, 80) || ''
    })).slice(0, 20));
  `);
  console.log("\nForm fields:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_details.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
