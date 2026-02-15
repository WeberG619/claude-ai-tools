import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 120000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PureSpectrum tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

  const ws = new WebSocket(psTab.webSocketDebuggerUrl);
  ws.addEventListener("error", () => { L("WS error"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); });

  ws.addEventListener("open", () => {
    let id = 0;
    const pending = new Map();
    ws.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); if (m.error) p.rej(new Error(m.error.message)); else p.res(m.result); }
    });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    // NO awaitPromise to avoid hangs
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };
    // Fire and forget
    const fire = (method, params = {}) => { const i = ++id; ws.send(JSON.stringify({ id: i, method, params })); };

    const psSelectOption = async (target) => {
      return await eval_(`
        (function() {
          var target = ${JSON.stringify(target)};
          var labels = document.querySelectorAll('label');
          for (var i = 0; i < labels.length; i++) {
            var t = labels[i].textContent.trim();
            if (t === target || t.indexOf(target) >= 0) {
              var forId = labels[i].getAttribute('for');
              if (forId && forId.startsWith('selection-item')) {
                var cb = document.getElementById(forId);
                if (cb) { cb.click(); return 'checked ' + forId + ': ' + t.substring(0, 50); }
              }
              labels[i].click();
              return 'clicked label: ' + t.substring(0, 50);
            }
          }
          return 'NOT_FOUND';
        })()
      `);
    };

    const psClickNext = async () => {
      let r = await eval_(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim();
            if (t === 'Next' || t === 'Continue' || t === 'Submit') {
              var rect = btns[i].getBoundingClientRect();
              if (rect.width > 30 && rect.x > 0) {
                return JSON.stringify({ text: t, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
              }
            }
          }
          return null;
        })()
      `);
      if (!r) return 'no button';
      let bi = JSON.parse(r);
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: bi.x, y: bi.y, button: "left", clickCount: 1 });
      await sleep(100);
      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: bi.x, y: bi.y, button: "left", clickCount: 1 });
      return 'clicked ' + bi.text;
    };

    const psTypeText = async (value) => {
      return await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"], input[type="number"], input:not([type]), textarea, input[type="search"]');
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden' && !inputs[i].id.startsWith('cky') && inputs[i].id !== 'search-input') {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], ${JSON.stringify(value)});
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              return 'typed';
            }
          }
          return 'no input';
        })()
      `);
    };

    const psFillTexts = async (answers) => {
      return await eval_(`
        (function() {
          var answers = ${JSON.stringify(answers)};
          var inputs = document.querySelectorAll('input[type="text"], textarea');
          var filled = 0, aIdx = 0;
          for (var i = 0; i < inputs.length; i++) {
            if (inputs[i].offsetParent !== null && inputs[i].type !== 'hidden' && !inputs[i].id.startsWith('cky') && inputs[i].id !== 'search-input') {
              var proto = inputs[i].tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
              setter.call(inputs[i], answers[aIdx % answers.length]);
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('keyup', { bubbles: true }));
              filled++; aIdx++;
            }
          }
          return filled;
        })()
      `);
    };

    const doDragDrop = async () => {
      // Get positions
      let positions = await eval_(`
        (function() {
          var box79 = null;
          var imgs = document.querySelectorAll('.cdk-drag img');
          for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
          }
          if (!box79) return JSON.stringify({ error: 'no box 79' });
          var br = box79.getBoundingClientRect();

          var dz = document.querySelector('#dropZoneList');
          if (!dz) dz = document.querySelector('.drop-zone');
          if (!dz) return JSON.stringify({ error: 'no drop zone' });
          var dr = dz.getBoundingClientRect();

          return JSON.stringify({
            sx: Math.round(br.x + br.width/2), sy: Math.round(br.y + br.height/2),
            tx: Math.round(dr.x + dr.width/2), ty: Math.round(dr.y + dr.height/2)
          });
        })()
      `);
      let pos = JSON.parse(positions);
      if (pos.error) return 'DRAG ERROR: ' + pos.error;

      L("Drag: (" + pos.sx + "," + pos.sy + ") -> (" + pos.tx + "," + pos.ty + ")");

      // Fire CDP mouse events without waiting for responses
      fire("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.sx, y: pos.sy, button: "left", clickCount: 1, buttons: 1 });
      await sleep(400);

      // Move in steps
      for (let s = 1; s <= 20; s++) {
        let px = Math.round(pos.sx + (pos.tx - pos.sx) * s / 20);
        let py = Math.round(pos.sy + (pos.ty - pos.sy) * s / 20);
        fire("Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y: py, button: "left", buttons: 1 });
        await sleep(40);
      }
      await sleep(300);

      fire("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.tx, y: pos.ty, button: "left", clickCount: 1, buttons: 0 });
      await sleep(1500);

      // Check if drag worked
      let check = await eval_(`document.body.innerText.substring(0, 200)`);
      if (check.includes('drag and drop')) {
        L("CDP drag didn't work. Trying JS pointer events...");
        // Try JS pointer events
        await eval_(`
          (function() {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            var dz = document.querySelector('#dropZoneList') || document.querySelector('.drop-zone');
            var br = box79.getBoundingClientRect();
            var dr = dz.getBoundingClientRect();
            var sx = br.x + br.width/2, sy = br.y + br.height/2;
            var tx = dr.x + dr.width/2, ty = dr.y + dr.height/2;

            box79.dispatchEvent(new PointerEvent('pointerdown', {
              clientX: sx, clientY: sy, bubbles: true, cancelable: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, pressure: 0.5
            }));

            for (var s = 1; s <= 20; s++) {
              var px = sx + (tx - sx) * s / 20;
              var py = sy + (ty - sy) * s / 20;
              document.dispatchEvent(new PointerEvent('pointermove', {
                clientX: px, clientY: py, bubbles: true, cancelable: true,
                pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, pressure: 0.5
              }));
            }

            document.dispatchEvent(new PointerEvent('pointerup', {
              clientX: tx, clientY: ty, bubbles: true, cancelable: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 0
            }));
          })()
        `);
        await sleep(1000);
      }

      return 'drag attempted';
    };

    (async () => {
      await send("DOM.enable");
      await send("Runtime.enable");

      const govTextAnswers = [
        "They should invest more in road maintenance and infrastructure throughout the community.",
        "More affordable housing options would help working families in our area.",
        "Better public transportation access would reduce congestion and improve mobility.",
        "Expanding parks and recreational facilities would benefit all residents.",
        "Investing in local school improvements would strengthen our community.",
        "More support for small business development through streamlined permits."
      ];
      let textIdx = 0;
      let lastQ = '';
      let stuckCount = 0;

      for (let round = 0; round < 40; round++) {
        let pageText, url;
        try {
          url = await eval_(`window.location.href`);
          pageText = await eval_(`document.body ? document.body.innerText.substring(0, 2000) : 'loading'`);
        } catch(e) {
          L("R" + round + ": Loading...");
          await sleep(3000);
          continue;
        }
        if (!pageText || pageText === 'loading') { await sleep(2000); continue; }

        let lower = pageText.toLowerCase();
        let progress = pageText.match(/(\d+)%/);
        L("\n=== R" + round + (progress ? " (" + progress[1] + "%)" : "") + " ===");

        // End states
        if (lower.includes('thank you') || lower.includes('survey is complete') || lower.includes('your response has been recorded')) {
          L("SURVEY COMPLETE!"); L(pageText.substring(0, 300)); break;
        }
        if (lower.includes('unfortunately') || lower.includes('disqualified') || lower.includes('screened out')) {
          L("SCREENED OUT"); L(pageText.substring(0, 300)); break;
        }
        if (!url.includes('purespectrum')) { L("REDIRECTED: " + url); break; }

        // Get question line - check for ? first, then any meaningful text
        let lines = pageText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let question = lines.find(l => l.includes('?') && l.length > 10)
          || lines.find(l => l.includes(':') && l.length > 10 && l.length < 200)
          || lines.find(l => l.length > 15 && l.length < 200 && !l.match(/^\d+%$/) && l !== 'Next' && l !== 'A' && l !== 'Privacy Policy')
          || '';
        L("Q: " + question.substring(0, 120));

        // Stuck detection
        if (question === lastQ) {
          stuckCount++;
          if (stuckCount >= 4) { L("STUCK!"); break; }
        } else { stuckCount = 0; }
        lastQ = question;

        let qLower = question.toLowerCase();

        // Check for drag-and-drop question
        if (qLower.includes('drag') && qLower.includes('drop')) {
          L("DRAG AND DROP detected!");
          let dragResult = await doDragDrop();
          L("Drag result: " + dragResult);
          await sleep(500);
          let c = await psClickNext();
          L("Next: " + c);
          await sleep(3000);
          continue;
        }

        // Count inputs
        let textInputCount = await eval_(`
          (function() {
            var count = 0;
            document.querySelectorAll('input[type="text"], textarea').forEach(function(i) {
              if (i.offsetParent !== null && !i.id.startsWith('cky') && i.id !== 'search-input') count++;
            });
            return count;
          })()
        `);

        let cbCount = await eval_(`document.querySelectorAll('input[type="checkbox"][id^="selection-item"]').length`);
        let radioCount = await eval_(`document.querySelectorAll('input[type="radio"]').length`);

        // Check for "type the code" attention check (check full page text too)
        if (lower.includes('type') && lower.includes('code') || lower.includes('type the')) {
          // Find the code in the full page text
          let codeMatch = pageText.match(/code\s+(\w+)/i) || pageText.match(/type\s+(\w+)\s/i);
          if (codeMatch) {
            let code = codeMatch[1];
            // Skip common false positives
            if (code.toLowerCase() !== 'the' && code.toLowerCase() !== 'in' && code.toLowerCase() !== 'into') {
              L("Attention check code: " + code);
              let r = await psTypeText(code);
              L("Typed: " + r);
              await sleep(500);
              let c = await psClickNext();
              L("Next: " + c);
              await sleep(3000);
              continue;
            }
          }
        }

        L("   txt=" + textInputCount + " cb=" + cbCount + " radio=" + radioCount);

        // Check full page text for zipcode (not just question line)
        if (lower.includes('zipcode') || lower.includes('zip code') || lower.includes('my zipcode')) {
          let r = await psTypeText("83864");
          L("   ZIP: " + r);
        } else if (textInputCount > 0) {
          let answers = govTextAnswers.slice(textIdx, textIdx + textInputCount);
          if (answers.length < textInputCount) answers = govTextAnswers.slice(0, textInputCount);
          let filled = await psFillTexts(answers);
          L("   Filled " + filled + " texts");
          textIdx += filled;
        } else if (cbCount > 0) {
          let target = null;
          if (qLower.includes('sport')) target = 'National Football League';
          else if (qLower.includes('news') || qLower.includes('media')) target = 'Local TV news';
          else if (qLower.includes('social media')) target = 'Facebook';
          else if (qLower.includes('streaming')) target = 'Netflix';
          else if (qLower.includes('store') || qLower.includes('shop')) target = 'Amazon';
          else if (qLower.includes('issue') || qLower.includes('concern') || qLower.includes('important')) target = 'Economy';

          if (target) {
            L("-> " + target);
            let r = await psSelectOption(target);
            L("   " + r);
          } else {
            L("-> first checkbox");
            let r = await eval_(`
              (function() {
                var cbs = document.querySelectorAll('input[type="checkbox"][id^="selection-item"]');
                if (cbs.length > 0) {
                  cbs[0].click();
                  var label = document.querySelector('label[for="' + cbs[0].id + '"]');
                  return 'checked: ' + (label ? label.textContent.trim().substring(0, 50) : cbs[0].id);
                }
                return 'no cbs';
              })()
            `);
            L("   " + r);
          }
        } else if (radioCount > 0) {
          let target = null;
          if (qLower.includes('gender')) target = 'Male';
          else if (qLower.includes('agree')) target = 'Agree';
          else if (qLower.includes('likely')) target = 'Somewhat likely';

          if (target) {
            L("-> " + target);
            let r = await psSelectOption(target);
            L("   " + r);
          } else {
            L("-> first radio");
            let r = await eval_(`
              (function() {
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length > 0) { radios[0].click(); return 'checked first'; }
                return 'no radios';
              })()
            `);
            L("   " + r);
          }
        } else {
          L("   No inputs. Text: " + pageText.substring(0, 200));
        }

        await sleep(500);
        let cont = await psClickNext();
        L("   " + cont);
        await sleep(3000);
      }

      // Final
      L("\n=== FINAL ===");
      try {
        let fUrl = await eval_(`window.location.href`);
        let fPage = await eval_(`document.body ? document.body.innerText.substring(0, 1500) : 'null'`);
        L("URL: " + fUrl.substring(0, 80));
        L("Page:\n" + fPage.substring(0, 800));
      } catch(e) { L("Error: " + e.message); }

      const ss = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      writeFileSync('D:\\_CLAUDE-TOOLS\\cw_survey.png', Buffer.from(ss.data, 'base64'));

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
