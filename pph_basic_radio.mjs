// Select Basic radio and submit on PPH fast-track page
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
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected");

  // Find all radio buttons and form elements
  let r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
    const labels = Array.from(document.querySelectorAll('label'));
    const forms = Array.from(document.querySelectorAll('form'));
    const submits = Array.from(document.querySelectorAll('button[type="submit"], input[type="submit"], button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, text: (el.textContent?.trim() || el.value || '').substring(0, 60),
        type: el.type, class: (el.className?.toString() || '').substring(0, 60),
        rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }
      }));

    const radioInfo = radios.map(r => ({
      name: r.name, value: r.value, checked: r.checked,
      id: r.id,
      labelText: r.labels?.[0]?.textContent?.trim()?.substring(0, 80) || '',
      parentClass: r.parentElement?.className?.substring(0, 60),
      grandparentText: r.parentElement?.parentElement?.textContent?.trim()?.substring(0, 80)
    }));

    const labelInfo = labels.filter(l => l.textContent.includes('Basic') || l.textContent.includes('Fast'))
      .map(l => ({
        text: l.textContent.trim().substring(0, 80),
        for: l.htmlFor,
        class: (l.className?.toString() || '').substring(0, 60),
        hasRadio: !!l.querySelector('input[type="radio"]'),
        rect: { x: Math.round(l.getBoundingClientRect().x + l.getBoundingClientRect().width/2),
                y: Math.round(l.getBoundingClientRect().y + l.getBoundingClientRect().height/2) }
      }));

    return JSON.stringify({ radios: radioInfo, labels: labelInfo, forms: forms.length, submits });
  `);
  console.log(r);

  const info = JSON.parse(r);

  // Find the Basic radio button
  const basicRadio = info.radios.find(r =>
    r.labelText.includes('Basic') || r.value?.includes('basic') || r.value === '0' || r.value === 'false'
  );

  const basicLabel = info.labels.find(l => l.text.includes('Basic'));

  if (basicRadio) {
    console.log(`\nSelecting radio: name="${basicRadio.name}" value="${basicRadio.value}" (${basicRadio.labelText})`);
    await eval_(`
      const radio = document.querySelector('input[type="radio"][value="${basicRadio.value}"][name="${basicRadio.name}"]') ||
                    Array.from(document.querySelectorAll('input[type="radio"]')).find(r => !r.checked);
      if (radio) {
        radio.checked = true;
        radio.click();
        radio.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `);
    console.log("Radio selected");
  } else if (basicLabel) {
    console.log(`\nClicking label: "${basicLabel.text}" at (${basicLabel.rect.x}, ${basicLabel.rect.y})`);
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed", x: basicLabel.rect.x, y: basicLabel.rect.y,
      button: "left", clickCount: 1
    });
    await sleep(50);
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased", x: basicLabel.rect.x, y: basicLabel.rect.y,
      button: "left", clickCount: 1
    });
    console.log("Label clicked");
  } else if (info.radios.length > 0) {
    // Just select the second radio (Basic is usually second, Fast-Track first)
    const idx = info.radios.length > 1 ? 1 : 0;
    console.log(`\nSelecting radio #${idx}: name="${info.radios[idx].name}" value="${info.radios[idx].value}"`);
    await eval_(`
      const radios = document.querySelectorAll('input[type="radio"]');
      if (radios[${idx}]) {
        radios[${idx}].checked = true;
        radios[${idx}].click();
        radios[${idx}].dispatchEvent(new Event('change', { bubbles: true }));
      }
    `);
    console.log("Radio selected");
  }

  await sleep(1000);

  // Verify selection
  r = await eval_(`
    const checked = document.querySelector('input[type="radio"]:checked');
    return checked ? JSON.stringify({ name: checked.name, value: checked.value, label: checked.labels?.[0]?.textContent?.trim()?.substring(0, 50) }) : 'none checked';
  `);
  console.log("Selected:", r);

  // Find and click submit/continue button
  console.log("\nLooking for submit button...");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"], a'))
      .filter(el => {
        if (!el.offsetParent) return false;
        const text = (el.textContent?.trim() || el.value || '').toLowerCase();
        return (text.includes('continue') || text.includes('submit') || text.includes('proceed') ||
                text.includes('confirm') || text.includes('select') || text === 'next') &&
               el.getBoundingClientRect().y > 200;
      })
      .map(el => ({
        tag: el.tagName, text: (el.textContent?.trim() || el.value || '').substring(0, 50),
        href: el.href || '', type: el.type,
        rect: { x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }
      }));

    return JSON.stringify(btns);
  `);
  console.log("Submit buttons:", r);

  const buttons = JSON.parse(r);
  if (buttons.length > 0) {
    const btn = buttons[0];
    console.log(`Clicking: "${btn.text}" at (${btn.rect.x}, ${btn.rect.y})`);
    if (btn.href) {
      await eval_(`window.location.href = ${JSON.stringify(btn.href)}`);
    } else {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btn.rect.x, y: btn.rect.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btn.rect.x, y: btn.rect.y, button: "left", clickCount: 1 });
    }
    await sleep(5000);
  } else {
    // Maybe the form submits automatically or there's a different mechanism
    // Try submitting any form on the page
    console.log("No submit button found, trying form submit...");
    await eval_(`
      const form = document.querySelector('form');
      if (form) { form.submit(); return 'form submitted'; }
      return 'no form';
    `);
    await sleep(5000);
  }

  // Final result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body?.innerText?.substring(0, 1500)
    });
  `);
  console.log("\nFinal:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
