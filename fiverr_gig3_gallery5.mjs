// Gallery upload using Page.fileChooserOpened interception
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
  const events = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
    if (msg.method) {
      events.push(msg);
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
  return { ws, send, eval_, events };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_, events } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  await send("DOM.enable");
  await send("Page.enable");

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });
  console.log("File chooser interception enabled");

  // Find the Browse link/button in the portfolio/image section
  let r = await eval_(`
    const portfolio = document.querySelector('.portfolio-section');
    if (!portfolio) return JSON.stringify({ error: 'no portfolio' });

    // Find clickable elements
    const clickable = Array.from(portfolio.querySelectorAll('a, button, [role="button"], span, label'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 30)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim(),
        class: (el.className || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));

    // Also find the drag-drop target placeholder
    const placeholder = portfolio.querySelector('.gallery-item-placeholder');
    const phRect = placeholder ? placeholder.getBoundingClientRect() : null;

    return JSON.stringify({
      clickable,
      placeholder: phRect ? {
        x: Math.round(phRect.x + phRect.width/2),
        y: Math.round(phRect.y + phRect.height/2),
        w: Math.round(phRect.width),
        h: Math.round(phRect.height)
      } : null
    });
  `);
  console.log("Portfolio clickable elements:", r);
  const data = JSON.parse(r);

  // Find Browse link
  const browseLink = data.clickable.find(el => el.text.includes('Browse'));

  if (browseLink) {
    console.log(`\nClicking Browse at (${browseLink.x}, ${browseLink.y})`);

    // Set up a listener for file chooser event before clicking
    const fileChooserPromise = new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        const fcEvent = events.find(e => e.method === 'Page.fileChooserOpened');
        if (fcEvent) {
          clearInterval(checkInterval);
          resolve(fcEvent);
        }
      }, 100);
      // Timeout after 5s
      setTimeout(() => { clearInterval(checkInterval); resolve(null); }, 5000);
    });

    await clickAt(send, browseLink.x, browseLink.y);

    const fcEvent = await fileChooserPromise;
    if (fcEvent) {
      console.log("File chooser opened!", JSON.stringify(fcEvent.params));
      // Accept with our file
      await send("Page.handleFileChooser", {
        action: "accept",
        files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
      });
      console.log("File accepted via file chooser");
    } else {
      console.log("No file chooser event received, trying direct click on placeholder...");

      // Try clicking the placeholder itself
      if (data.placeholder) {
        events.length = 0; // Clear events
        const fcPromise2 = new Promise((resolve) => {
          const checkInterval = setInterval(() => {
            const fcEvent = events.find(e => e.method === 'Page.fileChooserOpened');
            if (fcEvent) {
              clearInterval(checkInterval);
              resolve(fcEvent);
            }
          }, 100);
          setTimeout(() => { clearInterval(checkInterval); resolve(null); }, 5000);
        });

        await clickAt(send, data.placeholder.x, data.placeholder.y);
        const fc2 = await fcPromise2;
        if (fc2) {
          console.log("File chooser opened from placeholder!");
          await send("Page.handleFileChooser", {
            action: "accept",
            files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
          });
          console.log("File accepted");
        } else {
          console.log("Still no file chooser. Trying JS click on input...");
          events.length = 0;
          const fcPromise3 = new Promise((resolve) => {
            const checkInterval = setInterval(() => {
              const fcEvent = events.find(e => e.method === 'Page.fileChooserOpened');
              if (fcEvent) {
                clearInterval(checkInterval);
                resolve(fcEvent);
              }
            }, 100);
            setTimeout(() => { clearInterval(checkInterval); resolve(null); }, 5000);
          });
          await eval_(`document.getElementById('image').click(); return 'clicked';`);
          const fc3 = await fcPromise3;
          if (fc3) {
            console.log("File chooser opened from JS click!");
            await send("Page.handleFileChooser", {
              action: "accept",
              files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
            });
            console.log("File accepted");
          } else {
            console.log("No file chooser from any method");
          }
        }
      }
    }

    await sleep(8000);

    // Check upload result
    r = await eval_(`
      const portfolio = document.querySelector('.portfolio-section');
      const imgs = portfolio ? Array.from(portfolio.querySelectorAll('img')).filter(el => el.src).map(el => ({ src: el.src.substring(0, 80), w: el.offsetWidth, h: el.offsetHeight })) : [];
      const items = portfolio ? Array.from(portfolio.querySelectorAll('.gallery-item-placeholder')).map(el => ({
        class: el.className.substring(0, 60),
        hasImg: !!el.querySelector('img'),
        bg: el.style.backgroundImage ? el.style.backgroundImage.substring(0, 80) : ''
      })) : [];
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({ imgs, items, errors });
    `);
    console.log("\nUpload result:", r);
  } else {
    console.log("No Browse link found in portfolio section");

    // Try directly clicking the image input via JS
    events.length = 0;
    const fcPromise = new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        const fcEvent = events.find(e => e.method === 'Page.fileChooserOpened');
        if (fcEvent) {
          clearInterval(checkInterval);
          resolve(fcEvent);
        }
      }, 100);
      setTimeout(() => { clearInterval(checkInterval); resolve(null); }, 5000);
    });
    await eval_(`document.getElementById('image').click(); return 'clicked';`);
    const fc = await fcPromise;
    if (fc) {
      await send("Page.handleFileChooser", {
        action: "accept",
        files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
      });
      console.log("File accepted via JS click");
      await sleep(8000);
    }
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    await sleep(500);
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(10000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);

    const state = JSON.parse(r);
    if (state.wizard === '5' || (state.wizard === '4' && state.errors.length === 0)) {
      if (state.wizard === '4') {
        await eval_(`window.location.href = location.href.replace(/wizard=4/, 'wizard=5').replace(/&tab=\\w+/, '')`);
        await sleep(5000);
        ws.close();
        await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
        r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
        console.log("Nav to wizard=5:", r);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
