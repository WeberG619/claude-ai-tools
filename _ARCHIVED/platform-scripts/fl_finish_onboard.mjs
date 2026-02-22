// Finish onboarding steps: birthdate -> rest -> dashboard, then upload photo
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

async function clickButton(send, eval_, text) {
  const r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === ${JSON.stringify(text)} && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);
  if (!r) return false;
  const pos = JSON.parse(r);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  return true;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  // If on languages-and-birthdate, fill birthdate and continue
  if (r.includes('languages-and-birthdate')) {
    console.log("=== Languages & Birthdate page ===");

    // Check if birthdate already filled
    r = await eval_(`
      const dateInput = document.querySelector('input[placeholder*="MM" i], input[type="date"], input[placeholder*="birth" i]');
      if (dateInput) return JSON.stringify({ found: true, value: dateInput.value, placeholder: dateInput.placeholder });
      // Look for all inputs
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden')
        .map(i => ({ id: i.id, type: i.type, placeholder: i.placeholder, value: i.value }));
      return JSON.stringify({ found: false, inputs });
    `);
    console.log("Birthdate input:", r);

    const bdData = JSON.parse(r);
    if (bdData.found && !bdData.value) {
      // Fill birthdate
      r = await eval_(`
        const dateInput = document.querySelector('input[placeholder*="MM" i], input[type="date"]');
        if (dateInput) {
          dateInput.focus();
          return 'focused';
        }
        return 'not found';
      `);
      if (r === 'focused') {
        await sleep(200);
        await send("Input.insertText", { text: "06/19/1974" });
        await sleep(300);
        // Tab out
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
        await sleep(200);
        console.log("Birthdate filled: 06/19/1974");
      }
    } else if (bdData.found) {
      console.log("Birthdate already has value:", bdData.value);
    }

    // Click Next
    console.log("\nClicking Next...");
    await clickButton(send, eval_, "Next");
    await sleep(3000);
  }

  // Keep clicking through pages until we hit the dashboard
  for (let step = 0; step < 5; step++) {
    r = await eval_(`return location.href`);
    console.log(`\nStep ${step + 1} - URL: ${r}`);

    // Check if we're on the dashboard
    if (r.includes('/dashboard') || r.includes('/home')) {
      console.log("=== REACHED DASHBOARD ===");
      break;
    }

    // Check page content
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        buttons: Array.from(document.querySelectorAll('button'))
          .filter(b => b.offsetParent !== null)
          .map(b => b.textContent.trim().substring(0, 40)),
        preview: document.body.innerText.substring(0, 500)
      });
    `);
    console.log("Page:", r);

    const pageData = JSON.parse(r);

    // Close any modals first
    await eval_(`
      const close = document.querySelector('.ModalCloseButton, [class*="ModalClose"]');
      if (close) close.click();
    `);
    await sleep(500);

    // Try Next, Skip, or Continue buttons
    if (pageData.buttons.includes('Next')) {
      console.log("Clicking Next...");
      await clickButton(send, eval_, "Next");
    } else if (pageData.buttons.includes('Skip')) {
      console.log("Clicking Skip...");
      await clickButton(send, eval_, "Skip");
    } else if (pageData.buttons.includes('Continue')) {
      console.log("Clicking Continue...");
      await clickButton(send, eval_, "Continue");
    } else if (pageData.buttons.includes('Done')) {
      console.log("Clicking Done...");
      await clickButton(send, eval_, "Done");
    } else if (pageData.buttons.some(b => b.toLowerCase().includes('finish'))) {
      const finishBtn = pageData.buttons.find(b => b.toLowerCase().includes('finish'));
      console.log(`Clicking "${finishBtn}"...`);
      await clickButton(send, eval_, finishBtn);
    } else if (pageData.buttons.some(b => b.toLowerCase().includes('start'))) {
      const startBtn = pageData.buttons.find(b => b.toLowerCase().includes('start'));
      console.log(`Clicking "${startBtn}"...`);
      await clickButton(send, eval_, startBtn);
    } else {
      console.log("No clear next step. Trying to navigate to dashboard...");
      await send("Page.navigate", { url: "https://www.freelancer.com/dashboard" });
    }
    await sleep(3000);
  }

  // Now we should be on dashboard or close to it
  r = await eval_(`return location.href`);
  console.log("\n=== Current URL:", r, "===");

  // Navigate to profile edit page from dashboard
  console.log("\nLooking for profile edit link...");
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'))
      .filter(a => a.href && (
        a.href.includes('/u/') || a.href.includes('/profile') ||
        a.href.includes('settings') || a.href.includes('edit')
      ))
      .map(a => ({ text: a.textContent.trim().substring(0, 40), href: a.href.substring(0, 80) }));
    const avatarLinks = Array.from(document.querySelectorAll('[class*="avatar" i] a, a [class*="avatar" i], [class*="UserAvatar" i]'))
      .map(el => ({ tag: el.tagName, class: el.className?.toString()?.substring(0, 60), parent: el.parentElement?.href?.substring(0, 80) || '' }));
    return JSON.stringify({ links: links.slice(0, 10), avatarLinks });
  `);
  console.log("Profile links:", r);

  // Try navigating to the user profile edit directly
  console.log("\nNavigating to profile edit...");
  await send("Page.navigate", { url: "https://www.freelancer.com/u/BIMOpsStudio" });
  await sleep(4000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      fileInputs: document.querySelectorAll('input[type="file"]').length,
      editBtns: Array.from(document.querySelectorAll('a, button'))
        .filter(el => el.offsetParent !== null && (
          el.textContent.trim().toLowerCase().includes('edit') ||
          el.textContent.trim().toLowerCase().includes('upload') ||
          el.className?.toString()?.toLowerCase()?.includes('edit') ||
          el.className?.toString()?.toLowerCase()?.includes('pencil')
        ))
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 40),
          href: el.href?.substring(0, 80) || '',
          class: el.className?.toString()?.substring(0, 60)
        })),
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nProfile page:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
