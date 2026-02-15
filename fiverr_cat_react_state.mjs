// Change category by manipulating React Select's internal state directly
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit"));
  if (!tab) throw new Error("No Fiverr edit tab");
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
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 400)); return null; }
    return r.result?.value;
  };
  async function cdpClick(x, y) {
    // Full mouse event sequence: move, press, release
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
  return { ws, send, eval_, cdpClick, pressKey };
}

async function main() {
  const { ws, send, eval_, cdpClick, pressKey } = await connect();

  // Step 1: Deep inspect the React Select to understand the component tree
  console.log("=== Step 1: Deep inspect React Select ===");
  const inspect = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (!input) return 'input not found';

      // Walk up the tree to find the React fiber
      let fiber = null;
      for (const key of Object.keys(input)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          fiber = input[key];
          break;
        }
      }

      if (!fiber) return 'no React fiber found';

      // Walk up to find the Select component
      let current = fiber;
      let selectInstance = null;
      let depth = 0;
      while (current && depth < 30) {
        if (current.stateNode && current.stateNode.setState &&
            (current.stateNode.props?.options || current.stateNode.state?.menuIsOpen !== undefined)) {
          selectInstance = current.stateNode;
          break;
        }
        // Also check memoizedProps for function components
        if (current.memoizedProps?.options) {
          return JSON.stringify({
            type: 'function_component',
            hasOptions: true,
            optionCount: current.memoizedProps.options?.length,
            options: current.memoizedProps.options?.map(o => typeof o === 'object' ? (o.label || o.name || JSON.stringify(o).substring(0, 50)) : String(o)).slice(0, 20),
            depth
          });
        }
        current = current.return;
        depth++;
      }

      if (selectInstance) {
        return JSON.stringify({
          type: 'class_component',
          hasState: !!selectInstance.state,
          menuIsOpen: selectInstance.state?.menuIsOpen,
          options: selectInstance.props?.options?.map(o => o.label || o.name).slice(0, 20),
          value: selectInstance.props?.value
        });
      }

      return 'walked ' + depth + ' levels, no Select found';
    })()
  `);
  console.log("React inspection:", inspect);

  // Step 2: Try to find React Select's onChange and options via React fiber tree
  console.log("\n=== Step 2: Find Select props via fiber ===");
  const propsInfo = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (!input) return 'input not found';

      let fiber = null;
      for (const key of Object.keys(input)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          fiber = input[key];
          break;
        }
      }
      if (!fiber) return 'no fiber';

      // Collect all props with options as we walk up
      let current = fiber;
      let results = [];
      let depth = 0;
      while (current && depth < 40) {
        const props = current.memoizedProps || current.pendingProps;
        if (props) {
          const keys = Object.keys(props);
          const interesting = keys.filter(k =>
            k === 'options' || k === 'onChange' || k === 'onMenuOpen' ||
            k === 'value' || k === 'selectProps' || k === 'menuIsOpen' ||
            k === 'onInputChange' || k === 'inputValue'
          );
          if (interesting.length > 0) {
            let info = { depth, keys: interesting };
            if (props.options) {
              info.optionCount = props.options.length;
              info.sampleOptions = props.options.slice(0, 5).map(o => {
                if (typeof o === 'object') return { label: o.label, value: o.value };
                return o;
              });
            }
            if (props.value) {
              info.currentValue = typeof props.value === 'object' ?
                { label: props.value.label, value: props.value.value } : props.value;
            }
            if (props.selectProps?.options) {
              info.selectPropsOptions = props.selectProps.options.length;
            }
            results.push(info);
          }
        }
        current = current.return;
        depth++;
      }

      return JSON.stringify(results);
    })()
  `);
  console.log("Props info:", propsInfo);

  // Step 3: Try to call onChange directly with the Programming & Tech option
  console.log("\n=== Step 3: Trigger onChange directly ===");
  const changeResult = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (!input) return 'input not found';

      let fiber = null;
      for (const key of Object.keys(input)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          fiber = input[key];
          break;
        }
      }
      if (!fiber) return 'no fiber';

      // Find the component with onChange and options
      let current = fiber;
      let depth = 0;
      while (current && depth < 40) {
        const props = current.memoizedProps || current.pendingProps;
        if (props && props.onChange && props.options && props.options.length > 0) {
          // Found it! Now find "Programming & Tech" in options
          const options = props.options;
          const target = options.find(o => {
            const label = (o.label || o.name || '').toLowerCase();
            return label.includes('programming') || label.includes('tech');
          });

          if (target) {
            try {
              props.onChange(target, { action: 'select-option', option: target });
              return JSON.stringify({ success: true, selected: target.label || target.value, depth });
            } catch(e) {
              return JSON.stringify({ error: e.message, target: target.label });
            }
          }

          return JSON.stringify({
            noMatch: true,
            availableOptions: options.map(o => o.label || o.value || JSON.stringify(o).substring(0, 40)),
            depth
          });
        }
        current = current.return;
        depth++;
      }

      return 'no onChange+options found after ' + depth + ' levels';
    })()
  `);
  console.log("onChange result:", changeResult);
  await sleep(2000);

  // Step 4: Verify the change
  const state1 = await eval_(`
    JSON.stringify({
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      title: document.querySelector('textarea')?.value
    })
  `);
  console.log("\n=== State after onChange ===", state1);

  // Step 5: If main category changed, handle subcategory
  const cats = JSON.parse(state1 || '{}');
  if (cats.categories?.[0]?.toLowerCase().includes('programming')) {
    console.log("\nMain category changed! Now handling subcategory...");
    await sleep(1500);

    // Inspect subcategory select
    const subInfo = await eval_(`
      (function() {
        const input = document.querySelector('#react-select-3-input');
        if (!input) return 'subcategory input not found';

        let fiber = null;
        for (const key of Object.keys(input)) {
          if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
            fiber = input[key];
            break;
          }
        }
        if (!fiber) return 'no fiber';

        let current = fiber;
        let depth = 0;
        while (current && depth < 40) {
          const props = current.memoizedProps || current.pendingProps;
          if (props && props.onChange && props.options && props.options.length > 0) {
            const options = props.options;
            // Look for AI-related subcategory
            const priorities = ['ai app', 'ai agent', 'chatbot', 'ai integration', 'ai service', 'software', 'web app'];
            let target = null;
            for (const kw of priorities) {
              target = options.find(o => (o.label || '').toLowerCase().includes(kw));
              if (target) break;
            }

            if (target) {
              try {
                props.onChange(target, { action: 'select-option', option: target });
                return JSON.stringify({ success: true, selected: target.label || target.value });
              } catch(e) {
                return JSON.stringify({ error: e.message });
              }
            }

            return JSON.stringify({
              noMatch: true,
              available: options.map(o => o.label || o.value).slice(0, 20)
            });
          }
          current = current.return;
          depth++;
        }
        return 'no onChange+options found after ' + depth + ' levels';
      })()
    `);
    console.log("Subcategory result:", subInfo);
    await sleep(2000);
  } else {
    console.log("\nMain category did NOT change. Trying alternative approach...");

    // Alternative: Try to find the form's state management (Redux, Context, etc.)
    const altResult = await eval_(`
      (function() {
        // Look for any Redux store or React context
        const root = document.querySelector('#root') || document.querySelector('#__next') || document.querySelector('[data-reactroot]');
        if (!root) return 'no root';

        let fiber = null;
        for (const key of Object.keys(root)) {
          if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance') || key.startsWith('_reactRootContainer')) {
            fiber = root[key];
            break;
          }
        }

        // Try _reactRootContainer approach
        if (root._reactRootContainer) {
          return 'found _reactRootContainer: ' + typeof root._reactRootContainer;
        }

        // Check for __NEXT_DATA__ or similar global state
        if (window.__NEXT_DATA__) return 'Next.js app found';
        if (window.__REDUX_DEVTOOLS_EXTENSION__) return 'Redux available';

        // Try to find the actual control div and dispatch a proper mousedown
        const input2 = document.querySelector('#react-select-2-input');
        const container = input2?.closest('[class*="container"]');
        const control = container?.querySelector('[class*="control"]');

        if (control) {
          // Get exact rect
          const rect = control.getBoundingClientRect();
          return JSON.stringify({
            controlRect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
            controlClass: control.className.substring(0, 80),
            // Check what event handlers are on it
            fiberKey: Object.keys(control).filter(k => k.startsWith('__react')).join(', ')
          });
        }

        return 'no control found';
      })()
    `);
    console.log("Alternative inspection:", altResult);

    // Try clicking the actual control div with proper coordinates
    if (altResult && altResult.includes('controlRect')) {
      const info = JSON.parse(altResult);
      const { x, y, w, h } = info.controlRect;
      const clickX = x + w / 2;
      const clickY = y + h / 2;

      console.log(`\nClicking control at (${clickX}, ${clickY}) [rect: ${w}x${h}]...`);

      // Try a more realistic mouse sequence
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: clickX, y: clickY });
      await sleep(200);
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: clickX, y: clickY, button: "left", clickCount: 1,
        buttons: 1
      });
      await sleep(100);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: clickX, y: clickY, button: "left", clickCount: 1
      });
      await sleep(2000);

      const afterClick = await eval_(`
        JSON.stringify({
          menuVisible: !!document.querySelector('[class*="MenuList"], [class*="menuList"]'),
          optionCount: document.querySelectorAll('[class*="option"]').length,
          activeEl: document.activeElement?.id || document.activeElement?.tagName,
          ariaExpanded: !!document.querySelector('[aria-expanded="true"]')
        })
      `);
      console.log("After control click:", afterClick);

      const parsed = JSON.parse(afterClick);
      if (parsed.menuVisible || parsed.optionCount > 0) {
        console.log("Menu opened! Looking for Programming & Tech...");
        // Find and click it
        const progCoords = await eval_(`
          (function() {
            const opts = Array.from(document.querySelectorAll('[class*="option"], [role="option"]')).filter(o => o.offsetParent !== null);
            const prog = opts.find(o => o.textContent.toLowerCase().includes('programming'));
            if (prog) {
              const rect = prog.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: prog.textContent.trim() });
            }
            return JSON.stringify({ options: opts.map(o => o.textContent.trim()).slice(0, 15) });
          })()
        `);
        console.log("Programming option:", progCoords);

        const progParsed = JSON.parse(progCoords);
        if (progParsed.x) {
          await cdpClick(progParsed.x, progParsed.y);
          await sleep(2000);
        }
      }
    }
  }

  // Final state
  const finalState = await eval_(`
    JSON.stringify({
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      title: document.querySelector('textarea')?.value
    })
  `);
  console.log("\n=== FINAL STATE ===", finalState);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
