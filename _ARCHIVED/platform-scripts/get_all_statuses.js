(function() {
  var btns = document.querySelectorAll("button, [role=button]");
  var statuses = [];
  btns.forEach(function(b) {
    var text = b.textContent.trim().toLowerCase();
    if (text === "pending" || text === "verified" || text === "not started" || text === "failed") {
      var parent = b.parentElement;
      var context = parent ? parent.textContent.trim().replace(/\s+/g, " ").substring(0, 80) : "";
      statuses.push(text + " | context: " + context);
    }
  });
  return statuses.join("\n");
})();