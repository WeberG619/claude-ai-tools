(function() {
  var btns = Array.from(document.querySelectorAll("button, a"));
  var domainBtns = btns.filter(function(b) { return b.textContent.toLowerCase().includes("domain"); });
  return domainBtns.map(function(b,i) { return i + ":" + b.tagName + ":" + b.textContent.trim().substring(0,50) + ":" + (b.href || "no-href"); }).join("\n");
})();
