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
  const tab = tabs.find(t => t.type === "page");

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
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

    (async () => {
      // Navigate to a $5.76 instant survey (25 min)
      const surveyUrl = "https://workplace.clickworker.com/en/workplace/jobs/1079433/edit?instant_job_id=05e3ce8d-8d3c-4f49-a080-eec49684235c&instant_job_source=cint";
      await send("Page.navigate", { url: surveyUrl });
      await sleep(5000);

      let url = await eval_(`window.location.href`);
      L("URL: " + url);

      if (url.includes('two_fa')) {
        L("BLOCKED BY 2FA");
        ws.close();
        writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
        process.exit(0);
      }

      // Get page content
      let pageText = await eval_(`document.body.innerText.substring(0, 5000)`);
      L("PAGE TEXT:");
      L(pageText);

      // Get form elements
      let formJson = await eval_(`
        (function() {
          var inputs = document.querySelectorAll('input, select, textarea, button');
          return JSON.stringify(Array.from(inputs).filter(function(i) {
            return i.offsetParent !== null;
          }).map(function(i) {
            return {
              tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '',
              value: (i.value || '').substring(0, 80),
              text: i.textContent ? i.textContent.trim().substring(0, 80) : '',
              label: (i.labels && i.labels[0]) ? i.labels[0].textContent.trim().substring(0, 120) : ''
            };
          }).slice(0, 30));
        })()
      `);
      L("FORM: " + formJson);

      // Get external links
      let linksJson = await eval_(`
        (function() {
          var links = document.querySelectorAll('a');
          return JSON.stringify(Array.from(links).filter(function(a) {
            return a.href && !a.href.includes('clickworker') && a.offsetParent !== null;
          }).map(function(a) {
            return { text: a.textContent.trim().substring(0, 80), href: a.href.substring(0, 200) };
          }));
        })()
      `);
      L("External links: " + linksJson);

      // Get iframes
      let iframesJson = await eval_(`
        (function() {
          var iframes = document.querySelectorAll('iframe');
          return JSON.stringify(Array.from(iframes).map(function(f) {
            return { src: (f.src || '').substring(0, 200) };
          }));
        })()
      `);
      L("Iframes: " + iframesJson);

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
