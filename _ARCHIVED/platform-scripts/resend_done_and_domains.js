(function() {
  var btn = Array.from(document.querySelectorAll("button")).find(function(b) { return b.textContent.trim() === "Done"; });
  if (btn) { btn.click(); return "clicked Done"; }
  return "no Done button";
})();
