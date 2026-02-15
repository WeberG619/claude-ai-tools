// Try different approaches to save Fiverr pricing and advance
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
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // First, check if extra service prices are required
  console.log("=== Checking extra services ===");
  let r = await eval_(`
    // Check extra service sections - they have checkboxes and price inputs
    const extras = [];

    // Additional hours checkbox
    const addHoursCheckbox = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        checked: el.checked,
        class: (el.className?.toString() || '').substring(0, 40),
        labelText: el.closest('label')?.textContent?.trim()?.substring(0, 40) || '',
        parentText: el.parentElement?.textContent?.trim()?.substring(0, 40) || '',
        y: Math.round(el.getBoundingClientRect().y)
      }));

    // Look for price inputs in the extras area (y > 1000)
    const extraPrices = Array.from(document.querySelectorAll('.price-stepper, input[type="number"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 800)
      .map(el => ({
        value: el.value || '',
        placeholder: el.placeholder || '',
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        required: el.required,
        name: el.name || ''
      }));

    // Get hidden field values for extras
    const hiddenExtras = {
      pkg1_additionalHoursPrice: document.querySelector('input[name="gig[packages][1][upgrades_per_package][100000][price]"]')?.value,
      pkg2_additionalHoursPrice: document.querySelector('input[name="gig[packages][2][upgrades_per_package][100000][price]"]')?.value,
      pkg3_additionalHoursPrice: document.querySelector('input[name="gig[packages][3][upgrades_per_package][100000][price]"]')?.value,
      extraFastActive: document.querySelector('input[name="gig[gig_items_attributes][8765][active]"]')?.value,
    };

    return JSON.stringify({ checkboxes: addHoursCheckbox, extraPrices, hiddenExtras });
  `);
  console.log(r);

  // The "Additional hours" and "Extra fast delivery" checkboxes are checked by default
  // They might require prices to be filled in
  // Let me check if any extra price inputs are empty and required

  const state = JSON.parse(r);
  console.log("\nCheckboxes:", state.checkboxes.map(c => `${c.labelText || c.parentText}: ${c.checked}`));
  console.log("Extra prices:", state.extraPrices.map(p => `y=${p.y} val="${p.value}" class=${p.class}`));
  console.log("Hidden extras:", state.hiddenExtras);

  // The "Additional Hours" is checked and might need prices for each package
  // And "Extra fast delivery" is also checked
  // Let's uncheck both extras to simplify, or fill in their prices

  // Strategy: Uncheck the "Additional hours" and "Extra fast delivery" checkboxes
  // to remove the requirement for extra prices
  console.log("\n=== Disabling extra services ===");

  r = await eval_(`
    // Find and uncheck "Additional hours" and "Extra fast delivery" checkboxes
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null && !el.className.includes('pkgs-toggler'));

    const results = [];
    for (const cb of checkboxes) {
      const label = cb.closest('label')?.textContent?.trim() || '';
      const parentText = cb.parentElement?.textContent?.trim()?.substring(0, 40) || '';
      if (cb.checked && (label.includes('Additional') || label.includes('Extra') || parentText.includes('Additional') || parentText.includes('Extra'))) {
        cb.click();
        results.push({ text: label || parentText, nowChecked: cb.checked });
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Unchecked:", r);
  await sleep(500);

  // Now try saving
  console.log("\n=== Saving ===");

  // Enable network monitoring to see if form submission happens
  await send("Network.enable");

  // Click Save & Continue
  r = await eval_(`
    const btn = document.querySelector('.btn-submit');
    if (btn) btn.click();
    return btn ? 'clicked' : 'not found';
  `);
  console.log("Save click:", r);

  // Wait for network request
  await sleep(5000);

  // Check if page changed
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim() || '',
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("After save:", r);

  const afterSave = JSON.parse(r);
  if (afterSave.step === 'Pricing') {
    console.log("\nStill on Pricing. Let me try form submit directly...");

    // Try submitting the form programmatically
    r = await eval_(`
      const form = document.querySelector('#gig-edit-create-form');
      if (!form) return 'no form';

      // Check if there's a jQuery submit handler
      const hasJQuery = typeof jQuery !== 'undefined' || typeof $ !== 'undefined';

      // Try triggering the submit event
      const evt = new Event('submit', { bubbles: true, cancelable: true });
      const result = form.dispatchEvent(evt);

      return JSON.stringify({
        formFound: true,
        hasJQuery,
        submitEventResult: result,
        formAction: form.action
      });
    `);
    console.log("Form submit attempt:", r);
    await sleep(5000);

    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
    console.log("After form submit:", r);

    // If still stuck, try clicking the "Description & FAQ" breadcrumb directly
    const afterSubmit = JSON.parse(r);
    if (afterSubmit.step === 'Pricing') {
      console.log("\nStill on pricing. Trying to navigate via breadcrumb...");

      // Try clicking "Description & FAQ" in the step navigation
      r = await eval_(`
        const crumbs = Array.from(document.querySelectorAll('.crumb-content'));
        const descCrumb = crumbs.find(c => c.textContent.includes('Description'));
        if (descCrumb) {
          const link = descCrumb.closest('a') || descCrumb.closest('span') || descCrumb;
          link.click();
          return 'clicked Description crumb';
        }
        // Try the nav items
        const navItems = Array.from(document.querySelectorAll('.nav-crumb'));
        return JSON.stringify(navItems.map(n => n.textContent.trim().substring(0, 30)));
      `);
      console.log("Breadcrumb click:", r);
      await sleep(3000);

      r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
      console.log("After breadcrumb:", r);

      // If still stuck, try the just "Save" button (not "Save & Continue")
      const afterCrumb = JSON.parse(r);
      if (afterCrumb.step === 'Pricing') {
        console.log("\nTrying just Save button...");
        r = await eval_(`
          const saveBtn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.trim() === 'Save' && !b.textContent.includes('Continue') && !b.textContent.includes('Preview'));
          if (saveBtn) {
            saveBtn.click();
            return 'clicked Save only';
          }
          return 'Save not found';
        `);
        console.log(r);
        await sleep(5000);

        r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
        console.log("After Save:", r);

        // Try navigating directly
        console.log("\nNavigating directly to step 3...");
        r = await eval_(`
          // Navigate by changing wizard param
          window.location.href = location.href.replace('wizard=1', 'wizard=2');
          return 'navigating';
        `);
        console.log(r);
        await sleep(5000);

        // Reconnect since page navigated
        try {
          r = await eval_(`return JSON.stringify({ url: location.href })`);
          console.log("After navigate:", r);
        } catch(e) {
          console.log("Connection lost (page navigated). Reconnecting...");
        }
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
