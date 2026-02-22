// Dismiss camera modal, look for file upload alternative
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // First dismiss the camera modal by clicking "No, thanks"
  let r = await eval_(`
    const noThanks = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'No, thanks');
    if (noThanks) {
      const rect = noThanks.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    console.log("Clicking 'No, thanks'...");
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(2000);
  }

  // Now check what the page looks like after dismissing camera
  r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="Modal" i]'))
      .filter(el => window.getComputedStyle(el).display !== 'none')
      .map(el => ({
        tag: el.tagName,
        class: el.className?.toString()?.substring(0, 60),
        text: el.textContent?.trim()?.substring(0, 100)
      }));
    const buttons = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({
        text: b.textContent.trim().substring(0, 40),
        class: b.className?.toString()?.substring(0, 50),
        rect: (() => { const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; })()
      }));

    // Look for any element with "upload" or "browse" text
    const uploadEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const t = el.textContent?.trim()?.toLowerCase() || '';
        return el.offsetParent !== null && el.childElementCount === 0 &&
          (t.includes('upload') || t.includes('browse') || t.includes('choose file') || t.includes('select file')) &&
          t.length < 50;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; })()
      }));

    return JSON.stringify({
      url: location.href,
      fileInputs: fileInputs.length,
      modals,
      buttons,
      uploadEls,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("After dismissing camera modal:", r);

  const state = JSON.parse(r);

  // If there's an upload option, click it
  if (state.uploadEls.length > 0) {
    const uploadEl = state.uploadEls[0];
    console.log(`\nClicking "${uploadEl.text}"...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: uploadEl.rect.x, y: uploadEl.rect.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: uploadEl.rect.x, y: uploadEl.rect.y, button: "left", clickCount: 1 });
    await sleep(2000);
  }

  // Check if there's a different photo upload flow now
  // Maybe the photo area changed after dismissing camera
  r = await eval_(`
    const photoArea = document.querySelector('.ProfileDetailsPhotoAndName-photo, [class*="photo" i]');
    const photoContent = photoArea?.innerHTML?.substring(0, 500);
    const allClickable = Array.from(document.querySelectorAll('a, button, [role="button"], [class*="btn" i], [class*="Btn" i]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 40),
        class: el.className?.toString()?.substring(0, 60),
        href: el.href?.substring(0, 80) || '',
        rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height }; })()
      }));
    return JSON.stringify({
      photoContent,
      clickables: allClickable,
      fileInputs: Array.from(document.querySelectorAll('input[type="file"]')).length
    });
  `);
  console.log("\nPhoto area & clickables:", r);

  // Try clicking photo area again (might have different behavior after camera denied)
  console.log("\nTrying PhotoFloatingBtn again...");
  r = await eval_(`
    const btn = document.querySelector('.PhotoFloatingBtn');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(2000);

    // Check what appeared this time
    r = await eval_(`
      const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="Modal" i]'))
        .filter(el => window.getComputedStyle(el).display !== 'none')
        .map(el => el.textContent?.trim()?.substring(0, 200));
      const fileInputs = document.querySelectorAll('input[type="file"]').length;
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => b.textContent.trim());
      const actionSheet = document.querySelector('[class*="action-sheet" i], [class*="ActionSheet" i], [class*="bottom-sheet" i], [class*="BottomSheet" i], [class*="menu" i]');
      return JSON.stringify({
        modals,
        fileInputs,
        buttons: btns,
        actionSheet: actionSheet ? actionSheet.textContent?.trim()?.substring(0, 100) : null,
        preview: document.body.innerText.substring(0, 1000)
      });
    `);
    console.log("After 2nd click on PhotoFloatingBtn:", r);
  }

  // If still no file input, try the "Next" button approach -
  // maybe we can skip the photo and complete profile another way
  console.log("\n--- Alternative: Try skipping photo with Next ---");
  r = await eval_(`
    const nextBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (nextBtn) {
      const rect = nextBtn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, disabled: nextBtn.disabled });
    }
    return null;
  `);
  console.log("Next button:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
