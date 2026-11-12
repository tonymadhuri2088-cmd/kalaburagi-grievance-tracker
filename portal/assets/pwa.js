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
  var isAndroid = /android/i.test(ua);
  var isMobile = isIos || isAndroid || /mobile/i.test(ua);
  // Many phones open links inside another app (WhatsApp, Instagram, a QR scanner). Those cannot install apps.
  var inApp = /FBAN|FBAV|Instagram|WhatsApp|Snapchat|Telegram|MicroMessenger|Line\/|GSA\/|; wv\)|\bwv\b/i.test(ua);

  // The exact steps for this phone, so nobody has to guess.
  function helpText() {
    if (inApp) return "This page is open inside another app, which cannot install it. Tap the menu (three dots) and choose Open in Chrome (or Open in browser). Then tap the menu again and choose Install app.";
    if (isIos) return "On iPhone, use Safari: tap the Share icon, then Add to Home Screen, then Add.";
    if (/SamsungBrowser/i.test(ua)) return "In Samsung Internet: tap the menu (three lines), then Add page to, then Home screen.";
    if (/Firefox/i.test(ua)) return "In Firefox: tap the menu (three dots), then Install.";
    if (/EdgA/i.test(ua)) return "In Edge: tap the menu (three dots), then Add to phone.";
    if (isAndroid) return "In Chrome: tap the menu (three dots at the top right), then Install app (or Add to Home screen). If you do not see it, open this link in Chrome, not inside another app.";
    return "In Chrome or Edge: click the install icon at the right of the address bar, or open the menu and choose Install.";
  }
  function showHelp() {
    var shown = false;
    document.querySelectorAll("[data-install-help]").forEach(function (note) { note.hidden = false; note.textContent = helpText(); shown = true; });
    return shown;
  }

  function setButtons() {
    var buttons = document.querySelectorAll("[data-install]");
    buttons.forEach(function (button) {
      if (standalone) { button.hidden = true; return; }
      button.hidden = !(deferred || isMobile);
    });
    document.querySelectorAll("[data-install-ios]").forEach(function (note) { note.hidden = standalone || !isIos; });
    document.querySelectorAll("[data-installed]").forEach(function (note) { note.hidden = !standalone; });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault(); deferred = event; setButtons();
    var h = document.getElementById("installHint"); if (h) h.hidden = true;
  });
  window.addEventListener("appinstalled", function () { deferred = null; standalone = true; setButtons(); });

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-install]");
    if (!button) return;
    event.preventDefault();
    if (deferred) { deferred.prompt(); deferred.userChoice.finally(function () { deferred = null; setButtons(); }); }
    else {
      if (!showHelp() && isIos) { var note = document.querySelector("[data-install-ios]"); if (note) note.hidden = false; }
    }
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
    var hint0 = document.getElementById("installHint");
    // On a phone where the browser has not offered the install prompt, show the steps straight away.
    if (hint0 && isMobile && !standalone) { hint0.hidden = false; hint0.textContent = helpText(); }
    var hint = document.getElementById("installHint");
    var go = bar.querySelector("[data-install-now]");
    if (go) go.addEventListener("click", function () {
      if (deferred) { deferred.prompt(); deferred.userChoice.finally(function () { deferred = null; }); return; }
      if (hint) { hint.hidden = false; hint.textContent = helpText(); }
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
