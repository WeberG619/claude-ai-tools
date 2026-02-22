(function() {
  var body = document.body.innerText;
  var sections = ["Domain Verification", "DKIM", "Enable Sending", "SPF", "Enable Receiving", "MX", "Configuration"];
  var result = [];
  sections.forEach(function(s) {
    var idx = body.indexOf(s);
    if (idx > -1) {
      result.push(s + ": " + body.substring(idx, idx + 200).replace(/\s+/g, " "));
    }
  });
  var badges = document.querySelectorAll("[class*='badge'], [class*='Badge'], [class*='status'], [class*='Status']");
  badges.forEach(function(b, i) {
    result.push("BADGE" + i + ": " + b.textContent.trim() + " class=" + b.className.substring(0,40));
  });
  return result.join("\n");
})();