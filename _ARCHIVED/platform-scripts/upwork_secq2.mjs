// Fix security question answer to "120th Street", save, then fix city
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

  // Check if security question dialog is still open
  let r = await eval_(`
    const answerInput = document.getElementById('securityQuestion_answer');
    const hasDialog = document.body.innerText.includes('security question');
    return JSON.stringify({
      hasDialog,
      answerInput: answerInput ? { value: answerInput.value, visible: answerInput.offsetParent !== null } : null
    });
  `);
  console.log("Dialog state:", r);
  const dialogState = JSON.parse(r);

  if (dialogState.answerInput) {
    // Clear the answer field and type the correct answer
    console.log("Fixing security question answer to '120th Street'...");
    
    r = await eval_(`
      const inp = document.getElementById('securityQuestion_answer');
      if (inp) {
        inp.scrollIntoView({ block: 'center' });
        inp.focus();
        inp.click();
        const rect = inp.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: inp.value });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const ansPos = JSON.parse(r);
    console.log("Answer field:", r);

    if (!ansPos.error) {
      await clickAt(send, ansPos.x, ansPos.y);
      await sleep(200);

      // Select all and delete
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(100);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
      await sleep(100);

      // Type correct answer
      await send("Input.insertText", { text: "120th Street" });
      await sleep(300);

      // Verify answer
      r = await eval_(`
        const inp = document.getElementById('securityQuestion_answer');
        return inp ? inp.value : 'not found';
      `);
      console.log("Answer now:", r);

      // Make sure checkbox is checked
      r = await eval_(`
        const cb = document.getElementById('securityQuestion_lockingNotice');
        if (cb && !cb.checked) {
          const rect = cb.getBoundingClientRect();
          return JSON.stringify({ needsClick: true, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ needsClick: false, checked: cb ? cb.checked : 'not found' });
      `);
      const cbInfo = JSON.parse(r);
      if (cbInfo.needsClick) {
        await clickAt(send, cbInfo.x, cbInfo.y);
        await sleep(200);
      }

      // Find and click Save button
      r = await eval_(`
        const saveBtn = Array.from(document.querySelectorAll('button'))
          .find(el => el.textContent.trim() === 'Save' && el.offsetParent !== null);
        if (saveBtn) {
          const rect = saveBtn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no Save button' });
      `);
      console.log("Save button:", r);
      const saveBtn = JSON.parse(r);
      
      if (!saveBtn.error) {
        await clickAt(send, saveBtn.x, saveBtn.y);
        console.log("Clicked Save");
        await sleep(3000);

        // Check if we're past the security question now
        r = await eval_(`return JSON.stringify({
          url: location.href,
          hasSecurityQ: document.body.innerText.includes('security question'),
          hasError: document.body.innerText.includes('error') || document.body.innerText.includes('Error')
        })`);
        console.log("After save:", r);
      }
    }
  } else {
    console.log("No security question dialog found. Navigating to contact info...");
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
  }

  // Reconnect and check state
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  r = await eval_(`return JSON.stringify({
    url: location.href,
    hasBuffalo: document.body.innerText.includes('Buffalo'),
    hasSandpoint: document.body.innerText.includes('Sandpoint')
  })`);
  console.log("\nPage state:", r);
  const pageState = JSON.parse(r);

  if (pageState.url.includes('security-question')) {
    // Still on security question - maybe need to reload
    console.log("Still on security question page. Navigating away...");
    await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
    await sleep(4000);
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  // Now fix the city
  r = await eval_(`return JSON.stringify({
    url: location.href,
    hasBuffalo: document.body.innerText.includes('Buffalo'),
    hasSandpoint: document.body.innerText.includes('Sandpoint'),
    locationSection: document.body.innerText.includes('Location') ? 
      document.body.innerText.substring(document.body.innerText.indexOf('Location'), document.body.innerText.indexOf('Location') + 200) : ''
  })`);
  console.log("\nContact info state:", r);
  const contactState = JSON.parse(r);

  if (contactState.hasBuffalo) {
    console.log("\nCity still Buffalo. Clicking Location Edit...");
    
    // Scroll down to Location section
    await eval_(`window.scrollTo(0, 600)`);
    await sleep(500);
    
    r = await eval_(`
      // Find the Edit button near the Location section
      const locHeader = Array.from(document.querySelectorAll('*'))
        .find(el => el.textContent.trim() === 'Location' && el.tagName.match(/^H[1-6]$/));
      
      const editBtns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.textContent.trim() === 'Edit' && el.offsetParent !== null)
        .map(el => ({
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      
      return JSON.stringify({ editBtns, locHeader: locHeader ? locHeader.tagName : 'none' });
    `);
    console.log("Edit buttons:", r);
    const { editBtns } = JSON.parse(r);
    
    // Click the last Edit button (for Location)
    if (editBtns.length >= 2) {
      await clickAt(send, editBtns[editBtns.length - 1].x, editBtns[editBtns.length - 1].y);
      console.log("Clicked Location Edit");
      await sleep(2000);

      // Check what opened
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            id: el.id || '',
            placeholder: el.placeholder || '',
            value: el.value,
            type: el.type
          }));
        return JSON.stringify(inputs, null, 2);
      `);
      console.log("Inputs:", r);
      const inputs = JSON.parse(r);
      
      // Find city input
      const cityInput = inputs.find(i => i.placeholder.includes('city') || i.id.includes('typeahead'));
      if (cityInput) {
        console.log("Found city input:", cityInput.value);
        
        if (cityInput.value !== 'Sandpoint') {
          // Focus city input
          r = await eval_(`
            const inp = document.querySelector('#${cityInput.id}') || 
              Array.from(document.querySelectorAll('input'))
                .find(el => el.placeholder?.includes('city') && el.offsetParent !== null);
            if (inp) {
              inp.scrollIntoView({ block: 'center' });
              inp.focus();
              const rect = inp.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
            return JSON.stringify({ error: 'not found' });
          `);
          const cityPos = JSON.parse(r);
          
          if (!cityPos.error) {
            // Clear and type
            await clickAt(send, cityPos.x, cityPos.y);
            await sleep(200);
            
            // Clear with button if available
            r = await eval_(`
              const clearBtns = Array.from(document.querySelectorAll('button'))
                .filter(el => el.textContent.trim() === 'Clear Input' && el.offsetParent !== null)
                .map(el => ({
                  x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                  y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
                }));
              return JSON.stringify(clearBtns);
            `);
            console.log("Clear buttons:", r);
            const clearBtns = JSON.parse(r);
            
            // Click the city clear button (second one, after address clear)
            if (clearBtns.length >= 2) {
              await clickAt(send, clearBtns[1].x, clearBtns[1].y);
              console.log("Clicked city Clear button");
              await sleep(500);
            } else {
              // Manual clear
              await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
              await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
              await sleep(100);
              await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
              await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
              await sleep(100);
            }

            // Re-focus and type Sandpoint
            r = await eval_(`
              const inp = Array.from(document.querySelectorAll('input'))
                .find(el => el.placeholder?.includes('city') && el.offsetParent !== null);
              if (inp) {
                inp.focus();
                inp.click();
                const rect = inp.getBoundingClientRect();
                return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
              return JSON.stringify({ error: 'not found' });
            `);
            const cityPos2 = JSON.parse(r);
            if (!cityPos2.error) {
              await clickAt(send, cityPos2.x, cityPos2.y);
              await sleep(200);
            }
            
            await send("Input.insertText", { text: "Sandpoint" });
            await sleep(1000);

            // Check for suggestions
            r = await eval_(`
              const suggestions = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"], li[class*="typeahead"]'))
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                  text: el.textContent.trim().substring(0, 60),
                  x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                  y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
                }));
              return JSON.stringify(suggestions);
            `);
            console.log("Suggestions:", r);
            const suggestions = JSON.parse(r);
            
            const sandpointSugg = suggestions.find(s => s.text.includes('Sandpoint'));
            if (sandpointSugg) {
              await clickAt(send, sandpointSugg.x, sandpointSugg.y);
              console.log("Selected:", sandpointSugg.text);
              await sleep(1000);
            } else {
              // Just escape and tab
              await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
              await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
              await sleep(200);
              await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
              await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
              await sleep(300);
            }
          }
        }

        // Click Update
        await sleep(500);
        r = await eval_(`
          const updateBtn = Array.from(document.querySelectorAll('button'))
            .find(el => el.textContent.trim() === 'Update' && el.offsetParent !== null);
          if (updateBtn) {
            const rect = updateBtn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'no Update' });
        `);
        const updateBtn = JSON.parse(r);
        if (!updateBtn.error) {
          await clickAt(send, updateBtn.x, updateBtn.y);
          console.log("Clicked Update");
          await sleep(5000);

          // Verify
          ws.close();
          await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          await eval_(`window.location.href = 'https://www.upwork.com/freelancers/settings/contactInfo'`);
          await sleep(4000);
          ws.close();
          await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));

          r = await eval_(`
            const text = document.body.innerText;
            const locIdx = text.indexOf('Location');
            return JSON.stringify({
              hasSandpoint: text.includes('Sandpoint'),
              hasBuffalo: text.includes('Buffalo'),
              locationSection: locIdx >= 0 ? text.substring(locIdx, locIdx + 200) : 'not found'
            });
          `);
          console.log("\n=== FINAL RESULT ===");
          console.log(r);
        }
      }
    }
  } else if (contactState.hasSandpoint) {
    console.log("\n*** City already shows Sandpoint! ***");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
