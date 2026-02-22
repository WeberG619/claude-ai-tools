// Fill Upwork profile creation steps
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

async function clickNext(send, eval_) {
  const r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' || b.textContent.trim() === 'Next, add your experience');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Next button' });
  `);
  const btn = JSON.parse(r);
  if (!btn.error) {
    await clickAt(send, btn.x, btn.y);
    await sleep(3000);
  }
  return btn;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // === STEP 1: Experience Level ===
  console.log("=== Step 1: Experience ===");
  // Select "I have some experience"
  let r = await eval_(`
    const radio = document.querySelector('input[value="NEEDS_TIP"]');
    if (radio) {
      const rect = radio.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + 10) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const expRadio = JSON.parse(r);
  if (!expRadio.error) {
    await clickAt(send, expRadio.x, expRadio.y);
    await sleep(500);
    console.log("Selected: I have some experience");
  }

  await clickNext(send, eval_);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
  console.log("\nStep 2 page:", r);

  // === STEP 2: Goal ===
  console.log("\n=== Step 2: Goal ===");
  // This step usually asks what you want to do - find work, etc.
  r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name,
        value: el.value,
        label: el.closest('label')?.textContent?.trim()?.substring(0, 60) || '',
        x: Math.round(el.getBoundingClientRect().x + 10),
        y: Math.round(el.getBoundingClientRect().y + 10)
      }));
    return JSON.stringify(radios);
  `);
  console.log("Options:", r);
  const step2Options = JSON.parse(r);

  // Select the first/primary option (usually "earn extra income" or "build my freelance career")
  if (step2Options.length > 0) {
    // Prefer "earn money" or "main income" type option
    const mainOpt = step2Options.find(o =>
      o.value.includes('MAIN') || o.value.includes('INCOME') || o.value.includes('SIDE')
    ) || step2Options[0];
    await clickAt(send, mainOpt.x, mainOpt.y);
    await sleep(500);
    console.log(`Selected: ${mainOpt.value}`);
  }

  await clickNext(send, eval_);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
  console.log("\nStep 3 page:", r);

  // === STEP 3: How did you hear about us ===
  console.log("\n=== Step 3 ===");
  r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name,
        value: el.value,
        label: el.closest('label')?.textContent?.trim()?.substring(0, 60) || '',
        x: Math.round(el.getBoundingClientRect().x + 10),
        y: Math.round(el.getBoundingClientRect().y + 10)
      }));
    const inputs = Array.from(document.querySelectorAll('input, textarea, [role="combobox"]'))
      .filter(el => el.offsetParent !== null && el.type !== 'radio')
      .map(el => ({
        tag: el.tagName,
        type: el.type,
        id: el.id,
        placeholder: el.placeholder?.substring(0, 40) || '',
        label: el.labels?.[0]?.textContent?.trim()?.substring(0, 40) || '',
        ariaLabel: el.getAttribute('aria-label')?.substring(0, 40) || ''
      }));
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 40)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify({ radios, inputs, btns });
  `);
  console.log("Elements:", r);
  const step3 = JSON.parse(r);

  if (step3.radios.length > 0) {
    // Select "Other" or "Word of mouth" or first option
    const opt = step3.radios.find(o => o.value.includes('OTHER') || o.value.includes('WORD')) || step3.radios[0];
    await clickAt(send, opt.x, opt.y);
    await sleep(500);
    console.log(`Selected: ${opt.value}`);
  }

  // Click Next / Continue
  const nextBtn = step3.btns.find(b =>
    b.text === 'Next' || b.text.includes('Continue') || b.text.includes('Get started')
  );
  if (nextBtn) {
    await clickAt(send, nextBtn.x, nextBtn.y);
    await sleep(5000);
  }

  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 600) })`);
  console.log("\nAfter step 3:", r);

  // Continue through remaining steps
  for (let step = 0; step < 10; step++) {
    r = await eval_(`
      const page = {
        url: location.href,
        step: location.href.split('/').pop().split('?')[0],
        bodySnip: document.body.innerText.substring(0, 200)
      };
      const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({ value: el.value, x: Math.round(el.getBoundingClientRect().x + 10), y: Math.round(el.getBoundingClientRect().y + 10) }));
      const inputs = Array.from(document.querySelectorAll('input:not([type="radio"]):not([type="hidden"]):not([type="checkbox"]), textarea'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          id: el.id, type: el.type, placeholder: el.placeholder?.substring(0, 40) || '',
          label: el.labels?.[0]?.textContent?.trim()?.substring(0, 40) || el.getAttribute('aria-label')?.substring(0, 40) || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      const nextBtn = Array.from(document.querySelectorAll('button'))
        .find(b => ['Next', 'Continue', 'Submit', 'Review', 'Save'].some(t => b.textContent.trim().includes(t)));
      const skipBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Skip'));
      return JSON.stringify({
        ...page,
        radios,
        inputs,
        hasNext: !!nextBtn,
        nextText: nextBtn?.textContent?.trim() || '',
        nextPos: nextBtn ? { x: Math.round(nextBtn.getBoundingClientRect().x + nextBtn.getBoundingClientRect().width/2), y: Math.round(nextBtn.getBoundingClientRect().y + nextBtn.getBoundingClientRect().height/2) } : null,
        hasSkip: !!skipBtn,
        skipPos: skipBtn ? { x: Math.round(skipBtn.getBoundingClientRect().x + skipBtn.getBoundingClientRect().width/2), y: Math.round(skipBtn.getBoundingClientRect().y + skipBtn.getBoundingClientRect().height/2) } : null
      });
    `);
    console.log(`\n--- Step ${step + 4} ---`);
    console.log(r);
    const state = JSON.parse(r);

    // If we're on the profile page or dashboard, we're done
    if (state.url.includes('profile') && !state.url.includes('create-profile')) break;
    if (state.url.includes('dashboard')) break;
    if (state.url.includes('best-matches')) break;

    // Skip for now if no required fields
    if (state.hasSkip && state.inputs.length === 0 && state.radios.length === 0) {
      console.log("Skipping...");
      await clickAt(send, state.skipPos.x, state.skipPos.y);
      await sleep(3000);
      ws.close(); await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
      continue;
    }

    // Select first radio if available
    if (state.radios.length > 0) {
      await clickAt(send, state.radios[0].x, state.radios[0].y);
      await sleep(500);
    }

    // Click Next if available
    if (state.hasNext) {
      await clickAt(send, state.nextPos.x, state.nextPos.y);
      await sleep(3000);
      ws.close(); await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    } else if (state.hasSkip) {
      await clickAt(send, state.skipPos.x, state.skipPos.y);
      await sleep(3000);
      ws.close(); await sleep(500);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    } else {
      console.log("No next/skip button found, stopping");
      break;
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
