// Close unnecessary tabs - keep only the main platform pages
const CDP_HTTP = "http://localhost:9222";

async function main() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();

  // Tabs to KEEP (main platform pages we need)
  const keepUrls = [
    "fiverr.com/join",
    "peopleperhour.com/freelancer/register",
    "freelancer.com/new-freelancer",
    "guru.com/pro/ProfileBuild",
    // Keep these platform homepages if actively using
    "freelancer.com/jobs",
    "peopleperhour.com/freelance-jobs",
  ];

  // Tabs to CLOSE: old platform homepages we opened earlier, iframes, trackers, workers
  const closableTypes = ["iframe", "worker", "service_worker"];
  const closableUrls = [
    "insight.adsrvr.org",
    "doubleclick.net",
    "googletagmanager.com",
    "recaptcha.net",
    "online-metrix.net",
    "px-cloud.net",
    "casalemedia.com",
    "adsrvr.org",
    "f-cdn.com",
    "ogs.google.com",
    "accounts.google.com/RotateCookies",
  ];

  // Also close platform homepages we don't need open anymore
  const closablePages = [
    "freelancer.com/$",     // homepage
    "fiverr.com/$",         // homepage (not /join)
    "textbroker.com",
    "cadcrowd.com",
    "contra.com",
    "peopleperhour.com/$",  // homepage (not /freelancer/register)
    "freeup.net",
    "outlier.ai",
    "dataannotation.tech",
    "console.cloud.google.com",
    "chrome://newtab",
    "chrome://newtab-footer",
  ];

  let closed = 0;
  let kept = 0;

  for (const tab of tabs) {
    // Always close non-page types
    if (closableTypes.includes(tab.type)) {
      try {
        await fetch(`${CDP_HTTP}/json/close/${tab.id}`, { method: "PUT" });
        closed++;
      } catch (e) {}
      continue;
    }

    // Close tracker/ad iframes
    if (closableUrls.some(u => tab.url.includes(u))) {
      try {
        await fetch(`${CDP_HTTP}/json/close/${tab.id}`, { method: "PUT" });
        closed++;
      } catch (e) {}
      continue;
    }

    // Close specific pages we don't need
    const shouldClose = closablePages.some(pattern => {
      if (pattern.endsWith("$")) {
        // Exact domain match (homepage only)
        const domain = pattern.slice(0, -1);
        const url = new URL(tab.url);
        return url.hostname.includes(domain.replace("/", "")) && (url.pathname === "/" || url.pathname === "");
      }
      return tab.url.includes(pattern);
    });

    if (shouldClose) {
      console.log(`Closing: [${tab.type}] ${tab.title?.substring(0, 50)} - ${tab.url.substring(0, 80)}`);
      try {
        await fetch(`${CDP_HTTP}/json/close/${tab.id}`, { method: "PUT" });
        closed++;
      } catch (e) {}
      continue;
    }

    // Check if this is a tab we should keep
    const isKeep = keepUrls.some(u => tab.url.includes(u));
    if (tab.type === "page") {
      if (isKeep) {
        console.log(`Keeping: ${tab.title?.substring(0, 50)} - ${tab.url.substring(0, 80)}`);
      } else {
        console.log(`Keeping (unlisted): ${tab.title?.substring(0, 50)} - ${tab.url.substring(0, 80)}`);
      }
      kept++;
    }
  }

  console.log(`\nClosed ${closed} tabs, kept ${kept} page tabs`);
}

main().catch(e => console.error("Error:", e.message));
