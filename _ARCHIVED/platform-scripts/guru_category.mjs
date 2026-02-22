// Click Engineering & Architecture category on Guru.com
// This time, prevent default form submit behavior
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru tab");

  const ws = new WebSocket(guru.webSocketDebuggerUrl);
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
  let { ws, send, eval_ } = await connect();

  // First, check what the title shows
  console.log("Checking current title...");
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input[type="text"].g-input'));
    const title = inputs.find(i => i.placeholder && i.placeholder.includes("App Development"));
    return title ? "Title: " + title.value : "title not found";
  `);
  console.log("  ", r);

  // Check if the category button click is handled by Angular/JS or ASP.NET
  console.log("\nInspecting category button behavior...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
      .find(b => b.textContent.includes("Engineering & Architecture"));
    if (!btn) return "button not found";

    // Check for Angular bindings
    const ngScope = typeof angular !== 'undefined' ? 'angular found' : 'no angular';

    // Check what events are on the button
    const evts = btn.getAttribute('ng-click') || btn.getAttribute('data-ng-click')
      || btn.getAttribute('@click') || btn.getAttribute('v-on:click') || '';

    // Check parent form action
    const form = btn.closest('form');

    // Try to find the JS framework handling this
    const hasReact = !!btn._reactInternalInstance || !!btn.__reactFiber$;
    const hasVue = !!btn.__vue__;

    return JSON.stringify({
      ngScope,
      eventAttrs: evts,
      formId: form?.id,
      formAction: form?.action,
      btnType: btn.type,
      react: hasReact,
      vue: hasVue,
      parentClasses: btn.parentElement?.className,
      // Check for AngularJS scope
      hasScope: typeof angular !== 'undefined' && !!angular.element(btn).scope()
    });
  `);
  console.log("  Button info:", r);

  // Try changing button type to "button" before clicking to prevent form submit
  console.log("\nChanging button type and clicking...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
      .find(b => b.textContent.includes("Engineering & Architecture"));
    if (!btn) return "not found";

    // Change type to prevent form submission
    btn.type = "button";

    // Click it
    btn.click();
    return "clicked (type changed to button)";
  `);
  console.log("  Result:", r);
  await sleep(3000);

  // Check what happened
  console.log("\nChecking page state after click...");
  r = await eval_(`
    // Check if new elements appeared (skill checkboxes, subcategories, etc.)
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null && c.id !== 'ProfileVisibility');

    // Check for any new sections
    const pageText = document.body.innerText;
    const hasNewContent = pageText.includes('Architecture') && pageText.includes('skill');

    // Check if the button is now highlighted/selected
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes("Engineering & Architecture"));
    const btnClass = btn?.className || '';

    // Check title is still there
    const titleInput = document.querySelector('input[placeholder*="App Development"]');

    return JSON.stringify({
      checkboxCount: checkboxes.length,
      titleStillThere: !!titleInput && titleInput.value,
      btnClass: btnClass,
      labels: checkboxes.map(c => {
        const lbl = c.closest('label') || c.parentElement;
        return lbl?.textContent?.trim()?.substring(0, 40) || '';
      }).slice(0, 20)
    }, null, 2);
  `);
  console.log("  State:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
