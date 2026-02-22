// Upwork signup - select freelancer and fill form
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching: ${urlMatch}`);
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
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected to Upwork\n");

  // Step 1: Select "I'm a freelancer"
  let r = await eval_(`
    const options = Array.from(document.querySelectorAll('button, [role="button"], [class*="radio"], label, div'))
      .filter(el => el.textContent.trim().includes('freelancer') && el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        tag: el.tagName,
        class: (el.className || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width)
      }));
    return JSON.stringify(options);
  `);
  console.log("Freelancer options:", r);
  const options = JSON.parse(r);

  // Click the freelancer option (find the one that's like a card/radio button)
  const freelancerOpt = options.find(o => o.text.includes("looking for work")) || options[0];
  if (freelancerOpt) {
    console.log(`Clicking freelancer option at (${freelancerOpt.x}, ${freelancerOpt.y})`);
    await clickAt(send, freelancerOpt.x, freelancerOpt.y);
    await sleep(1000);
  }

  // Click "Create Account"
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Create Account') || b.textContent.trim().includes('Apply as'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Create button:", r);
  const createBtn = JSON.parse(r);

  if (!createBtn.error) {
    await clickAt(send, createBtn.x, createBtn.y);
    await sleep(5000);

    // Check what page we're on now
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        title: document.title,
        body: document.body.innerText.substring(0, 800)
      });
    `);
    console.log("\nAfter create:", r);

    // Check if we need to fill in signup form (name, email, password)
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          type: el.type,
          name: el.name,
          id: el.id,
          placeholder: el.placeholder,
          label: el.labels?.[0]?.textContent?.trim() || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(inputs);
    `);
    console.log("\nForm inputs:", r);
    const inputs = JSON.parse(r);

    // Fill in name fields
    const firstNameInput = inputs.find(i => i.name?.includes('first') || i.id?.includes('first') || i.placeholder?.toLowerCase().includes('first'));
    const lastNameInput = inputs.find(i => i.name?.includes('last') || i.id?.includes('last') || i.placeholder?.toLowerCase().includes('last'));
    const emailInput = inputs.find(i => i.type === 'email' || i.name?.includes('email') || i.id?.includes('email'));
    const passwordInput = inputs.find(i => i.type === 'password' || i.name?.includes('password'));

    if (firstNameInput) {
      await clickAt(send, firstNameInput.x, firstNameInput.y);
      await sleep(200);
      await send("Input.insertText", { text: "Weber" });
      await sleep(300);
      console.log("First name: Weber");
    }

    if (lastNameInput) {
      await clickAt(send, lastNameInput.x, lastNameInput.y);
      await sleep(200);
      await send("Input.insertText", { text: "Gouin" });
      await sleep(300);
      console.log("Last name: Gouin");
    }

    if (emailInput) {
      await clickAt(send, emailInput.x, emailInput.y);
      await sleep(200);
      await send("Input.insertText", { text: "weberg619@gmail.com" });
      await sleep(300);
      console.log("Email: weberg619@gmail.com");
    }

    if (passwordInput) {
      await clickAt(send, passwordInput.x, passwordInput.y);
      await sleep(200);
      // Generate a decent password
      await send("Input.insertText", { text: "W3ber!Upwork2026" });
      await sleep(300);
      console.log("Password: set");
    }

    // Check for country selection
    r = await eval_(`
      const selects = Array.from(document.querySelectorAll('select, [class*="dropdown"], [role="combobox"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          id: el.id,
          name: el.name,
          class: (el.className || '').substring(0, 50),
          text: el.textContent?.trim()?.substring(0, 40) || ''
        }));
      return JSON.stringify(selects);
    `);
    console.log("\nDropdowns:", r);

    // Look for terms checkbox
    r = await eval_(`
      const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          id: el.id,
          name: el.name,
          label: el.labels?.[0]?.textContent?.trim()?.substring(0, 60) || '',
          checked: el.checked,
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + 10)
        }));
      return JSON.stringify(checkboxes);
    `);
    console.log("Checkboxes:", r);
    const checkboxes = JSON.parse(r);
    for (const cb of checkboxes) {
      if (!cb.checked) {
        await clickAt(send, cb.x, cb.y);
        await sleep(300);
        console.log(`Checked: ${cb.label || cb.id}`);
      }
    }

    // Find submit button
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button[type="submit"], button'))
        .filter(el => el.offsetParent !== null && (
          el.textContent.trim().includes('Create') ||
          el.textContent.trim().includes('Sign Up') ||
          el.textContent.trim().includes('Continue') ||
          el.textContent.trim().includes('Join') ||
          el.type === 'submit'
        ))
        .map(el => ({
          text: el.textContent.trim(),
          type: el.type,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(btns);
    `);
    console.log("\nSubmit buttons:", r);

    // DON'T submit yet - just show what we have
    console.log("\n=== Form State ===");
    r = await eval_(`
      const fields = Array.from(document.querySelectorAll('input'))
        .filter(el => el.offsetParent !== null && el.type !== 'hidden')
        .map(el => ({
          name: el.name || el.id,
          type: el.type,
          value: el.type === 'password' ? '***' : el.value,
          label: el.labels?.[0]?.textContent?.trim()?.substring(0, 30) || ''
        }));
      return JSON.stringify(fields);
    `);
    console.log(r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
