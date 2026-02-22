(function() {
  var result = [];
  result.push("URL: " + window.location.href);
  result.push("Title: " + document.title);
  var headings = document.querySelectorAll("h1, h2, h3, h4");
  headings.forEach(function(h) { result.push("H: " + h.textContent.trim().substring(0,80)); });
  var buttons = document.querySelectorAll("button, [role=button]");
  buttons.forEach(function(b) { result.push("BTN: " + b.textContent.trim().substring(0,80)); });
  var links = document.querySelectorAll("a");
  for (var i = 0; i < Math.min(links.length, 15); i++) {
    result.push("A: " + links[i].textContent.trim().substring(0,60) + " -> " + links[i].href.substring(0,80));
  }
  return result.join("\n");
})();