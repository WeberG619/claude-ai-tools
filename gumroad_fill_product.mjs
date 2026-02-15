// Fill in Gumroad product details and save
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
        await sleep(3);
      }
    };
    const selectAll = async () => {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2 });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2 });
      await sleep(100);
    };
    ws.addEventListener('open', async () => {
      const mid = id++;
      pending.set(mid, { res: () => {}, rej: () => {} });
      ws.send(JSON.stringify({ id: mid, method: 'Page.enable', params: {} }));
      resolve({ ws, send, ev, typeText, selectAll, close: () => ws.close() });
    });
    ws.addEventListener('error', reject);
  });
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('gumroad.com'));
  if (!tab) { console.log('No Gumroad tab'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);
  await sleep(500);

  const url = await c.ev('window.location.href');
  console.log('URL:', url);

  // 1. Set the URL slug to something nice
  console.log('Setting URL slug...');
  const slugField = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].placeholder === 'iukfn') {
          inputs[i].focus();
          return 'found';
        }
      }
      return 'not found';
    })()
  `);
  if (slugField === 'found') {
    await c.selectAll();
    await sleep(100);
    await c.typeText('revit-starter-kit');
    console.log('Set slug to: revit-starter-kit');
    await sleep(300);
  }

  // 2. Set the description using contenteditable
  console.log('\nSetting description...');
  const descHTML = `<h2>Revit C# Add-in Starter Kit</h2>
<p>Stop wasting hours setting up boilerplate. Get a production-ready Visual Studio solution that compiles for <strong>Revit 2024, 2025, and 2026</strong> out of the box.</p>

<h3>What's Inside</h3>
<ul>
<li><strong>Multi-target .csproj</strong> — Build for Revit 2024 (.NET 4.8), 2025, and 2026 (.NET 8) from one solution</li>
<li><strong>Ribbon UI setup</strong> — Tab, panels, and push buttons ready to go with IExternalApplication</li>
<li><strong>Sample commands</strong> — IExternalCommand boilerplate with TaskDialog, element selection, and data export</li>
<li><strong>WPF dialog template</strong> — Professional MVVM-ready dialog with XAML styling</li>
<li><strong>Helper utilities</strong> — Get parameters, create transactions, filter elements, and more</li>
<li><strong>.addin manifest</strong> — Pre-configured for immediate deployment</li>
<li><strong>Complete documentation</strong> — Setup guide, architecture overview, and API reference</li>
</ul>

<h3>Who Is This For?</h3>
<ul>
<li>Developers starting with the Revit API</li>
<li>BIM managers building in-house tools</li>
<li>Freelancers who need a fast project template</li>
<li>Teams standardizing their add-in architecture</li>
</ul>

<h3>Tech Stack</h3>
<p>C# | .NET Framework 4.8 / .NET 8 | WPF | Revit API | Visual Studio 2022</p>

<p><em>Built by Weber Gouin — Revit API specialist with 10+ years of BIM automation experience.</em></p>`;

  await c.ev(`
    (() => {
      var editor = document.querySelector('[contenteditable="true"]');
      if (editor) {
        editor.focus();
        editor.innerHTML = ${JSON.stringify(descHTML)};
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        return 'set';
      }
      return 'not found';
    })()
  `);
  console.log('Description set');
  await sleep(500);

  // 3. Set the summary (You'll get...)
  console.log('\nSetting summary...');
  const summaryField = await c.ev(`
    (() => {
      var inputs = document.querySelectorAll('input[type="text"]');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].placeholder === "You'll get...") {
          inputs[i].focus();
          return 'found';
        }
      }
      return 'not found';
    })()
  `);
  if (summaryField === 'found') {
    await c.selectAll();
    await sleep(100);
    await c.typeText('Complete Visual Studio solution for Revit 2024-2026 with sample commands, WPF UI, and documentation');
    console.log('Summary set');
    await sleep(300);
  }

  // 4. Click "Save and continue"
  console.log('\nSaving...');
  await c.ev(`window.scrollTo(0, 0)`);
  await sleep(300);

  const saved = await c.ev(`
    (() => {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent.trim().toLowerCase();
        if (t.includes('save') || t.includes('publish')) {
          btns[i].click();
          return 'Clicked: ' + btns[i].textContent.trim();
        }
      }
      return 'no save button';
    })()
  `);
  console.log(saved);
  await sleep(5000);

  // Check result
  const resultUrl = await c.ev('window.location.href');
  const resultText = await c.ev(`document.body.innerText.substring(0, 1000)`);
  console.log('\nResult URL:', resultUrl);
  console.log('Result:', resultText.substring(0, 500));

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
