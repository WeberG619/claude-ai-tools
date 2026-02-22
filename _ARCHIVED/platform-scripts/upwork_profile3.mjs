// Fix work-preference step and continue profile creation
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

  // Check all checkboxes on work-preference page
  let r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        checked: el.checked,
        label: el.closest('label, [class*="card"]')?.textContent?.trim()?.substring(0, 60) || '',
        x: Math.round(el.getBoundingClientRect().x + 10),
        y: Math.round(el.getBoundingClientRect().y + 10)
      }));
    return JSON.stringify(cbs);
  `);
  console.log("Checkboxes:", r);
  const cbs = JSON.parse(r);

  // Check first two (find opportunities + package work)
  for (let i = 0; i < Math.min(cbs.length, 2); i++) {
    if (!cbs[i].checked) {
      await clickAt(send, cbs[i].x, cbs[i].y);
      await sleep(500);
      console.log(`Checked: ${cbs[i].label.substring(0, 40)}`);
    }
  }

  // Click "Next, create a profile"
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Next button:", r);
  const nextBtn = JSON.parse(r);
  if (!nextBtn.error) {
    await clickAt(send, nextBtn.x, nextBtn.y);
    await sleep(5000);
  }

  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Now we should be on the actual profile creation steps
  // Loop through remaining steps
  for (let step = 0; step < 20; step++) {
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: location.href.split('/').pop().split('?')[0],
        body: document.body.innerText.substring(0, 400)
      });
    `);
    console.log(`\n=== Step: ${JSON.parse(r).step} ===`);
    console.log(r);
    const page = JSON.parse(r);

    // Check if done
    if (page.url.includes('dashboard') || page.url.includes('best-matches') ||
        page.url.includes('feed') || page.body.includes('Your profile is ready')) {
      console.log("\n*** PROFILE COMPLETE! ***");
      break;
    }

    // Get page elements
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          id: el.id, type: el.type, value: el.value,
          placeholder: el.placeholder?.substring(0, 40) || '',
          label: el.labels?.[0]?.textContent?.trim()?.substring(0, 40) || el.getAttribute('aria-label')?.substring(0, 40) || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          value: el.value, checked: el.checked,
          label: el.closest('label')?.textContent?.trim()?.substring(0, 40) || '',
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + 10)
        }));
      const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          checked: el.checked,
          label: el.closest('label')?.textContent?.trim()?.substring(0, 40) || '',
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + 10)
        }));
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify({ inputs, radios, cbs, btns });
    `);
    const elements = JSON.parse(r);
    console.log("Inputs:", elements.inputs.length, "Radios:", elements.radios.length, "Buttons:", elements.btns.map(b => b.text).join(', '));

    // Handle based on page step
    const pageStep = page.step;

    if (pageStep === 'title' || page.body.includes('professional title')) {
      // Set title
      const titleInput = elements.inputs.find(i => i.label?.includes('title') || i.placeholder?.includes('title'));
      if (titleInput) {
        await clickAt(send, titleInput.x, titleInput.y);
        await sleep(200);
        await send("Input.insertText", { text: "BIM Specialist | Technical Writer | Data Entry Expert" });
        await sleep(500);
        console.log("Title set");
      }
    } else if (pageStep === 'categories' || page.body.includes('kind of work')) {
      // Select work categories - click suggestions
      const searchInput = elements.inputs[0];
      if (searchInput) {
        await clickAt(send, searchInput.x, searchInput.y);
        await sleep(200);
        await send("Input.insertText", { text: "Writing" });
        await sleep(2000);
        // Click first suggestion
        r = await eval_(`
          const suggestions = Array.from(document.querySelectorAll('[class*="suggestion"], [role="option"], [class*="result"], li'))
            .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60)
            .map(el => ({
              text: el.textContent.trim(),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(suggestions.slice(0, 5));
        `);
        console.log("Suggestions:", r);
        const suggs = JSON.parse(r);
        if (suggs.length > 0) {
          await clickAt(send, suggs[0].x, suggs[0].y);
          await sleep(500);
        }
      }
    } else if (pageStep === 'skills' || page.body.includes('skills')) {
      // Skip to add skills later
    } else if (pageStep === 'rate' || page.body.includes('hourly rate') || page.body.includes('per hour')) {
      // Set hourly rate
      const rateInput = elements.inputs.find(i => i.type === 'number' || i.label?.includes('rate') || i.placeholder?.includes('$'));
      if (rateInput) {
        await clickAt(send, rateInput.x, rateInput.y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await sleep(50);
        await send("Input.insertText", { text: "25" });
        await sleep(500);
        console.log("Rate set: $25/hr");
      }
    } else if (pageStep === 'bio' || pageStep === 'overview' || page.body.includes('bio') || page.body.includes('overview')) {
      // Set bio/overview
      const bioInput = elements.inputs.find(i => i.tag === 'TEXTAREA' || i.type === 'textarea');
      if (bioInput) {
        await clickAt(send, bioInput.x, bioInput.y);
        await sleep(200);
        await send("Input.insertText", { text: "Experienced BIM specialist and technical professional offering high-quality writing, data entry, and document management services. I bring attention to detail and technical expertise to every project, ensuring accurate, professional results delivered on time." });
        await sleep(500);
        console.log("Bio set");
      }
    }

    // Select first unchecked radio if any
    if (elements.radios.length > 0) {
      const unchecked = elements.radios.find(r => !r.checked);
      if (unchecked) {
        await clickAt(send, unchecked.x, unchecked.y);
        await sleep(500);
      }
    }

    // Find Next/Continue/Skip button
    const next = elements.btns.find(b =>
      b.text === 'Next' || b.text.includes('Next,') || b.text.includes('Continue') ||
      b.text.includes('Review') || b.text.includes('Submit')
    );
    const skip = elements.btns.find(b => b.text.includes('Skip'));

    if (next) {
      await sleep(500);
      await clickAt(send, next.x, next.y);
      await sleep(3000);
    } else if (skip) {
      await clickAt(send, skip.x, skip.y);
      await sleep(3000);
    } else {
      console.log("No navigation button found");
      break;
    }

    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
