// Shared by the concept demos: follow the course site's light/dark toggle when embedded,
// and grow the iframe to fit the demo so phones never scroll inside it.
(function () {
  try {
    const body = window.parent !== window && window.parent.document.body;
    if (body) {
      const sync = () => document.documentElement.dataset.theme =
        body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "light";
      sync();
      new MutationObserver(sync).observe(body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
    }
  } catch (e) { /* opened on its own, or cross-origin: keep the OS setting */ }
  window.fitFrame = function () {
    try { if (window.frameElement) window.frameElement.style.height = (document.documentElement.scrollHeight + 4) + "px"; } catch (e) {}
  };
  window.addEventListener("resize", () => window.fitFrame());
  window.addEventListener("load", () => window.fitFrame());
})();
