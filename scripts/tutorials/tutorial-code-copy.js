/* Idempotent fallback copy controls for legacy RStudio/Pandoc code blocks. */
(function () {
  "use strict";

  function addLegacyControls() {
    var root = document.getElementById("quarto-document-content") || document.querySelector("main.content") || document.body;
    root.querySelectorAll("pre.r, pre.bash, pre.sourceCode").forEach(function (pre) {
      if (!pre.querySelector("code")) return;

      var quartoScaffold = pre.closest(".code-copy-outer-scaffold");
      if (quartoScaffold && quartoScaffold.querySelector(".code-copy-button")) return;
      if (pre.closest(".qbio-copy-wrap")) return;
      if (pre.querySelector(".code-copy-button, .qbio-copy-button")) return;
      if (pre.parentElement && pre.parentElement.querySelector(".code-copy-button, .qbio-copy-button")) return;

      var wrapper = document.createElement("div");
      wrapper.className = "qbio-copy-wrap";
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);

      var button = document.createElement("button");
      button.type = "button";
      button.className = "qbio-copy-button";
      button.title = "Copy code";
      button.setAttribute("aria-label", "Copy code");
      button.textContent = "Copy";
      wrapper.appendChild(button);

      button.addEventListener("click", function () {
        var value = pre.querySelector("code").textContent;
        function report(ok) {
          button.textContent = ok ? "Copied" : "Copy failed";
          window.setTimeout(function () { button.textContent = "Copy"; }, 1400);
        }
        function fallback() {
          var temporary = document.createElement("textarea");
          temporary.value = value;
          temporary.style.position = "fixed";
          temporary.style.opacity = "0";
          document.body.appendChild(temporary);
          temporary.select();
          var copied = false;
          try { copied = document.execCommand("copy"); } catch (error) { copied = false; }
          temporary.remove();
          report(copied);
        }
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(value).then(function () { report(true); }, fallback);
        } else {
          fallback();
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addLegacyControls, { once: true });
  } else {
    addLegacyControls();
  }
})();
