import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
const L = (msg) => out.push(msg);

setTimeout(() => {
  L("TIMEOUT");
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
}, 30000);

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const psTab = tabs.find(t => t.type === "page" && t.url.includes('purespectrum'));
  if (!psTab) { L("No PS tab"); writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n')); process.exit(1); }

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
    const eval_ = async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result?.value; };

    (async () => {
      // Synchronous drag simulation - all events dispatched immediately
      let result = await eval_(`
        (function() {
          var log = [];
          var box79 = null;
          var imgs = document.querySelectorAll('.cdk-drag img');
          for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
          }
          if (!box79) return 'no box 79';

          var dz = document.querySelector('#dropZoneList');
          if (!dz) return 'no drop zone';

          var br = box79.getBoundingClientRect();
          var dr = dz.getBoundingClientRect();
          var sx = br.x + br.width/2, sy = br.y + br.height/2;
          var tx = dr.x + dr.width/2, ty = dr.y + dr.height/2;
          log.push('from(' + Math.round(sx) + ',' + Math.round(sy) + ')to(' + Math.round(tx) + ',' + Math.round(ty) + ')');

          // Dispatch all pointer events synchronously
          box79.dispatchEvent(new PointerEvent('pointerdown', {
            clientX: sx, clientY: sy, screenX: sx, screenY: sy,
            bubbles: true, cancelable: true, composed: true,
            pointerId: 1, pointerType: 'mouse', isPrimary: true,
            button: 0, buttons: 1, width: 1, height: 1, pressure: 0.5
          }));
          log.push('pointerdown');

          // Move steps synchronously
          for (var s = 1; s <= 20; s++) {
            var px = sx + (tx - sx) * s / 20;
            var py = sy + (ty - sy) * s / 20;
            document.dispatchEvent(new PointerEvent('pointermove', {
              clientX: px, clientY: py, screenX: px, screenY: py,
              bubbles: true, cancelable: true, composed: true,
              pointerId: 1, pointerType: 'mouse', isPrimary: true,
              button: 0, buttons: 1, width: 1, height: 1, pressure: 0.5
            }));
          }
          log.push('moved 20 steps');

          // Also dispatch on document for good measure
          document.dispatchEvent(new PointerEvent('pointerup', {
            clientX: tx, clientY: ty, screenX: tx, screenY: ty,
            bubbles: true, cancelable: true, composed: true,
            pointerId: 1, pointerType: 'mouse', isPrimary: true,
            button: 0, buttons: 0, width: 1, height: 1, pressure: 0
          }));
          log.push('pointerup');

          log.push('dz children: ' + dz.children.length + ' html: ' + dz.innerHTML.substring(0, 150));
          return log.join(' | ');
        })()
      `);
      L("Sync drag: " + result);

      await sleep(1000);

      // Check page state
      let page = await eval_(`document.body.innerText.substring(0, 400)`);
      L("Page: " + page.substring(0, 300));

      // If still on drag page, try approach 2: use mouse events on the document
      if (page.includes('drag and drop')) {
        L("\\nTrying mouse events on document...");
        let r2 = await eval_(`
          (function() {
            var box79 = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79 = imgs[i].closest('.cdk-drag'); break; }
            }
            var dz = document.querySelector('#dropZoneList');
            var br = box79.getBoundingClientRect();
            var dr = dz.getBoundingClientRect();
            var sx = br.x + br.width/2, sy = br.y + br.height/2;
            var tx = dr.x + dr.width/2, ty = dr.y + dr.height/2;

            // mousedown on element
            box79.dispatchEvent(new MouseEvent('mousedown', {
              clientX: sx, clientY: sy, bubbles: true, cancelable: true,
              button: 0, buttons: 1
            }));

            // mousemove on document
            for (var s = 1; s <= 20; s++) {
              var px = sx + (tx - sx) * s / 20;
              var py = sy + (ty - sy) * s / 20;
              document.dispatchEvent(new MouseEvent('mousemove', {
                clientX: px, clientY: py, bubbles: true, cancelable: true,
                button: 0, buttons: 1
              }));
            }

            // mouseup on document
            document.dispatchEvent(new MouseEvent('mouseup', {
              clientX: tx, clientY: ty, bubbles: true, cancelable: true,
              button: 0, buttons: 0
            }));

            return 'done. dz: ' + dz.innerHTML.substring(0, 150);
          })()
        `);
        L("Mouse events: " + r2);
        await sleep(1000);

        page = await eval_(`document.body.innerText.substring(0, 400)`);
        L("Page after mouse: " + page.substring(0, 200));
      }

      // If still stuck, try approach 3: find Angular component and call methods
      if (page.includes('drag and drop')) {
        L("\\nTrying Angular component access...");
        let r3 = await eval_(`
          (function() {
            // Try to access Angular CDK internals
            var dz = document.querySelector('#dropZoneList');
            var box79el = null;
            var imgs = document.querySelectorAll('.cdk-drag img');
            for (var i = 0; i < imgs.length; i++) {
              if (imgs[i].alt === '79') { box79el = imgs[i].closest('.cdk-drag'); break; }
            }

            // Check for __ngContext__ on elements
            var dzNg = dz ? dz.__ngContext__ : null;
            var boxNg = box79el ? box79el.__ngContext__ : null;

            // Try ng.getComponent
            var ngRef = null;
            try {
              if (typeof ng !== 'undefined') {
                ngRef = ng.getComponent(box79el);
              }
            } catch(e) {}

            // Check for cdkDrag directive instance
            var directives = null;
            try {
              if (typeof ng !== 'undefined') {
                directives = ng.getDirectives(box79el);
              }
            } catch(e) {}

            return JSON.stringify({
              dzNgType: dzNg ? typeof dzNg : 'null',
              boxNgType: boxNg ? typeof boxNg : 'null',
              ngRef: ngRef ? 'found' : 'null',
              directives: directives ? directives.length + ' directives' : 'null',
              directiveTypes: directives ? directives.map(function(d) { return d.constructor.name; }) : []
            });
          })()
        `);
        L("Angular: " + r3);
      }

      // Screenshot
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
