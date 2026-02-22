(function() {
  var links = document.querySelectorAll("a");
  var result = [];
  links.forEach(function(a, i) {
    if (a.href.includes("domain")) {
      result.push("LINK" + i + ": " + a.textContent.trim().substring(0,60) + " -> " + a.href);
    }
  });
  var rows = document.querySelectorAll("tr, [class*='row'], [class*='Row']");
  rows.forEach(function(r, i) {
    var text = r.textContent.trim().replace(/\s+/g, " ").substring(0, 150);
    if (text.includes("bimops") || text.includes("domain")) {
      result.push("ROW" + i + ": " + text);
    }
  });
  var body = document.body.innerText;
  var idx = body.indexOf("bimops");
  if (idx > -1) {
    result.push("TEXT: " + body.substring(Math.max(0,idx-20), idx+100).replace(/\s+/g, " "));
  }
  return result.join("\n");
})();