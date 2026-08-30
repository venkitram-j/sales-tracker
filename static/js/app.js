(function () {
  "use strict";
  function loading(btn, on) {
    if (!btn) return;
    if (on) {
      if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
      btn.disabled = true;
      btn.setAttribute("aria-disabled", "true");
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>' +
        (btn.dataset.loadingText || "Processing...");
    } else {
      btn.disabled = false;
      btn.removeAttribute("aria-disabled");
      if (btn.dataset.originalHtml) {
        btn.innerHTML = btn.dataset.originalHtml;
        delete btn.dataset.originalHtml;
      }
    }
  }
  function initForms() {
    document.querySelectorAll("form[data-loading-form]").forEach((f) =>
      f.addEventListener("submit", (e) => {
        if (!f.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          f.classList.add("was-validated");
          return;
        }
        f.classList.add("was-validated");
        loading(e.submitter || f.querySelector('[type="submit"]'), true);
      }),
    );
  }
  function initPasswords() {
    document.querySelectorAll("[data-password-toggle]").forEach((b) =>
      b.addEventListener("click", () => {
        let t = document.querySelector(b.dataset.passwordTarget),
          i = b.querySelector("i");
        if (!t) return;
        let show = t.type === "password";
        t.type = show ? "text" : "password";
        if (i) {
          i.classList.toggle("bi-eye", !show);
          i.classList.toggle("bi-eye-slash", show);
        }
        b.setAttribute("aria-label", show ? "Hide password" : "Show password");
      }),
    );
  }
  function apiWithLoading(request, message) {
    let o = document.createElement("div");
    o.className =
      "position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-25 d-flex align-items-center justify-content-center";
    o.style.zIndex = "1090";
    o.setAttribute("role", "status");
    o.innerHTML =
      '<div class="bg-body rounded-4 shadow p-4 text-center"><div class="spinner-border text-primary mb-3" aria-hidden="true"></div><div class="fw-semibold">' +
      (message || "Loading...") +
      "</div></div>";
    document.body.appendChild(o);
    return Promise.resolve(request).finally(() => o.remove());
  }
  window.SalesTracker = {
    setButtonLoading: loading,
    apiWithLoading: apiWithLoading,
  };
  document.addEventListener("DOMContentLoaded", () => {
    initForms();
    initPasswords();
    document
      .querySelectorAll("[data-current-year]")
      .forEach((e) => (e.textContent = new Date().getFullYear()));
  });
})();
