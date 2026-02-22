// Check why Save button isn't working on employment dialog
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const res = await fetch(`${CDP}/json`);
  const tabs = await res.json();
  const page = tabs.find(t => t.type === 'page' && t.url.includes('upwork.com'));
  if (!page) { console.log('No Upwork tab'); process.exit(1); }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));

  let id = 1;
  const pending = new Map();
  ws.addEventListener('message', e => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
    }
  });
  const ev = async (expr) => {
    const r = await new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
    });
    return r.result?.value;
  };

  // Check the Save button state
  console.log('=== SAVE BUTTON STATE ===');
  const saveState = await ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'No modal found';
      const saveBtn = [...modal.querySelectorAll('button')].find(b => b.textContent.trim().toLowerCase() === 'save');
      if (!saveBtn) return 'No save button';
      return JSON.stringify({
        text: saveBtn.textContent.trim(),
        disabled: saveBtn.disabled,
        ariaDisabled: saveBtn.getAttribute('aria-disabled'),
        className: saveBtn.className,
        style: saveBtn.style.cssText,
        pointerEvents: getComputedStyle(saveBtn).pointerEvents,
        opacity: getComputedStyle(saveBtn).opacity,
        cursor: getComputedStyle(saveBtn).cursor,
        parentDisabled: saveBtn.parentElement?.disabled
      });
    })()
  `);
  console.log(saveState);

  // Check for validation errors
  console.log('\n=== VALIDATION ERRORS ===');
  const errors = await ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'No modal';
      const errorEls = [...modal.querySelectorAll('[class*="error"], [class*="invalid"], [class*="alert"], [role="alert"], [class*="danger"], [class*="warning"], .text-danger, .text-error')];
      const ariaInvalid = [...modal.querySelectorAll('[aria-invalid="true"]')];
      const required = [...modal.querySelectorAll('[required], [aria-required="true"]')];
      return JSON.stringify({
        errorMessages: errorEls.map(el => el.textContent.trim()).filter(Boolean),
        invalidFields: ariaInvalid.map(el => el.tagName + '|' + el.name + '|' + el.placeholder + '|' + el.value),
        requiredFields: required.map(el => el.tagName + '|' + el.name + '|' + el.placeholder + '|val=' + el.value)
      });
    })()
  `);
  console.log(errors);

  // Check all input values in the modal
  console.log('\n=== ALL INPUT VALUES ===');
  const inputValues = await ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'No modal';
      const inputs = [...modal.querySelectorAll('input, textarea, select')];
      return JSON.stringify(inputs.map(i => ({
        tag: i.tagName,
        type: i.type,
        name: i.name,
        id: i.id,
        placeholder: i.placeholder,
        value: i.value,
        checked: i.checked,
        ariaInvalid: i.getAttribute('aria-invalid'),
        required: i.required || i.getAttribute('aria-required'),
        readOnly: i.readOnly,
        disabled: i.disabled
      })));
    })()
  `);
  console.log(inputValues);

  // Check for hidden dropdown/select state
  console.log('\n=== DROPDOWN STATES ===');
  const dropdowns = await ev(`
    (() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return 'No modal';
      // Check for custom dropdown components
      const customDropdowns = [...modal.querySelectorAll('[role="combobox"], [role="listbox"], [class*="dropdown"], [class*="select"]')];
      // Check for hidden inputs that store actual values
      const hiddenInputs = [...modal.querySelectorAll('input[type="hidden"]')];
      return JSON.stringify({
        customDropdowns: customDropdowns.map(el => ({
          role: el.getAttribute('role'),
          text: el.textContent.trim().substring(0, 60),
          ariaExpanded: el.getAttribute('aria-expanded'),
          value: el.getAttribute('value') || el.dataset?.value
        })),
        hiddenInputs: hiddenInputs.map(i => ({ name: i.name, value: i.value, id: i.id }))
      });
    })()
  `);
  console.log(dropdowns);

  ws.close();
  process.exit(0);
}
main().catch(e => { console.error(e.message); process.exit(1); });
