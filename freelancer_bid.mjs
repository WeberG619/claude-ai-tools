// Bid on top Freelancer jobs
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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

async function typeText(send, text) {
  for (const char of text) {
    if (char === '\n') {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", keyCode: 13 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", keyCode: 13 });
    } else {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
      await send("Input.dispatchKeyEvent", { type: "char", text: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
    }
    await sleep(10);
  }
}

const JOBS = [
  {
    url: "https://www.freelancer.com/projects/academic-writing/Dissertation-Proofreading-Needed/details",
    bidAmount: "300",
    bidDays: "3",
    proposal: `I'd be happy to proofread your Tax Law dissertation with careful attention to detail.

My approach:
- Line-by-line review for grammar, punctuation, and spelling
- Consistency checks on citation format and legal terminology
- Clarity improvements while preserving your academic voice
- Track changes in Word so you can review every edit

I work with academic manuscripts regularly and understand the precision required for dissertation submissions. I can turn this around within 3 days with a thorough, professional review.

Happy to discuss your specific requirements or timeline. Looking forward to helping you submit a polished manuscript.`
  },
  {
    url: "https://www.freelancer.com/projects/creative-writing/Classic-Website-Copywriting-Editing/details",
    bidAmount: "200",
    bidDays: "5",
    proposal: `I can write polished, elegant website copy that matches your classic aesthetic.

What I'll deliver:
- Headlines and section intros with a refined tone
- Clear, persuasive calls-to-action
- Micro-copy that reads smoothly throughout
- Consistent voice across all pages

I focus on writing that's clean and purposeful — no filler, no jargon, just words that serve your design. I'll work closely with your layout to ensure every piece of copy fits both visually and contextually.

Happy to start with a sample section so you can see the style before committing to the full project.`
  },
  {
    url: "https://www.freelancer.com/projects/excel-vba/Excel-Text-Data-Cleanup/details",
    bidAmount: "280",
    bidDays: "3",
    proposal: `I can handle this Excel text data cleanup efficiently and accurately.

My approach:
- Import/paste raw text into properly structured Excel columns
- Clean and standardize formatting (consistent casing, spacing, punctuation)
- Remove duplicates and fix encoding issues
- Validate entries for completeness and consistency
- Deliver a ready-to-use, properly formatted workbook

I work with Excel daily for data processing tasks and can turn this around quickly. Happy to discuss the specific structure you need for the final output.`
  }
];

async function main() {
  const { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // First check remaining bids
  console.log("=== Checking bid allowance ===");
  let r = await eval_(`
    window.location.href = 'https://www.freelancer.com/users/settings/membership';
    return 'navigating...';
  `);
  await sleep(5000);

  r = await eval_(`
    const bodyText = document.body?.innerText || '';
    // Look for bid info
    const bidInfo = bodyText.match(/\\d+\\s*(of|\\/)\\s*\\d+\\s*bids?/i)?.[0] || '';
    const planInfo = bodyText.match(/(free|basic|plus|professional|premier)\\s*plan/i)?.[0] || '';
    return JSON.stringify({
      url: location.href,
      bidInfo,
      planInfo,
      preview: bodyText.substring(0, 2000)
    });
  `);
  console.log("Membership:", r);

  // Now bid on each job
  for (const job of JOBS) {
    console.log(`\n\n========================================`);
    console.log(`Bidding on: ${job.url.split('/').pop()}`);
    console.log(`Amount: $${job.bidAmount} | Days: ${job.bidDays}`);
    console.log(`========================================`);

    // Navigate to job
    await eval_(`window.location.href = ${JSON.stringify(job.url)}; return 'ok';`);
    await sleep(5000);

    // Check if we can bid (look for bid form or "Place Bid" button)
    r = await eval_(`
      const url = location.href;
      const title = document.querySelector('h1')?.textContent?.trim() || '';

      // Check for existing bid
      const alreadyBid = document.body?.innerText?.includes('You have already bid') ||
                         document.body?.innerText?.includes('Your bid') ||
                         document.querySelector('[class*="already-bid"]');

      // Find bid button
      const bidBtn = document.querySelector('button[class*="PlaceBid"], button[class*="place-bid"], a[href*="place-bid"]');
      const bidBtnText = bidBtn?.textContent?.trim() || '';

      // Check for bid form already visible
      const bidForm = document.querySelector('[class*="BidForm"], [class*="bid-form"], textarea[name*="description"]');
      const hasBidForm = !!bidForm;

      // Check for amount input
      const amountInput = document.querySelector('input[name*="amount"], input[name*="bid"], input[type="number"]');

      return JSON.stringify({
        url, title, alreadyBid: !!alreadyBid, bidBtnText,
        hasBidForm, hasAmountInput: !!amountInput,
        preview: document.body?.innerText?.substring(0, 1500)
      });
    `);
    console.log("Page state:", r);

    const state = JSON.parse(r);

    if (state.alreadyBid) {
      console.log("SKIP - Already bid on this job");
      continue;
    }

    // Look for "Place Bid" or equivalent button and click it
    r = await eval_(`
      // Find all buttons/links related to bidding
      const elements = Array.from(document.querySelectorAll('button, a, [role="button"]'))
        .filter(el => {
          const text = el.textContent.trim().toLowerCase();
          return (text.includes('bid') || text.includes('proposal')) && el.offsetParent !== null;
        })
        .map(el => ({
          tag: el.tagName, text: el.textContent.trim().substring(0, 50),
          class: (el.className?.toString() || '').substring(0, 80),
          href: el.href || '',
          rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }
        }));

      return JSON.stringify(elements);
    `);
    console.log("Bid-related elements:", r);

    const bidElements = JSON.parse(r);

    // Try to find and click "Place Bid" button
    const placeBidBtn = bidElements.find(el =>
      el.text.toLowerCase().includes('place bid') ||
      el.text.toLowerCase().includes('place a bid')
    );

    if (placeBidBtn) {
      console.log(`Clicking: "${placeBidBtn.text}"`);
      await eval_(`
        const btn = Array.from(document.querySelectorAll('button, a, [role="button"]'))
          .find(el => el.textContent.trim().toLowerCase().includes('place bid') || el.textContent.trim().toLowerCase().includes('place a bid'));
        if (btn) btn.click();
      `);
      await sleep(2000);
    }

    // Now look for the bid form
    r = await eval_(`
      // Find form inputs
      const inputs = Array.from(document.querySelectorAll('input, textarea'))
        .filter(el => el.offsetParent !== null && el.type !== 'hidden')
        .map(el => ({
          tag: el.tagName, type: el.type, name: el.name || '',
          id: el.id || '', placeholder: (el.placeholder || '').substring(0, 50),
          class: (el.className?.toString() || '').substring(0, 80),
          rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width) }
        }));

      return JSON.stringify(inputs);
    `);
    console.log("Form inputs:", r);

    const inputs = JSON.parse(r);

    // Find amount input (likely a number input near "bid" text)
    const amountInput = inputs.find(i =>
      i.name.includes('amount') || i.name.includes('bid') ||
      i.placeholder.toLowerCase().includes('amount') ||
      (i.type === 'number' || i.type === 'text') && i.rect.y > 200
    );

    // Find description/proposal textarea
    const descInput = inputs.find(i =>
      i.tag === 'TEXTAREA' ||
      i.name.includes('description') || i.name.includes('proposal') ||
      i.placeholder.toLowerCase().includes('describe') || i.placeholder.toLowerCase().includes('proposal')
    );

    // Find delivery days input
    const daysInput = inputs.find(i =>
      i.name.includes('day') || i.name.includes('period') || i.name.includes('delivery') ||
      i.placeholder.toLowerCase().includes('day')
    );

    console.log("Amount input:", amountInput ? `${amountInput.name || amountInput.id} at (${amountInput.rect.x},${amountInput.rect.y})` : "NOT FOUND");
    console.log("Desc input:", descInput ? `${descInput.name || descInput.id} at (${descInput.rect.x},${descInput.rect.y})` : "NOT FOUND");
    console.log("Days input:", daysInput ? `${daysInput.name || daysInput.id} at (${daysInput.rect.x},${daysInput.rect.y})` : "NOT FOUND");

    if (!amountInput && !descInput) {
      console.log("Cannot find bid form, checking page further...");

      // Check if there's an iframe or modal
      r = await eval_(`
        const iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({ src: f.src?.substring(0, 100), rect: f.getBoundingClientRect() }));
        const modals = Array.from(document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({ class: (el.className?.toString() || '').substring(0, 100), text: el.textContent?.substring(0, 200) }));

        // Also try scrolling down to find the form
        window.scrollTo(0, document.body.scrollHeight);

        return JSON.stringify({ iframes, modals });
      `);
      console.log("Iframes/modals:", r);
      await sleep(2000);

      // Retry finding inputs after scroll
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input, textarea'))
          .filter(el => el.offsetParent !== null && el.type !== 'hidden')
          .map(el => ({
            tag: el.tagName, type: el.type, name: el.name || '',
            id: el.id || '', placeholder: (el.placeholder || '').substring(0, 50),
            rect: { y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width) }
          }));
        return JSON.stringify(inputs);
      `);
      console.log("Inputs after scroll:", r);
      continue;
    }

    // Fill the amount
    if (amountInput) {
      const selector = amountInput.id ? `#${amountInput.id}` :
                       amountInput.name ? `[name="${amountInput.name}"]` :
                       `input[type="${amountInput.type}"]`;
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          el.focus();
          el.select();
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(el, ${JSON.stringify(job.bidAmount)});
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      `);
      console.log(`Set amount to $${job.bidAmount}`);
      await sleep(300);
    }

    // Fill delivery days
    if (daysInput) {
      const selector = daysInput.id ? `#${daysInput.id}` :
                       daysInput.name ? `[name="${daysInput.name}"]` :
                       `input[placeholder*="day"]`;
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          el.focus();
          el.select();
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(el, ${JSON.stringify(job.bidDays)});
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      `);
      console.log(`Set days to ${job.bidDays}`);
      await sleep(300);
    }

    // Fill description/proposal
    if (descInput) {
      const selector = descInput.id ? `#${descInput.id}` :
                       descInput.name ? `[name="${descInput.name}"]` :
                       'textarea';
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          el.focus();
          el.select();
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(el, ${JSON.stringify(job.proposal)});
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      `);
      console.log("Set proposal text");
      await sleep(300);
    }

    // Check the form state before submitting
    r = await eval_(`
      const formState = {};
      document.querySelectorAll('input, textarea').forEach(el => {
        if (el.offsetParent !== null && el.type !== 'hidden' && el.value) {
          formState[el.name || el.id || el.tagName] = el.value.substring(0, 100);
        }
      });

      // Find submit button
      const submitBtn = Array.from(document.querySelectorAll('button'))
        .find(b => {
          const text = b.textContent.trim().toLowerCase();
          return (text.includes('place bid') || text.includes('submit') || text.includes('send')) && b.offsetParent !== null;
        });

      return JSON.stringify({
        formState,
        submitBtn: submitBtn ? submitBtn.textContent.trim() : null,
        submitDisabled: submitBtn?.disabled
      });
    `);
    console.log("Pre-submit state:", r);

    const preSubmit = JSON.parse(r);
    if (preSubmit.submitBtn && !preSubmit.submitDisabled) {
      console.log(`Clicking "${preSubmit.submitBtn}"...`);
      await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => {
            const text = b.textContent.trim().toLowerCase();
            return (text.includes('place bid') || text.includes('submit') || text.includes('send')) && b.offsetParent !== null;
          });
        if (btn) btn.click();
      `);
      await sleep(3000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          errors: Array.from(document.querySelectorAll('[class*="error" i], [role="alert"], [class*="Error"]'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 100))
            .filter(t => t.length > 3),
          success: document.body?.innerText?.includes('bid has been placed') || document.body?.innerText?.includes('successfully')
        });
      `);
      console.log("Submit result:", r);
    } else {
      console.log("No submit button found or button is disabled");
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
