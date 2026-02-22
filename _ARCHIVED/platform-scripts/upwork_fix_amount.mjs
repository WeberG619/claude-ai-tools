// Fix the amount on the proposal edit page using React native setter
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.method === 'Page.javascriptDialogOpening') {
        const mid = id++;
        ws.send(JSON.stringify({ id: mid, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
      }
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    const typeText = async (text) => {
      for (const char of text) {
        await send('Input.dispatchKeyEvent', { type: 'char', text: char, unmodifiedText: char });
        await sleep(4);
      }
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // Current amount
  const currentVal = await c.ev(`document.getElementById('charged-amount-id')?.value`);
  console.log('Current value:', currentVal);

  // Step 1: Focus and clear the field completely using keyboard
  console.log('Clearing field...');
  await c.ev(`document.getElementById('charged-amount-id').focus()`);
  await sleep(200);

  // Select all with Ctrl+A, then delete
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Home', code: 'Home' });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Home', code: 'Home' });
  await sleep(50);
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'End', code: 'End', modifiers: 1 }); // Shift+End
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'End', code: 'End', modifiers: 1 });
  await sleep(50);
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace' });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
  await sleep(200);

  let val = await c.ev(`document.getElementById('charged-amount-id')?.value`);
  console.log('After clear:', val);

  // If still not cleared, use multiple backspaces
  if (val && val.length > 5) {
    console.log('Field still has content, clearing with backspaces...');
    for (let i = 0; i < 20; i++) {
      await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace' });
      await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace' });
      await sleep(30);
    }
    await sleep(200);
    val = await c.ev(`document.getElementById('charged-amount-id')?.value`);
    console.log('After backspaces:', val);
  }

  // Type the new value
  console.log('Typing 130...');
  await c.typeText('130');
  await sleep(500);

  val = await c.ev(`document.getElementById('charged-amount-id')?.value`);
  console.log('After typing 130:', val);

  // Tab out to trigger React state
  await c.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab' });
  await c.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
  await sleep(500);

  val = await c.ev(`document.getElementById('charged-amount-id')?.value`);
  console.log('After tab:', val);

  // Check the total and receive amounts
  const earnedVal = await c.ev(`document.getElementById('earned-amount-id')?.value`);
  console.log('You\'ll receive:', earnedVal);

  // If the value is correct, save
  if (val === '$130.00' || val === '130' || val === '$130') {
    console.log('Amount looks correct, saving...');
    await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
    await sleep(300);

    const saveResult = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim().toLowerCase();
          if (btns[i].offsetParent && !btns[i].disabled && (t.includes('save') || t.includes('update'))) {
            btns[i].click();
            return 'Clicked: ' + btns[i].textContent.trim();
          }
        }
        return 'no save button';
      })()
    `);
    console.log('Save:', saveResult);
    await sleep(8000);

    const resultUrl = await c.ev('window.location.href');
    const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
    console.log('Result URL:', resultUrl);
    console.log('Result:', resultText.substring(0, 300));
  } else {
    console.log('Amount still wrong. Trying nativeInputValueSetter...');
    await c.ev(`
      (() => {
        var el = document.getElementById('charged-amount-id');
        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(el, '130');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return el.value;
      })()
    `);
    await sleep(1000);
    val = await c.ev(`document.getElementById('charged-amount-id')?.value`);
    console.log('After native setter:', val);

    // Try saving regardless
    await c.ev(`window.scrollTo(0, document.body.scrollHeight)`);
    await sleep(300);
    const saveResult = await c.ev(`
      (() => {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = btns[i].textContent.trim().toLowerCase();
          if (btns[i].offsetParent && !btns[i].disabled && (t.includes('save') || t.includes('update'))) {
            btns[i].click();
            return 'Clicked: ' + btns[i].textContent.trim();
          }
        }
        return 'no save button';
      })()
    `);
    console.log('Save:', saveResult);
    await sleep(8000);
    const resultUrl = await c.ev('window.location.href');
    console.log('Result URL:', resultUrl);
    const resultText = await c.ev(`(document.querySelector('main') || document.body).innerText.substring(0, 500)`);
    console.log('Result:', resultText.substring(0, 300));
  }

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
