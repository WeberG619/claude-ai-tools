// Open gig platform signup pages in existing Chrome via CDP
// Runs on Windows side to access localhost:9222

const PLATFORMS = [
  ["DataAnnotation.tech", "https://www.dataannotation.tech/"],
  ["Outlier AI", "https://outlier.ai/"],
  ["iWriter", "https://www.iwriter.com/"],
  ["Textbroker", "https://www.textbroker.com/"],
  ["Freelancer.com", "https://www.freelancer.com/"],
  ["Fiverr", "https://www.fiverr.com/"],
  ["PeoplePerHour", "https://www.peopleperhour.com/"],
  ["Contra", "https://contra.com/"],
  ["CAD Crowd", "https://www.cadcrowd.com/"],
  ["Guru.com", "https://www.guru.com/"],
];

async function main() {
  // Get CDP websocket URL
  console.log("Connecting to Chrome CDP on localhost:9222...");
  const res = await fetch("http://localhost:9222/json/version");
  const info = await res.json();
  console.log("Browser:", info.Browser);
  const wsUrl = info.webSocketDebuggerUrl;
  console.log("WebSocket:", wsUrl);

  // Use CDP to create new tabs
  for (const [name, url] of PLATFORMS) {
    try {
      const createRes = await fetch(`http://localhost:9222/json/new?${url}`, { method: "PUT" });
      const tab = await createRes.json();
      console.log(`Opened: ${name} -> ${tab.url || url}`);
    } catch (e) {
      console.error(`Failed: ${name} - ${e.message}`);
    }
  }

  console.log(`\nDone! Opened ${PLATFORMS.length} tabs.`);
}

main().catch(console.error);
