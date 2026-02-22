// Save Guru.com service, then handle category via postback
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
  console.log("Connected\n");

  // Step 1: Verify form is filled
  console.log("Step 1: Verify form state...");
  let r = await eval_(`
    const title = document.querySelector('input[placeholder*="App Development"]');
    const editor = document.querySelector('.fr-element');
    const rates = document.querySelectorAll('.rateHourInput__minmax--input');
    return JSON.stringify({
      title: title?.value || 'empty',
      descLength: editor?.innerHTML?.length || 0,
      rate1: rates[0]?.value || 'empty',
      rate2: rates[1]?.value || 'empty'
    });
  `);
  console.log("  ", r);

  // Step 2: Try clicking Engineering & Architecture using __doPostBack
  // (proper ASP.NET way - but need to find the control name)
  console.log("\nStep 2: Try ASP.NET-style category selection...");
  r = await eval_(`
    // Check if there's an Angular scope managing the categories
    const catBtns = Array.from(document.querySelectorAll('button[type="submit"]'));
    const eng = catBtns.find(b => b.textContent.includes("Engineering"));
    if (!eng) return "button not found";

    // Check for Angular
    if (typeof angular !== 'undefined') {
      const scope = angular.element(eng).scope();
      return "Angular scope found: " + JSON.stringify(Object.keys(scope || {}));
    }

    // Check for AngularJS ng- attributes
    const wrapper = eng.closest('[ng-controller], [ng-app], [data-ng-controller]');

    // Look at the click handler through getEventListeners equivalent
    const parent = eng.parentElement;
    return JSON.stringify({
      parentTag: parent?.tagName,
      parentId: parent?.id,
      parentClass: parent?.className?.substring(0, 80),
      parentNgClick: parent?.getAttribute('ng-click'),
      wrapperTag: wrapper?.tagName,
      wrapperCtrl: wrapper?.getAttribute('ng-controller'),
      // Check for any React data
      reactKeys: eng._reactProps ? Object.keys(eng._reactProps) : [],
      // Check siblings
      siblingCount: parent?.children?.length,
    });
  `);
  console.log("  ", r);

  // Step 3: Try to use the API directly
  console.log("\nStep 3: Check for API calls...");
  r = await eval_(`
    // Check for existing XHR/fetch interceptors or API calls in the page
    const scripts = Array.from(document.querySelectorAll('script:not([src])'));
    let apiUrls = [];
    for (const s of scripts) {
      const text = s.textContent;
      const matches = text.match(/api\/v1[^\s'"]+/g) || [];
      apiUrls = apiUrls.concat(matches);
    }

    // Also check for WebAPIURL
    const apiBase = document.getElementById('WebAPIURL')?.value || '';

    return JSON.stringify({
      apiBase,
      apiUrls: [...new Set(apiUrls)].slice(0, 10)
    });
  `);
  console.log("  ", r);

  // Step 4: Click Publish directly and see what validation errors we get
  console.log("\nStep 4: Click Publish to see validation requirements...");
  r = await eval_(`
    const publishBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Publish');
    if (!publishBtn) return "Publish button not found";
    publishBtn.click();
    return "clicked Publish";
  `);
  console.log("  ", r);
  await sleep(3000);

  // Check for validation messages
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('.error, .validation, .alert, [class*="error"], [class*="valid"], [class*="warning"], [class*="required"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 100));

    const toasts = Array.from(document.querySelectorAll('[class*="toast"], [class*="notify"], [class*="message"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 100));

    return JSON.stringify({
      errors: errors.filter(e => e.length > 0).slice(0, 10),
      toasts: toasts.filter(t => t.length > 0).slice(0, 5),
      alertText: document.querySelector('.alert')?.textContent?.trim()?.substring(0, 200) || '',
      // Check if page changed
      url: location.href,
      bodyPreview: document.body.innerText.substring(0, 500)
    }, null, 2);
  `);
  console.log("  Validation:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
