import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 90000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const pageTab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const i = ++id;
      pending.set(i, { res, rej });
      ws.send(JSON.stringify({ id: i, method, params }));
    });
    const eval_ = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    const clickAt = async (x, y) => {
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    };

    const typeText = async (text) => {
      for (const char of text) {
        await send("Input.dispatchKeyEvent", { type: "char", text: char });
        await sleep(50);
      }
    };

    (async () => {
      // Step 1: Navigate to Google
      await send("Page.navigate", { url: "https://www.google.com" });
      await sleep(4000);

      let url = await eval_(`window.location.href`);
      L("Google URL: " + url);

      // Accept cookies if present
      await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t.includes('Accept') || t.includes('I agree') || t.includes('Accept all')) {
              btns[i].click();
              return 'accepted';
            }
          }
          return 'no cookie banner';
        })()
      `);
      await sleep(1000);

      // Step 2: Click the search box and type the keyword
      let r = await eval_(`
        (function() {
          var input = document.querySelector('input[name="q"], textarea[name="q"]');
          if (input) {
            input.focus();
            input.click();
            return 'focused search: ' + input.tagName;
          }
          return 'no search input';
        })()
      `);
      L("Search input: " + r);
      await sleep(500);

      // Type the keyword character by character to trigger autocomplete
      await typeText("Natural Vibrations Inc. Review");
      await sleep(3000);

      // Screenshot to see suggestions
      const ss1 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_google_suggestions.png', Buffer.from(ss1.data, 'base64'));
      L("Suggestions screenshot saved");

      // Check what suggestions appeared
      r = await eval_(`
        (function() {
          // Look for the autocomplete suggestions
          var suggestions = document.querySelectorAll('[role="listbox"] li, [role="option"], .sbct, .sbl1, ul[role="listbox"] li, .aajZCb div[role="option"]');
          var result = [];
          suggestions.forEach(function(s) {
            result.push(s.textContent.trim().substring(0, 100));
          });
          if (result.length === 0) {
            // Try a broader search
            var all = document.querySelectorAll('[data-attrid], .erkvQe, .sbct, [role="option"]');
            all.forEach(function(el) {
              result.push(el.textContent.trim().substring(0, 100));
            });
          }
          return JSON.stringify(result);
        })()
      `);
      L("Suggestions: " + r);

      // Look for "Report inappropriate predictions" link
      r = await eval_(`
        (function() {
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length; i++) {
            var t = all[i].textContent.trim().toLowerCase();
            if (t.includes('report') && t.includes('predictions') && t.length < 80) {
              var rect = all[i].getBoundingClientRect();
              return JSON.stringify({ text: all[i].textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), tag: all[i].tagName });
            }
            if (t.includes('report') && t.includes('inappropriate') && t.length < 80) {
              var rect = all[i].getBoundingClientRect();
              return JSON.stringify({ text: all[i].textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), tag: all[i].tagName });
            }
          }
          return 'not found';
        })()
      `);
      L("Report link: " + r);

      if (r !== 'not found') {
        let reportEl = JSON.parse(r);
        L("Clicking report at (" + reportEl.x + "," + reportEl.y + ")");
        await clickAt(reportEl.x, reportEl.y);
        await sleep(3000);

        // Screenshot the feedback form
        const ss2 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_google_report.png', Buffer.from(ss2.data, 'base64'));
        L("Report screenshot saved");

        // Check the feedback form
        let pageText = await eval_(`document.body.innerText.substring(0, 3000)`);
        L("Feedback page:");
        L(pageText.substring(0, 1500));

        // Look for the offending suggestion options
        r = await eval_(`
          (function() {
            var all = document.querySelectorAll('*');
            var matches = [];
            for (var i = 0; i < all.length; i++) {
              var t = all[i].textContent.trim();
              if ((t.includes('Offender') || t.includes('offender')) && t.length < 80) {
                var rect = all[i].getBoundingClientRect();
                matches.push({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), tag: all[i].tagName, class: (all[i].className||'').substring(0,40) });
              }
            }
            return JSON.stringify(matches);
          })()
        `);
        L("Offender options: " + r);

        // Try to hover over one of the offending suggestions to highlight it pink
        let offenderOpts = [];
        try { offenderOpts = JSON.parse(r); } catch(e) {}

        if (offenderOpts.length > 0) {
          let target = offenderOpts.find(o => o.text.includes('Offender Search')) || offenderOpts[0];
          L("Hovering over: " + target.text + " at (" + target.x + "," + target.y + ")");
          await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: target.x, y: target.y });
          await sleep(1000);

          // Take the final screenshot with hover highlight
          const ss3 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
          writeFileSync('D:\\_CLAUDE-TOOLS\\cw_keyword_screenshot.png', Buffer.from(ss3.data, 'base64'));
          L("Final screenshot saved at cw_keyword_screenshot.png");
        }
      } else {
        // No "Report" link found in suggestions - might need to search first
        L("No report link. Pressing Enter to search...");
        await send("Input.dispatchKeyEvent", { type: "keyDown", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
        await sleep(4000);

        let pageText = await eval_(`document.body.innerText.substring(0, 2000)`);
        L("Search results: " + pageText.substring(0, 1000));

        const ss2 = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_google_search.png', Buffer.from(ss2.data, 'base64'));
        L("Search results screenshot saved");
      }

      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(0);
    })().catch(e => {
      L("Error: " + e.message);
      ws.close();
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
      process.exit(1);
    });
  });
})().catch(e => {
  L("Fatal: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
