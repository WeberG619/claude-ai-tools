const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
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
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

function setVal(idx, text) {
  // Escape backticks and backslashes in text for template literal safety
  const escaped = text.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
  return `
    const allTA = document.querySelectorAll('textarea');
    const ta = allTA[${idx}];
    if (ta) {
      ta.focus();
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, \`${escaped}\`);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      ta.dispatchEvent(new Event('change', { bubbles: true }));
      ta.dispatchEvent(new Event('blur', { bubbles: true }));
      return 'filled textarea ' + ${idx};
    }
    return 'textarea ${idx} not found';
  `;
}

function clickRadioByLabel(labelText) {
  const escaped = labelText.replace(/'/g, "\\'");
  return `
    const labels = document.querySelectorAll('label');
    for (const lbl of labels) {
      if (lbl.textContent.trim().startsWith('${escaped}')) {
        const input = lbl.querySelector('input[type="radio"], input[type="checkbox"]');
        if (input) {
          input.click();
          return 'clicked: ${escaped}';
        }
      }
    }
    return 'not found: ${escaped}';
  `;
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  console.log("=== DEMOGRAPHICS ===");

  // Gender: Man
  let r = await eval_(clickRadioByLabel("Man"));
  console.log(r);
  await sleep(200);

  // Race: White
  r = await eval_(clickRadioByLabel("White"));
  console.log(r);
  await sleep(200);

  // English: Native
  r = await eval_(clickRadioByLabel("Native English speaker"));
  console.log(r);
  await sleep(200);

  // Languages textarea (index 0) - leave blank or French
  // Skip - leave blank

  // Location textarea (index 1)
  r = await eval_(setVal(1, "United States"));
  console.log(r);
  await sleep(200);

  // Professional status: Small Business Owner
  r = await eval_(clickRadioByLabel("Small Business Owner"));
  console.log(r);
  await sleep(200);

  // Target employees: 100,001 - 500,000
  r = await eval_(clickRadioByLabel("100,001 - 500,000"));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 1: GOOG Stock ===");
  r = await eval_(clickRadioByLabel("$244.84"));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 2: Book Recommendation ===");
  r = await eval_(clickRadioByLabel("Bad Recommendation"));
  console.log(r);
  await sleep(200);

  // Q2 explanation (textarea index 2)
  r = await eval_(setVal(2, `The Wager by David Grann tells the story of the HMS Wager, an 18th-century British warship that wrecked off the coast of Patagonia in 1741, leading to mutiny and conflicting survival accounts among the crew (source: davidgrann.com/book/the-wager). Phil Ivey is one of the most famous professional poker players in the world, known for his ten World Series of Poker bracelets and his intense, strategic approach to the game. Someone who enjoyed reading about Ivey's career in competitive poker would probably be looking for more content related to gaming, sports competition, or high-stakes decision-making in a modern context. While The Wager does involve survival and tough decisions, the subject matter of 18th-century naval history and shipwreck exploration is pretty far removed from the world of professional poker, so it wouldn't be a natural fit for this reader.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 3: Time Travel ===");
  r = await eval_(setVal(3, `If I could travel back in time, I'd go to ancient Rome around 125 AD to watch the construction of the Pantheon. I've spent a lot of my career working with building technology and architectural documentation, so getting to see how Roman engineers built that massive unreinforced concrete dome without any of the tools or software we rely on today would be a once-in-a-lifetime experience. The Pantheon's dome is still the largest of its kind almost 2,000 years later, which is honestly mind-blowing when you consider what we can barely get permitted and built today. I'd want to understand their construction sequencing, how they managed the formwork, and how they coordinated what must have been hundreds of workers on site. Beyond the building itself, I think it would be fascinating to see the daily routines of the craftsmen and laborers, because their hands-on skills are the kind of thing that never really makes it into the history books but is the backbone of everything we do in construction.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 4: NY Times ===");
  r = await eval_(clickRadioByLabel("Response A"));
  console.log(r);
  await sleep(200);

  // Q4 explanation (textarea index 4)
  r = await eval_(setVal(4, `Response A is the more accurate answer because it correctly states September 18, 1851 without adding any false information. Response B gets the date right but then claims the paper was originally called "the New York Daily Chronicle," which is incorrect. According to the Wikipedia article on the History of The New York Times, the newspaper was originally published as "The New-York Daily Times" before shortening its name in 1857. On top of that, the source URL provided in Response B appears to be a broken or non-standard link, which makes the whole response less trustworthy.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 5: Poem ===");
  r = await eval_(clickRadioByLabel("Response B is a better response"));
  console.log(r);
  await sleep(200);

  // Q5 explanation (textarea index 5)
  r = await eval_(setVal(5, `Response B is clearly the stronger answer because it actually follows the sonnet format that was specifically requested in the prompt. A sonnet has 14 lines with a structured rhyme scheme, and Response B delivers exactly that with three quatrains and a closing couplet, using rhyming pairs like "bed/bread/newlywed" and "away/disarray/dismay." It also nails the tone the prompt asked for, mixing Shakespearean-style language with genuinely funny imagery about being too lazy to walk to the fridge. Response A, on the other hand, reads more like unstructured free verse with no consistent rhyme scheme or meter, so it doesn't meet the basic requirement of being a sonnet at all.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 6: Olympics ===");
  r = await eval_(clickRadioByLabel("Response B"));
  console.log(r);
  await sleep(300);

  // Need to make sure we click the right "Response B" - for Q6 specifically
  // Let me re-check which radio group this belongs to
  r = await eval_(`
    // Find Q6's Response B radio - it's the one with name ceb39538...
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const radio of radios) {
      if (radio.name.startsWith('ceb39538')) {
        const label = radio.closest('label');
        if (label && label.textContent.trim() === 'Response B') {
          radio.click();
          return 'clicked Q6 Response B';
        }
      }
    }
    return 'Q6 Response B not found by name';
  `);
  console.log(r);
  await sleep(200);

  // Q6 explanation (textarea index 6)
  r = await eval_(setVal(6, `Both responses contain the same factual error: they list Delfo Cabrera as representing Great Britain, but he was actually an Argentine athlete who won the marathon (source: olympics.com/en/athletes/delfo-cabrera). Despite sharing this mistake, Response B is the better answer because it presents the same information in a much more concise and readable format. Response A pads out the content with unnecessary filler, like dedicating separate paragraphs to each medal color for every country and including sentences that don't add any real value, such as explaining why it won't list all event winners. Response B delivers the exact same data in a clean, organized way without wasting the reader's time.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 7: London Fog Rubrics ===");

  // Rubric 1: Yes (formal greeting)
  r = await eval_(`
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const radio of radios) {
      if (radio.name.startsWith('ddd53605')) {
        const label = radio.closest('label');
        if (label && label.textContent.trim() === 'Yes') {
          radio.click();
          return 'clicked Q7R1 Yes';
        }
      }
    }
    return 'Q7R1 Yes not found';
  `);
  console.log(r);
  await sleep(200);

  // Q7 Rubric 1 explanation (textarea index 7)
  r = await eval_(setVal(7, `The response opens with "Greetings" followed by "It is a pleasure to assist you with this request," which is both formal and polite. This meets the user's instruction to be greeted in a formal manner before the recipe is presented.`));
  console.log(r);
  await sleep(200);

  // Rubric 2: No (soy milk mentioned despite user hating it)
  r = await eval_(`
    const radios = document.querySelectorAll('input[type="radio"]');
    for (const radio of radios) {
      if (radio.name.startsWith('281d4a17')) {
        const label = radio.closest('label');
        if (label && label.textContent.trim() === 'No') {
          radio.click();
          return 'clicked Q7R2 No';
        }
      }
    }
    return 'Q7R2 No not found';
  `);
  console.log(r);
  await sleep(200);

  // Q7 Rubric 2 explanation (textarea index 8)
  r = await eval_(setVal(8, `The vegan variation fails on this rubric because it explicitly lists soy milk as one of the suggested plant-based alternatives, stating "such as oat milk, almond milk, or soy milk." The user clearly told the chatbot "fyi I hate soy milk," so including it as a recommendation shows the response didn't properly account for the user's stated preferences.`));
  console.log(r);
  await sleep(200);

  console.log("\n=== QUESTION 8: Custom Prompt + Rubrics ===");

  // Q8 prompt (textarea index 9)
  r = await eval_(setVal(9, `I'm working on renovating a mid-century modern home that was built in the early 1960s, and I want to preserve as much of the original architectural character as possible while updating it for how people actually live today. The home has an open floor plan with floor-to-ceiling windows, a flat roof, and exposed beam ceilings throughout the main living area. Recently I discovered that one of the main beams has some water damage from a roof leak that happened years ago before the previous owner had the roof replaced. The staining and some soft spots have me worried about whether the beam is still doing its job structurally.

Please write me a detailed guide on how to evaluate and address water-damaged exposed beams in a mid-century modern home. The tone should be practical and conversational, like getting advice from an experienced contractor friend who knows what he's talking about but doesn't talk down to you. Include at least three specific methods for assessing the extent of the damage, and give me step-by-step instructions for each method so I can actually follow along. Make sure to clearly explain when I should stop trying to figure it out myself and call in a structural engineer instead. Finally, wrap up with a brief section on preventive measures I can take going forward to protect the other beams from the same fate.`));
  console.log(r);
  await sleep(200);

  // Q8 rubric 1 (textarea index 10)
  r = await eval_(setVal(10, `Did the response include at least three specific methods for assessing the extent of water damage to the beam, with step-by-step instructions for each method?`));
  console.log(r);
  await sleep(200);

  // Q8 rubric 2 (textarea index 11)
  r = await eval_(setVal(11, `Did the response clearly explain when it would be appropriate to stop the self-assessment and consult a structural engineer instead?`));
  console.log(r);
  await sleep(200);

  console.log("\n=== EDUCATION & EXPERIENCE ===");

  // Education: Some college coursework
  r = await eval_(clickRadioByLabel("Some college coursework completed"));
  console.log(r);
  await sleep(200);

  // Major: Architecture
  r = await eval_(clickRadioByLabel("Architecture"));
  console.log(r);
  await sleep(200);

  // LinkedIn (textarea index 12) - skip/leave blank

  // Colleges (textarea index 13)
  r = await eval_(setVal(13, `Miami Dade College (2016 - 2018) - Architecture and Building Technology coursework`));
  console.log(r);
  await sleep(200);

  // Work history (textarea index 14)
  r = await eval_(setVal(14, `BIM Ops Studio (2024 - Present) - Principal / BIM Specialist

Architectural Drafting Firm (2020 - 2024) - Architectural Drafter / Technical Professional

Freelance (2018 - Present) - Content and Data Professional`));
  console.log(r);
  await sleep(200);

  // About me (textarea index 15)
  r = await eval_(setVal(15, `I have a background in architecture and building technology, with several years of experience creating construction documents and building information models using Autodesk Revit. I currently run my own small BIM consulting studio where I work with architects and engineers on multi-discipline projects, producing everything from floor plans and elevations to detailed technical documentation. Outside of architecture, I've done a good amount of freelance work in content writing, data entry, and document processing, and I'm comfortable working with tools like Excel, Google Sheets, and various PDF/CAD conversion software. I've also gotten pretty deep into AI tools over the past couple of years, using platforms like Claude and ChatGPT for prompt engineering and workflow automation. I'm a detail-oriented person who enjoys evaluating and analyzing information, which is a big part of why this kind of work appeals to me.`));
  console.log(r);
  await sleep(200);

  // How found us (textarea index 16)
  r = await eval_(setVal(16, `Google search for remote AI training work opportunities.`));
  console.log(r);
  await sleep(200);

  // Hours: 20-40
  r = await eval_(clickRadioByLabel("20-40 hours"));
  console.log(r);
  await sleep(200);

  // Other comments (textarea index 17) - leave blank

  console.log("\n=== VERIFICATION ===");

  // Verify all radio buttons are selected
  r = await eval_(`
    const checked = document.querySelectorAll('input[type="radio"]:checked, input[type="checkbox"]:checked');
    return JSON.stringify(Array.from(checked).map(c => {
      const label = c.closest('label')?.textContent?.trim().substring(0, 60) || c.name;
      return label;
    }));
  `);
  console.log("Checked items:", r);

  // Verify textareas filled
  r = await eval_(`
    const tas = document.querySelectorAll('textarea');
    return JSON.stringify(Array.from(tas).map((ta, i) => ({
      idx: i,
      filled: ta.value.length > 0,
      preview: ta.value.substring(0, 40)
    })).filter(t => t.filled));
  `);
  console.log("Filled textareas:", r);

  ws.close();
  console.log("\nDone! Review the page before submitting.");
})().catch(e => console.error("Error:", e.message));
