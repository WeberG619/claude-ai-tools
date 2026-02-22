// Skip linked accounts page and continue through Freelancer setup
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function clickButton(send, eval_, buttonText) {
  const r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, a'));
    const btn = btns.find(b => b.textContent.trim().includes(${JSON.stringify(buttonText)}) && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    return null;
  `);
  if (!r) { console.log(`  Button "${buttonText}" not found`); return false; }
  const pos = JSON.parse(r);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  console.log(`  Clicked "${pos.text}" at ${Math.round(pos.x)}, ${Math.round(pos.y)}`);
  return true;
}

async function getPageState(eval_) {
  const r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  return JSON.parse(r);
}

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  let state = await getPageState(eval_);
  console.log("Page:", state.url);
  console.log("Content:", state.preview.substring(0, 200));

  // Click Skip on linked accounts
  if (state.url.includes("linked-accounts")) {
    console.log("\nSkipping linked accounts...");
    await clickButton(send, eval_, "Skip");
    await sleep(4000);
    state = await getPageState(eval_);
    console.log("\nNew page:", state.url);
    console.log("Content:", state.preview.substring(0, 500));
  }

  // Handle whatever page comes next
  for (let step = 0; step < 5; step++) {
    state = await getPageState(eval_);
    console.log(`\n=== Step ${step + 1}: ${state.url} ===`);
    console.log(state.preview.substring(0, 800));

    // Check if we need to fill anything or just skip/next
    if (state.url.includes("profile-photo") || state.url.includes("photo")) {
      console.log("\nProfile photo page - skipping...");
      const skipped = await clickButton(send, eval_, "Skip");
      if (!skipped) await clickButton(send, eval_, "Next");
      await sleep(3000);
      continue;
    }

    if (state.url.includes("headline") || state.preview.includes("headline")) {
      console.log("\nHeadline page - filling...");
      await eval_(`
        const input = document.querySelector('input[type="text"], textarea');
        if (input) {
          input.focus();
          input.value = 'Professional Writer & Data Specialist | AI-Enhanced Workflow';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        return input ? 'filled' : 'not found';
      `);
      await clickButton(send, eval_, "Next");
      await sleep(3000);
      continue;
    }

    if (state.url.includes("hourly-rate") || state.preview.includes("hourly rate")) {
      console.log("\nHourly rate page - setting $35/hr...");
      await eval_(`
        const input = document.querySelector('input[type="number"], input[type="text"]');
        if (input) {
          input.focus();
          input.value = '35';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        return input ? 'set' : 'not found';
      `);
      await clickButton(send, eval_, "Next");
      await sleep(3000);
      continue;
    }

    if (state.url.includes("experience") || state.preview.includes("experience")) {
      console.log("\nExperience page - filling...");
      // Fill experience details
      const filled = await eval_(`
        const inputs = document.querySelectorAll('input, textarea');
        return JSON.stringify(Array.from(inputs).map(i => ({
          type: i.type, placeholder: i.placeholder, name: i.name, id: i.id
        })));
      `);
      console.log("  Form fields:", filled);

      // Try Skip if available
      const skipped = await clickButton(send, eval_, "Skip");
      if (!skipped) await clickButton(send, eval_, "Next");
      await sleep(3000);
      continue;
    }

    // Generic: try Next or Skip
    if (state.preview.includes("Skip")) {
      console.log("\nTrying Skip...");
      const skipped = await clickButton(send, eval_, "Skip");
      if (skipped) { await sleep(3000); continue; }
    }

    if (state.preview.includes("Next")) {
      console.log("\nTrying Next...");
      await clickButton(send, eval_, "Next");
      await sleep(3000);
      continue;
    }

    // If we can't find Next/Skip, we're probably done
    console.log("\nNo more Next/Skip buttons - setup may be complete");
    break;
  }

  // Final state
  state = await getPageState(eval_);
  console.log("\n=== FINAL STATE ===");
  console.log("URL:", state.url);
  console.log("Preview:", state.preview.substring(0, 1000));

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
