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

  // The install bar on the first screen: shown to anyone who has not installed the app, until they close it.
  function barSetup() {
    var bar = document.querySelector("[data-install-bar]");
    if (!bar) return;
    var closed = false;
    try { closed = sessionStorage.getItem("kgt_install_closed") === "1"; } catch (e) { closed = false; }
    bar.hidden = standalone || closed;
    var hint = document.getElementById("installHint");
    var go = bar.querySelector("[data-install-now]");
    if (go) go.addEventListener("click", function () {
      if (deferred) { deferred.prompt(); deferred.userChoice.finally(function () { deferred = null; }); return; }
      if (hint) {
        hint.hidden = false;
        hint.textContent = isIos ? "On iPhone: tap the Share icon in Safari, then Add to Home Screen."
          : "In Chrome: tap the menu (three dots), then Install app or Add to Home screen.";
      }
    });
    var close = bar.querySelector("[data-install-close]");
    if (close) close.addEventListener("click", function () {
      bar.hidden = true;
      try { sessionStorage.setItem("kgt_install_closed", "1"); } catch (e) { /* shown again next visit */ }
    });
    window.addEventListener("appinstalled", function () { bar.hidden = true; });
  }

  document.addEventListener("DOMContentLoaded", function () { setButtons(); barSetup(); });
})();
