// Click "Attach photo" in crop dialog, re-set fields, then Review
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

  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

  // Step 1: Check if crop dialog is still open
  let r = await eval_(`
    const attachBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Attach photo' && b.offsetParent !== null);
    const canvas = document.querySelector('canvas');
    return JSON.stringify({ hasAttach: !!attachBtn, hasCanvas: !!canvas });
  `);
  console.log("Dialog state:", r);
  const dialogState = JSON.parse(r);

  if (!dialogState.hasAttach) {
    // Need to re-upload the photo
    console.log("No crop dialog open. Re-uploading photo...");

    await send("DOM.enable");

    // Click Upload photo
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Upload photo'));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    const btnPos = JSON.parse(r);
    if (!btnPos.error) {
      await clickAt(send, btnPos.x, btnPos.y);
      await sleep(1500);
    }

    // Find and set file on file input
    const objResult = await send("Runtime.evaluate", {
      expression: `document.querySelector('input[type="file"]')`,
      returnByValue: false
    });
    if (objResult.result?.objectId) {
      const nodeDesc = await send("DOM.describeNode", {
        objectId: objResult.result.objectId
      });
      if (nodeDesc.node?.backendNodeId) {
        await send("DOM.setFileInputFiles", {
          backendNodeId: nodeDesc.node.backendNodeId,
          files: [photoPath]
        });
        console.log("Photo file set");
        await sleep(3000);
      }
    }
  }

  // Step 2: Click "Attach photo"
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Attach photo' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no Attach photo button' });
  `);
  console.log("Attach photo button:", r);
  const attachBtn = JSON.parse(r);

  if (!attachBtn.error) {
    await clickAt(send, attachBtn.x, attachBtn.y);
    console.log("Clicked Attach photo!");
    await sleep(3000);

    // Check if photo was saved
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
        .map(el => el.textContent.trim().substring(0, 80));
      const imgs = Array.from(document.querySelectorAll('img'))
        .filter(el => el.getBoundingClientRect().width > 40 && !el.src.includes('icon') && !el.src.includes('svg'))
        .map(el => ({ src: el.src.substring(0, 60), w: Math.round(el.getBoundingClientRect().width) }));
      return JSON.stringify({ errors, imgs });
    `);
    console.log("After attach:", r);
  }

  // Step 3: Re-set form fields (they may have been cleared by page navigation)
  console.log("\nRe-setting form fields...");
  r = await eval_(`
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const fields = [
      ['mm/dd/yyyy', '03/18/1974'],
      ['Enter street address', '619 Hopkins Rd'],
      ['Enter city', 'Sandpoint'],
      ['Enter state/province', 'ID'],
      ['Enter ZIP/Postal code', '83864'],
      ['Enter number', '2083551234']
    ];
    const results = [];
    for (const [ph, val] of fields) {
      const inp = Array.from(document.querySelectorAll('input')).find(el => el.placeholder === ph);
      if (inp) {
        if (!inp.value || inp.value !== val) {
          setter.call(inp, val);
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          results.push(ph + ': SET');
        } else {
          results.push(ph + ': OK');
        }
      } else {
        results.push(ph + ': NOT FOUND');
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Fields:", r);

  // Step 4: Click Review
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify(errors);
  `);
  console.log("Errors:", r);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
  const reviewBtn = JSON.parse(r);
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked Review");
    await sleep(5000);

    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`return JSON.stringify({
      url: location.href, step: location.href.split('/').pop().split('?')[0],
      body: document.body.innerText.substring(0, 500)
    })`);
    const page = JSON.parse(r);
    console.log("\n=== " + page.step + " ===");
    console.log(page.body.substring(0, 350));

    // If we advanced, look for Submit
    if (page.step !== 'location') {
      console.log("\nADVANCED! Looking for Submit...");
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null && !el.textContent.includes('Skip to'))
          .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
        return JSON.stringify(btns);
      `);
      console.log("Buttons:", r);
      const btns = JSON.parse(r);
      const submit = btns.find(b => b.text.includes('Submit') || b.text.includes('Publish'));
      if (submit) {
        await clickAt(send, submit.x, submit.y);
        console.log(`Clicked: ${submit.text}`);
        await sleep(8000);
        ws.close(); await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
        console.log("\n*** FINAL:", r);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
