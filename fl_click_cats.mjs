// Click categories and select skills on Freelancer.com
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

async function clickCategoryAndSkills(send, eval_, categoryName, skillsToSelect) {
  console.log(`\n--- Category: ${categoryName} ---`);

  // Find and click the category
  let r = await eval_(`
    const items = Array.from(document.querySelectorAll('*'));
    const cat = items.find(el => el.textContent.trim() === ${JSON.stringify(categoryName)} && el.offsetParent !== null);
    if (!cat) return 'category not found';
    // Get position for real click
    const rect = cat.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
  `);

  if (r === 'category not found') {
    console.log("  Category not found");
    return;
  }

  const pos = JSON.parse(r);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  console.log("  Clicked category");
  await sleep(1500);

  // Get available sub-skills
  r = await eval_(`
    // Look in the middle column for available skills
    const allEls = Array.from(document.querySelectorAll('*'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 2 && el.textContent.trim().length < 50);

    // Find skills in the second column (after "Select a category")
    const skillEls = allEls.filter(el => {
      const rect = el.getBoundingClientRect();
      return rect.x > 350 && rect.x < 700 && rect.y > 300; // Middle column
    });

    return JSON.stringify(skillEls.map(el => ({
      text: el.textContent.trim(),
      tag: el.tagName,
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    })).filter(s => !['No category selected', 'Select a category'].includes(s.text)));
  `);
  console.log("  Available skills:", r?.substring(0, 500));

  if (!r) return;
  const availableSkills = JSON.parse(r);

  // Click each desired skill
  for (const skillName of skillsToSelect) {
    const skill = availableSkills.find(s => s.text.toLowerCase().includes(skillName.toLowerCase()));
    if (skill) {
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: skill.x, y: skill.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: skill.x, y: skill.y, button: "left", clickCount: 1 });
      console.log(`  Selected: ${skill.text}`);
      await sleep(500);
    }
  }
}

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com/new-freelancer");
  console.log("Connected\n");

  // 1. Writing & Content
  await clickCategoryAndSkills(send, eval_, "Writing & Content", [
    "article", "content", "blog", "copywriting", "technical writing",
    "proofreading", "editing", "research", "report", "resume"
  ]);

  // 2. Data Entry & Admin
  await clickCategoryAndSkills(send, eval_, "Data Entry & Admin", [
    "data entry", "excel", "data processing", "spreadsheet", "typing"
  ]);

  // Check total skills selected
  console.log("\n=== Skills count ===");
  let r = await eval_(`
    const text = document.body.innerText;
    const match = text.match(/(\\d+) skills? selected/);
    return match ? match[0] : 'count not found. Preview: ' + text.substring(0, 300);
  `);
  console.log("  ", r);

  // Find and click Next
  console.log("\nLooking for Next button...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    console.log("  Found Next at", pos.x, pos.y);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
