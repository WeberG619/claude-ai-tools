(function() {
  var dialogs = document.querySelectorAll("[class*='css-qcrqvd']");
  if (dialogs.length === 0) return "no dialog found";
  var d = dialogs[0];
  return "HTML: " + d.innerHTML.substring(0, 2000);
})();