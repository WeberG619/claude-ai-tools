// Answer security question, then fix city
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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
  console.log("Connected\n");

  // Step 1: Fill in security question answer
  console.log("Filling security question...");
  
  // Focus and type in the answer field
  let r = await eval_(`
    const answerInput = document.getElementById('securityQuestion_answer');
    if (answerInput) {
      answerInput.scrollIntoView({ block: 'center' });
      answerInput.focus();
      answerInput.click();
      const rect = answerInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no answer input' });
  `);
  const ansPos = JSON.parse(r);
  if (ansPos.error) {
    console.log("Error:", ansPos.error);
    ws.close();
    return;
  }

  await clickAt(send, ansPos.x, ansPos.y);
  await sleep(200);
  await send("Input.insertText", { text: "Hopkins" });
  await sleep(300);

  // Check the "I understand" checkbox
  r = await eval_(`
    const checkbox = document.getElementById('securityQuestion_lockingNotice');
    if (checkbox && !checkbox.checked) {
      const rect = checkbox.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), checked: false });
    }
    return JSON.stringify({ checked: checkbox ? checkbox.checked : 'not found' });
  `);
  console.log("Checkbox:", r);
  const cbState = JSON.parse(r);
  if (!cbState.checked && cbState.x) {
    await clickAt(send, cbState.x, cbState.y);
    await sleep(300);
  }

  // Check the "Keep me logged in" checkbox too
  r = await eval_(`
    const checkbox = document.getElementById('securityQuestion_remember');
    if (checkbox && !checkbox.checked) {
      const rect = checkbox.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), checked: false });
    }
    return JSON.stringify({ checked: checkbox ? checkbox.checked : 'not found' });
  `);
  const remState = JSON.parse(r);
  if (!remState.checked && remState.x) {
    await clickAt(send, remState.x, remState.y);
    await sleep(300);
  }

  // Click Save
  console.log("Clicking Save...");
  await clickAt(send, 924, 874);
  await sleep(3000);

  // Check result
  r = await eval_(`return JSON.stringify({
    url: location.href,
    bodySnippet: document.body.innerText.substring(0, 300)
  })`);
  console.log("After Save:", r);

  // Now we should be back on contact info page
  // Need to click Edit on Location section again
  await sleep(1000);
  
  // Check if we need to reload
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({
    url: location.href,
    hasBuffalo: document.body.innerText.includes('Buffalo'),
    hasSandpoint: document.body.innerText.includes('Sandpoint'),
    bodySnippet: document.body.innerText.substring(0, 800)
  })`);
  const state = JSON.parse(r);
  console.log("\nCurrent state:");
  console.log("URL:", state.url);
  console.log("Has Buffalo:", state.hasBuffalo);
  console.log("Has Sandpoint:", state.hasSandpoint);

  if (state.hasBuffalo && !state.hasSandpoint) {
    console.log("\nCity still Buffalo. Clicking Location Edit...");
    
    // Find and click Location Edit button
    r = await eval_(`
      const editBtns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null)
        .map(el => ({
          text: 'Edit',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(editBtns);
    `);
    console.log("Edit buttons:", r);
    const editBtns = JSON.parse(r);
    
    // The second Edit button is for Location
    if (editBtns.length >= 2) {
      await clickAt(send, editBtns[1].x, editBtns[1].y);
      console.log("Clicked Location Edit at", editBtns[1].x, editBtns[1].y);
      await sleep(2000);

      // Find city input
      r = await eval_(`
        const cityInput = document.getElementById('typeahead-input-4') || 
          Array.from(document.querySelectorAll('input'))
            .find(el => el.placeholder?.includes('city') && el.offsetParent !== null);
        if (cityInput) {
          cityInput.scrollIntoView({ block: 'center' });
          const rect = cityInput.getBoundingClientRect();
          return JSON.stringify({ 
            value: cityInput.value, id: cityInput.id,
            x: Math.round(rect.x + rect.width/2), 
            y: Math.round(rect.y + rect.height/2) 
          });
        }
        return JSON.stringify({ error: 'no city input' });
      `);
      console.log("City input:", r);
      const cityInfo = JSON.parse(r);

      if (!cityInfo.error && cityInfo.value !== 'Sandpoint') {
        // Clear and type Sandpoint
        await clickAt(send, cityInfo.x, cityInfo.y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await sleep(100);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(100);
        await send("Input.insertText", { text: "Sandpoint" });
        await sleep(500);

        // Wait for typeahead suggestions
        r = await eval_(`
          const suggestions = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"], [class*="typeahead"] li, .dropdown-item'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({
              text: el.textContent.trim().substring(0, 60),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }));
          return JSON.stringify(suggestions);
        `);
        console.log("City suggestions:", r);
        const suggestions = JSON.parse(r);
        
        // Find Sandpoint, ID suggestion
        const sandpointSuggestion = suggestions.find(s => 
          s.text.includes('Sandpoint') && s.text.includes('ID')
        ) || suggestions.find(s => s.text.includes('Sandpoint')) || suggestions[0];
        
        if (sandpointSuggestion) {
          await clickAt(send, sandpointSuggestion.x, sandpointSuggestion.y);
          console.log("Selected:", sandpointSuggestion.text);
          await sleep(1000);
        } else {
          // Escape and tab out
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
          await sleep(200);
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
          await sleep(300);
        }
      } else if (cityInfo.value === 'Sandpoint') {
        console.log("City already shows Sandpoint in form! Just need to save.");
      }

      // Verify all fields
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input'))
          .filter(el => el.offsetParent !== null && el.type !== 'search' && el.type !== 'checkbox')
          .map(el => ({ id: el.id || '', placeholder: el.placeholder || '', value: el.value }));
        return JSON.stringify(inputs, null, 2);
      `);
      console.log("\nAll form fields:", r);

      // Click Update
      r = await eval_(`
        const updateBtn = Array.from(document.querySelectorAll('button'))
          .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
        if (updateBtn) {
          const rect = updateBtn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no Update button' });
      `);
      const updateBtn = JSON.parse(r);
      if (!updateBtn.error) {
        await clickAt(send, updateBtn.x, updateBtn.y);
        console.log("Clicked Update");
        await sleep(5000);
        
        // Check result
        ws.close();
        await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        
        // Reload to see fresh data
        await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
        await sleep(4000);
        ws.close();
        await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));

        r = await eval_(`
          const text = document.body.innerText;
          const locIdx = text.indexOf('Location');
          const locSection = locIdx >= 0 ? text.substring(locIdx, locIdx + 300) : '';
          return JSON.stringify({
            hasSandpoint: text.includes('Sandpoint'),
            hasBuffalo: text.includes('Buffalo'),
            locationSection: locSection
          });
        `);
        console.log("\n=== FINAL RESULT ===");
        console.log(r);
      }
    }
  } else if (state.hasSandpoint) {
    console.log("\n*** SUCCESS: City is now Sandpoint! ***");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
