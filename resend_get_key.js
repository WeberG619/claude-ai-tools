(function() {
  var allText = document.body.innerText;
  var match = allText.match(/re_[A-Za-z0-9_]+/g);
  var inputs = Array.from(document.querySelectorAll("input, code, pre, [data-testid], [class*=key], [class*=token]"));
  var values = inputs.map(function(e) { return e.tagName + ":" + (e.value || e.textContent || "").substring(0, 100); });
  var clipElem = document.querySelector("[class*=copy], [class*=clipboard], button[title*=Copy]");
  return JSON.stringify({
    reKeys: match,
    inputValues: values,
    clipElem: clipElem ? clipElem.outerHTML.substring(0, 200) : "none",
    dialogText: allText.substring(allText.indexOf("View API key"), allText.indexOf("View API key") + 500)
  });
})();
