// Delete draft gig, then transform gig #1 (resume -> MCP server)
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.type === "page");
  if (!tab) throw new Error("No Fiverr tab found");
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

  // ===== Delete the draft gig =====
  console.log("=== Deleting draft gig ===");

  // Navigate to draft filter
  await eval_(`window.location.href = "https://www.fiverr.com/users/weberg619/manage_gigs?current_filter=draft"`);
  await sleep(4000);

  // First select the checkbox for the draft gig
  const checkResult = await eval_(`
    (function() {
      const checkbox = document.querySelector('.js-cbx-gig-row');
      if (checkbox) {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        checkbox.click();
        return 'checkbox checked';
      }
      return 'no checkbox found';
    })()
  `);
  console.log("Checkbox:", checkResult);
  await sleep(1000);

  // Now click the Delete button (it should be enabled after selecting)
  const deleteResult = await eval_(`
    (function() {
      // Try the batch delete button first
      const btns = Array.from(document.querySelectorAll('a, button'));
      const deleteBtn = btns.find(b => {
        const text = b.textContent.trim().toLowerCase();
        return text === 'delete' && !b.classList.contains('disabled');
      });
      if (deleteBtn) {
        deleteBtn.click();
        return 'clicked delete button';
      }

      // Try submitting the delete form directly
      const form = document.querySelector('form[action*="delete"]');
      if (form) {
        form.submit();
        return 'submitted delete form';
      }

      // Check button state
      const allDeleteBtns = btns.filter(b => b.textContent.trim().toLowerCase() === 'delete');
      return 'delete not clickable. Buttons: ' + allDeleteBtns.map(b => b.className.substring(0, 40) + ' disabled=' + b.classList.contains('disabled')).join('; ');
    })()
  `);
  console.log("Delete:", deleteResult);
  await sleep(3000);

  // Check for confirmation dialog
  const dialogResult = await eval_(`
    (function() {
      const dialog = document.querySelector('[class*="modal"], [class*="dialog"], [class*="popup"], [role="dialog"]');
      if (dialog) {
        const confirmBtn = dialog.querySelector('button, a');
        const buttons = Array.from(dialog.querySelectorAll('button, a')).map(b => b.textContent.trim());
        return 'dialog found. Buttons: ' + buttons.join(', ');
      }

      // Check if we got redirected
      return 'no dialog. URL: ' + window.location.href + ' | Title: ' + document.title;
    })()
  `);
  console.log("After delete:", dialogResult);

  // If there's a confirmation, click confirm
  if (dialogResult && dialogResult.includes('dialog found')) {
    const confirmResult = await eval_(`
      (function() {
        const dialog = document.querySelector('[class*="modal"], [class*="dialog"], [role="dialog"]');
        if (dialog) {
          const btns = Array.from(dialog.querySelectorAll('button, a'));
          const confirm = btns.find(b => {
            const t = b.textContent.trim().toLowerCase();
            return t.includes('yes') || t.includes('delete') || t.includes('confirm') || t.includes('ok');
          });
          if (confirm) {
            confirm.click();
            return 'confirmed delete: ' + confirm.textContent.trim();
          }
        }
        return 'no confirm button';
      })()
    `);
    console.log("Confirm:", confirmResult);
    await sleep(3000);
  }

  // Verify deletion
  const verifyUrl = await eval_(`window.location.href`);
  console.log("After deletion URL:", verifyUrl);

  const gigCount = await eval_(`
    (function() {
      const active = document.querySelector('a[href*="current_filter=active"]');
      const draft = document.querySelector('a[href*="current_filter=draft"]');
      return JSON.stringify({
        activeText: active?.textContent?.trim() || 'unknown',
        draftText: draft?.textContent?.trim() || 'unknown'
      });
    })()
  `);
  console.log("Gig counts:", gigCount);

  // ===== Now transform gig #1 =====
  console.log("\n=== Transforming Gig #1: Resume -> MCP Server ===");
  await eval_(`window.location.href = "https://www.fiverr.com/users/weberg619/manage_gigs/write-a-professional-resume-cv-and-cover-letter-that-gets-interviews/edit?step=0&tab=general"`);
  await sleep(5000);

  // Update title
  const newTitle = "build a custom MCP server to connect AI to your software";
  const titleResult = await eval_(`
    (function() {
      const textarea = document.querySelector('textarea');
      if (!textarea) return 'textarea not found';
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(textarea, '${newTitle}');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      textarea.dispatchEvent(new Event('change', { bubbles: true }));
      return 'title updated to: ' + textarea.value;
    })()
  `);
  console.log("Title:", titleResult);
  await sleep(1000);

  // Check current state
  const state = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.querySelector('textarea')?.value || 'unknown',
      category: document.body.innerText.match(/WRITING & TRANSLATION|PROGRAMMING & TECH|[A-Z &]+\\n[A-Z &]+/)?.[0] || 'unknown'
    })
  `);
  console.log("Current state:", state);
  console.log("\n=== Script complete. Title updated. Category change requires manual selection of PROGRAMMING & TECH -> AI SERVICES from dropdowns. ===");

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
