(function() {
  var options = document.querySelectorAll("[role=option], [role=listbox] > *, li[class]");
  var result = [];
  options.forEach(function(o, i) {
    result.push("OPT" + i + ": text=" + o.textContent.trim() + " role=" + (o.getAttribute("role")||"") + " tag=" + o.tagName);
  });
  var listboxes = document.querySelectorAll("[role=listbox]");
  listboxes.forEach(function(lb, i) {
    result.push("LISTBOX" + i + ": " + lb.innerHTML.substring(0, 500));
  });
  return result.join("\n");
})();