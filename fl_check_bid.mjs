// Check if we can now bid on the data entry job
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

  // Navigate to the data entry job
  console.log("Navigating to data entry job...");
  await send("Page.navigate", { url: "https://www.freelancer.com/projects/data-management/Manual-Alphanumeric-Data-Entry/details" });
  await sleep(5000);

  // Check the page state - can we bid?
  let r = await eval_(`
    // Check for bid form
    const bidForm = document.querySelector('[class*="bid" i], [class*="Bid" i]');
    const bidInputs = Array.from(document.querySelectorAll('input, textarea'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        tag: i.tagName, type: i.type, id: i.id, name: i.name,
        placeholder: i.placeholder?.substring(0, 50),
        value: i.value?.substring(0, 30),
        label: i.labels?.[0]?.textContent?.trim()?.substring(0, 40) || ''
      }));

    // Check for "Complete your profile" block
    const completeProfile = document.body.innerText.includes('Complete your profile');
    const placeBid = document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Place Bid');
    const bidAmount = document.body.innerText.includes('Bid Amount') || document.body.innerText.includes('bid amount');

    // Look for any blocking messages
    const blockMessages = Array.from(document.querySelectorAll('[class*="alert" i], [class*="warning" i], [class*="block" i], [class*="restrict" i]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 10)
      .map(el => el.textContent.trim().substring(0, 100));

    const buttons = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null)
      .map(b => b.textContent.trim().substring(0, 40));

    return JSON.stringify({
      url: location.href,
      hasBidForm: !!bidForm,
      bidInputs,
      completeProfile,
      placeBid,
      bidAmount,
      blockMessages,
      buttons,
      preview: document.body.innerText.substring(0, 3000)
    });
  `);
  console.log("Job page state:", r);

  const state = JSON.parse(r);

  if (state.completeProfile) {
    console.log("\n=== STILL BLOCKED: Complete your profile ===");
    // Check what steps are needed
    r = await eval_(`
      // Find the complete profile section
      const section = Array.from(document.querySelectorAll('*'))
        .find(el => el.textContent.includes('Complete your profile') && el.textContent.length < 500);
      if (section) {
        return section.textContent.trim().substring(0, 400);
      }
      return 'section not found';
    `);
    console.log("Profile completion requirements:", r);

    // Look for a "complete profile" link or step list
    r = await eval_(`
      const steps = Array.from(document.querySelectorAll('a, button'))
        .filter(el => {
          const parent = el.closest('[class*="profile" i], [class*="complete" i], [class*="step" i]');
          return parent && el.offsetParent !== null;
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          href: el.href?.substring(0, 80) || ''
        }));
      return JSON.stringify(steps);
    `);
    console.log("Profile steps:", r);
  } else if (state.bidInputs.length > 0 || state.placeBid || state.bidAmount) {
    console.log("\n=== BID FORM AVAILABLE! ===");
    console.log("Inputs:", JSON.stringify(state.bidInputs));
  } else {
    console.log("\n=== Unknown state ===");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
