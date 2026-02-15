// Fill description in Quill editor and save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to description area
  await eval_(`window.scrollTo(0, 400)`);
  await sleep(500);

  // Click into the ql-editor (contenteditable div)
  let r = await eval_(`
    const editor = document.querySelector('.ql-editor');
    if (editor) {
      editor.scrollIntoView({ block: 'center' });
      const rect = editor.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + 20),
        y: Math.round(rect.y + 20),
        text: editor.textContent.trim().substring(0, 50),
        html: editor.innerHTML.substring(0, 100)
      });
    }
    return JSON.stringify({ error: 'no editor' });
  `);
  console.log("Editor:", r);
  const editor = JSON.parse(r);
  if (editor.error) { ws.close(); return; }

  await sleep(300);

  // Click into the editor
  console.log(`Clicking editor at (${editor.x}, ${editor.y})`);
  await clickAt(send, editor.x, editor.y);
  await sleep(500);

  // Focus the editor via JS
  await eval_(`
    const ed = document.querySelector('.ql-editor');
    if (ed) ed.focus();
  `);
  await sleep(300);

  // Select all existing content
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(200);

  // Delete selected
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(300);

  // Type the description using keyboard input
  const description = `Are you looking for a skilled proofreader and editor to polish your writing? I offer professional proofreading, editing, and rewriting services to ensure your content is clear, error-free, and impactful.

What you'll get:
- Thorough grammar, spelling, and punctuation correction
- Improved sentence structure and clarity
- Consistent tone and style throughout
- Enhanced readability and flow
- Track changes so you can see all edits made

I work with:
- Articles and blog posts
- Website content
- Academic papers and theses
- Books and manuscripts
- Business documents and reports
- Resumes and cover letters

Every piece of content deserves careful attention. I'll make sure your writing communicates exactly what you intend, with professional polish.

Order now and let me help your words make the right impression!`;

  console.log(`Typing description (${description.length} chars)...`);
  await send("Input.insertText", { text: description });
  await sleep(1000);

  // Check if the char counter updated
  r = await eval_(`
    const counter = document.querySelector('[class*="char-count"], [class*="character"]');
    const counterText = counter ? counter.textContent.trim() : '';
    const editorText = document.querySelector('.ql-editor')?.textContent?.trim()?.substring(0, 100) || '';
    const editorLen = document.querySelector('.ql-editor')?.textContent?.trim()?.length || 0;
    // Also check all spans/divs near the editor for the character count
    const allCounters = Array.from(document.querySelectorAll('span, div'))
      .filter(el => {
        const t = el.textContent.trim();
        return t.match(/\\d+\\/1200/) && el.offsetParent !== null;
      })
      .map(el => el.textContent.trim());
    return JSON.stringify({ counterText, editorText, editorLen, allCounters });
  `);
  console.log("After typing:", r);

  // If still 0, try Quill API directly
  const afterType = JSON.parse(r);
  if (afterType.editorLen < 120) {
    console.log("\nEditor text not set, trying Quill API...");
    r = await eval_(`
      const quillContainer = document.querySelector('.ql-container');
      if (quillContainer && quillContainer.__quill) {
        const quill = quillContainer.__quill;
        quill.setText('');
        quill.clipboard.dangerouslyPasteHTML(0, \`<p>Are you looking for a skilled proofreader and editor to polish your writing? I offer professional proofreading, editing, and rewriting services to ensure your content is clear, error-free, and impactful.</p><p><br></p><p>What you'll get:</p><p>- Thorough grammar, spelling, and punctuation correction</p><p>- Improved sentence structure and clarity</p><p>- Consistent tone and style throughout</p><p>- Enhanced readability and flow</p><p>- Track changes so you can see all edits made</p><p><br></p><p>I work with:</p><p>- Articles and blog posts</p><p>- Website content</p><p>- Academic papers and theses</p><p>- Books and manuscripts</p><p>- Business documents and reports</p><p>- Resumes and cover letters</p><p><br></p><p>Every piece of content deserves careful attention. I'll make sure your writing communicates exactly what you intend, with professional polish.</p><p><br></p><p>Order now and let me help your words make the right impression!</p>\`);
        return JSON.stringify({ text: quill.getText().substring(0, 100), length: quill.getText().length });
      }
      // Try React fiber approach
      const editor = document.querySelector('.ql-editor');
      if (editor) {
        editor.innerHTML = '<p>Are you looking for a skilled proofreader and editor to polish your writing? I offer professional proofreading, editing, and rewriting services to ensure your content is clear, error-free, and impactful.</p><p><br></p><p>What you will get:</p><p>- Thorough grammar, spelling, and punctuation correction</p><p>- Improved sentence structure and clarity</p><p>- Consistent tone and style throughout</p><p>- Enhanced readability and flow</p><p>- Track changes so you can see all edits made</p><p><br></p><p>I work with:</p><p>- Articles and blog posts</p><p>- Website content</p><p>- Academic papers and theses</p><p>- Books and manuscripts</p><p>- Business documents and reports</p><p>- Resumes and cover letters</p><p><br></p><p>Every piece of content deserves careful attention. I will make sure your writing communicates exactly what you intend, with professional polish.</p><p><br></p><p>Order now and let me help your words make the right impression!</p>';
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        return JSON.stringify({ text: editor.textContent.substring(0, 100), length: editor.textContent.length, method: 'innerHTML' });
      }
      return JSON.stringify({ error: 'no quill or editor' });
    `);
    console.log("Quill API result:", r);
  }

  await sleep(500);

  // Final check on counter
  r = await eval_(`
    const ed = document.querySelector('.ql-editor');
    const allCounters = Array.from(document.querySelectorAll('span, div'))
      .filter(el => {
        const t = el.textContent.trim();
        return t.match(/\\d+\\/1200/) && el.offsetParent !== null;
      })
      .map(el => el.textContent.trim());
    return JSON.stringify({
      editorLen: ed?.textContent?.trim()?.length || 0,
      counters: allCounters,
      editorPreview: ed?.textContent?.trim()?.substring(0, 80)
    });
  `);
  console.log("Final check:", r);

  // Scroll to Save & Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(800);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    console.log(`\nClicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors: Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100)),
        body: (document.body?.innerText || '').substring(200, 800)
      });
    `);
    console.log("\nAfter save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
