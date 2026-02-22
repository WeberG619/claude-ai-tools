// Open Fiverr signup page in Chrome
const CDP_HTTP = "http://localhost:9222";

async function main() {
  // Open Fiverr signup in new tab
  const url = "https://www.fiverr.com/join";
  const res = await fetch(`${CDP_HTTP}/json/new?${url}`, { method: "PUT" });
  const tab = await res.json();
  console.log("Opened Fiverr signup:", tab.url);

  // Also open PeoplePerHour signup
  const url2 = "https://www.peopleperhour.com/freelancer/register";
  const res2 = await fetch(`${CDP_HTTP}/json/new?${url2}`, { method: "PUT" });
  const tab2 = await res2.json();
  console.log("Opened PeoplePerHour signup:", tab2.url);
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
