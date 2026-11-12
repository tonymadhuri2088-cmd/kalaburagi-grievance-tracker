// Makes every page installable as an app: registers the service worker, offers an Install button and an iOS hint.
(function () {
  "use strict";
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }
  var standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  var deferred = null;
  var ua = navigator.userAgent || "";
  var isIos = /iphone|ipad|ipod/i.test(ua) && !window.MSStream;

  function setButtons() {
    var buttons = document.querySelectorAll("[data-install]");
    buttons.forEach(function (button) {
      if (standalone) { button.hidden = true; return; }
      button.hidden = !(deferred || isIos);
    });
    document.querySelectorAll("[data-install-ios]").forEach(function (note) { note.hidden = standalone || !isIos; });
    document.querySelectorAll("[data-installed]").forEach(function (note) { note.hidden = !standalone; });
  }

  window.addEventListener("beforeinstallprompt", function (event) { event.preventDefault(); deferred = event; setButtons(); });
  window.addEventListener("appinstalled", function () { deferred = null; standalone = true; setButtons(); });

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-install]");
    if (!button) return;
    event.preventDefault();
    if (deferred) { deferred.prompt(); deferred.userChoice.finally(function () { deferred = null; setButtons(); }); }
    else if (isIos) { var note = document.querySelector("[data-install-ios]"); if (note) { note.hidden = false; note.scrollIntoView({ behavior: "smooth", block: "center" }); } }
  });

  // The Share button on /share uses the phone's own share sheet when there is one.
  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-native-share]");
    if (!button) return;
    var data = { title: "Kalaburagi Grievance Tracker", text: "Try the Kalaburagi Grievance Tracker:", url: location.origin + "/" };
    if (navigator.share) navigator.share(data).catch(function () {});
  });
  if (!navigator.share) document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-native-share]").forEach(function (b) { b.hidden = true; });
  });

  document.addEventListener("DOMContentLoaded", setButtons);
})();
