// Transform Fiverr Gig #1: Resume -> MCP Server Development
// Step-by-step edit via CDP
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.type === "page");
  if (!tab) throw new Error("No Fiverr tab found");
  console.log(`Connected: ${tab.url}`);
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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) {
      console.error("JS Error:", JSON.stringify(r.exceptionDetails).substring(0, 300));
      return null;
    }
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, eval_ } = await connect();

  // Navigate to gig edit
  const editUrl = "https://www.fiverr.com/users/weberg619/manage_gigs/write-a-professional-resume-cv-and-cover-letter-that-gets-interviews/edit?step=0&tab=general";
  console.log("Navigating to edit page...");
  await eval_(`window.location.href = "${editUrl}"`);
  await sleep(5000);

  // ===== STEP 1: Update Title =====
  console.log("\n=== Updating Gig Title ===");
  const newTitle = "build a custom MCP server to connect AI to your software";
  const titleResult = await eval_(`
    (function() {
      const textarea = document.querySelector('textarea');
      if (!textarea) return 'textarea not found';

      // Clear and set using native setter for React
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(textarea, '${newTitle}');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      textarea.dispatchEvent(new Event('change', { bubbles: true }));

      return 'title set to: ' + textarea.value;
    })()
  `);
  console.log("Title:", titleResult);
  await sleep(1000);

  // ===== STEP 2: Change Category =====
  console.log("\n=== Changing Category ===");
  // First, click the category dropdown to open it
  const catResult = await eval_(`
    (function() {
      // Find all react-select containers
      const selects = document.querySelectorAll('[class*="react-select"]');
      const selectContainers = document.querySelectorAll('[class*="css-"][class*="container"]');

      // The category section - find the first react-select (main category)
      const catSelect = document.querySelector('#react-select-2-input');
      if (catSelect) {
        // Click the parent container to open dropdown
        const container = catSelect.closest('[class*="container"]') || catSelect.parentElement;
        container.click();
        catSelect.focus();
        return 'category dropdown opened';
      }

      // Try finding by label
      const labels = Array.from(document.querySelectorAll('label'));
      const catLabel = labels.find(l => l.textContent.includes('Category'));
      if (catLabel) {
        const sibling = catLabel.nextElementSibling || catLabel.parentElement.querySelector('[class*="select"]');
        if (sibling) sibling.click();
        return 'clicked category via label';
      }

      return 'category not found';
    })()
  `);
  console.log("Category:", catResult);
  await sleep(1000);

  // Look for category options
  const catOptions = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[class*="option"], [class*="menu"] [class*="option"], [id*="react-select"][id*="option"]'))
        .map(o => o.textContent.trim().substring(0, 50))
        .slice(0, 20)
    )
  `);
  console.log("Category options visible:", catOptions);

  // Type to search for Programming category
  await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (input) {
        input.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        setter.call(input, 'Programming');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    })()
  `);
  await sleep(2000);

  const catOptions2 = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[class*="option"], [id*="react-select"][id*="option"]'))
        .map(o => ({ text: o.textContent.trim().substring(0, 60), id: o.id || '' }))
        .slice(0, 15)
    )
  `);
  console.log("Filtered options:", catOptions2);

  // Select "PROGRAMMING & TECH" if visible
  const selectCat = await eval_(`
    (function() {
      const options = Array.from(document.querySelectorAll('[class*="option"], [id*="react-select"][id*="option"]'));
      const progOption = options.find(o => o.textContent.toLowerCase().includes('programming'));
      if (progOption) {
        progOption.click();
        return 'selected: ' + progOption.textContent.trim();
      }
      return 'programming option not found in ' + options.length + ' options';
    })()
  `);
  console.log("Selected category:", selectCat);
  await sleep(2000);

  // Check current state and look for subcategory
  const currentState = await eval_(`
    JSON.stringify({
      url: window.location.href,
      categoryText: document.querySelector('[class*="singleValue"]')?.textContent || 'unknown',
      subcatVisible: !!document.querySelector('#react-select-3-input'),
      pageText: document.body.innerText.substring(0, 300)
    })
  `);
  console.log("State after category:", currentState);

  // Now handle subcategory if visible
  const subCatResult = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-3-input');
      if (!input) return 'no subcategory input';
      const container = input.closest('[class*="container"]') || input.parentElement;
      container.click();
      input.focus();
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'AI');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      return 'typed AI in subcategory';
    })()
  `);
  console.log("Subcategory:", subCatResult);
  await sleep(2000);

  const subOptions = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[class*="option"], [id*="react-select-3"][id*="option"]'))
        .map(o => ({ text: o.textContent.trim().substring(0, 60), id: o.id || '' }))
        .slice(0, 10)
    )
  `);
  console.log("Subcategory options:", subOptions);

  // Select AI-related subcategory
  const selectSub = await eval_(`
    (function() {
      const options = Array.from(document.querySelectorAll('[class*="option"], [id*="react-select"][id*="option"]'));
      const aiOption = options.find(o => {
        const t = o.textContent.toLowerCase();
        return t.includes('ai') || t.includes('machine learning') || t.includes('chatbot') || t.includes('application');
      });
      if (aiOption) {
        aiOption.click();
        return 'selected: ' + aiOption.textContent.trim();
      }
      return 'ai option not found in ' + options.map(o => o.textContent.trim()).join(', ');
    })()
  `);
  console.log("Selected subcategory:", selectSub);
  await sleep(2000);

  // ===== STEP 3: Save overview =====
  console.log("\n=== Saving Overview ===");
  const saveResult = await eval_(`
    (function() {
      const buttons = Array.from(document.querySelectorAll('button, a'));
      const saveBtn = buttons.find(b => {
        const text = b.textContent.trim().toLowerCase();
        return text === 'save' || text === 'save & continue' || text === 'save & preview';
      });
      if (saveBtn) {
        saveBtn.click();
        return 'clicked: ' + saveBtn.textContent.trim();
      }
      return 'save button not found. Buttons: ' + buttons.map(b => b.textContent.trim().substring(0, 30)).filter(t => t.length > 0).slice(0, 10).join(', ');
    })()
  `);
  console.log("Save:", saveResult);
  await sleep(3000);

  // Final state
  const finalUrl = await eval_(`window.location.href`);
  console.log("\nFinal URL:", finalUrl);
  console.log("\n=== Overview step done. Check Fiverr to verify changes. ===");

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
