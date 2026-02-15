// Fill Guru.com service form via CDP - v2
// Handles ASP.NET postback correctly
const CDP_HTTP = "http://localhost:9222";

async function connect() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru tab found!");

  const ws = new WebSocket(guru.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", reject);
  });

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

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  let { ws, send, eval_ } = await connect();
  console.log("Connected");

  // Step 1: Navigate to edit profile services page
  console.log("\n=== Step 1: Navigate to Services page ===");
  await send("Page.navigate", { url: "https://www.guru.com/pro/ProfileBuild.aspx?tab=5&pscount=0" });
  await sleep(4000);

  // Step 2: Click "Add a Service" radio
  console.log("\n=== Step 2: Select 'Add a Service' ===");
  let r = await eval_(`
    const radio = document.getElementById('radioSvc');
    if (radio) { radio.click(); return "clicked radio"; }
    return "radio not found - page text: " + document.body.innerText.substring(0, 200);
  `);
  console.log("  Result:", r);
  await sleep(2000);

  // Step 3: Inspect the form structure more carefully
  console.log("\n=== Step 3: Inspect form ===");
  r = await eval_(`
    // Get the full form HTML structure (simplified)
    const form = document.getElementById('aspnetForm');
    if (!form) return "no form found";

    // Get all inputs with their context
    const allEls = Array.from(form.querySelectorAll('input, select, textarea, [contenteditable]'));
    const visible = allEls.filter(el => el.offsetParent !== null || el.type === 'hidden');

    // Get the category section specifically
    const catSection = form.innerHTML.match(/category|skill|Engineering/gi);

    return JSON.stringify({
      visibleElements: visible.map(el => ({
        tag: el.tagName, type: el.type, id: el.id, name: el.name,
        placeholder: el.placeholder || '',
        value: (el.value || '').substring(0, 50),
        contentEditable: el.contentEditable === 'true',
        classes: el.className.substring(0, 100),
        parentId: el.parentElement?.id || '',
        parentClass: el.parentElement?.className?.substring(0, 50) || ''
      })),
      categoryMatches: catSection?.length || 0
    }, null, 2);
  `);
  console.log("  Form:", r);

  // Step 4: Get the category buttons - check if they're real submit buttons or just styled
  console.log("\n=== Step 4: Check category buttons ===");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"], .btn'));
    const catBtns = btns.filter(b => {
      const txt = (b.textContent || b.value || '').trim();
      return ['Programming', 'Design', 'Writing', 'Administrative', 'Business', 'Sales', 'Engineering', 'Legal', 'Education'].some(c => txt.includes(c));
    });
    return JSON.stringify(catBtns.map(b => ({
      tag: b.tagName,
      type: b.type,
      text: (b.textContent || b.value || '').trim().substring(0, 40),
      id: b.id,
      name: b.name,
      onclick: b.getAttribute('onclick')?.substring(0, 100) || '',
      classes: b.className.substring(0, 100),
      formAction: b.getAttribute('formaction') || '',
      ngClick: b.getAttribute('ng-click') || b.getAttribute('data-ng-click') || '',
      dataAction: b.getAttribute('data-action') || ''
    })));
  `);
  console.log("  Category buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
