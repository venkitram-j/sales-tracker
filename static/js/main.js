
document.addEventListener("DOMContentLoaded", () => {
  const sidebar=document.querySelector(".sidebar");
  const toggle=document.querySelector("[data-sidebar-toggle]");
  if(toggle) toggle.addEventListener("click",()=>sidebar?.classList.toggle("show"));

  /* Desktop sidebar collapse/expand */
  const desktopToggle=document.querySelector("[data-sidebar-desktop-toggle]");
  if(desktopToggle){
    const body=document.body, icon=desktopToggle.querySelector("i"), key="salesTracker.sidebarCollapsed";
    const apply=collapsed=>{
      body.classList.toggle("sidebar-collapsed",collapsed);
      if(icon) icon.className=collapsed?"bi bi-layout-sidebar-inset-reverse":"bi bi-layout-sidebar-inset";
      desktopToggle.setAttribute("aria-label",collapsed?"Expand sidebar":"Collapse sidebar");
      desktopToggle.setAttribute("title",collapsed?"Expand sidebar":"Collapse sidebar");
    };
    let collapsed=false;
    try{collapsed=localStorage.getItem(key)==="true"}catch(e){}
    apply(collapsed);
    desktopToggle.addEventListener("click",()=>{
      collapsed=!body.classList.contains("sidebar-collapsed");
      apply(collapsed);
      try{localStorage.setItem(key,String(collapsed))}catch(e){}
    });
  }

  // ---- Disable submit buttons on form submission to prevent double clicks ----
  document.addEventListener("submit", function (e) {
      var form = e.target;
      if (!(form instanceof HTMLFormElement) || form.dataset.noDisable === "true") return;
      var submitBtns = form.querySelectorAll('button[type="submit"]');
      submitBtns.forEach(function (btn) {
          if (btn.disabled) return;
          var loadingText = btn.getAttribute("data-loading-text");
          btn.dataset.originalHtml = btn.innerHTML;
          if (loadingText) {
              btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' + loadingText;
          }
          btn.disabled = true;
      });
  });

});

// ---- Global loading overlay ------------------------------------------
// Disables the whole screen while any backend-hitting action is in
// flight: plain form submits (add/edit/upload/delete/etc.) and HTMX
// requests (live search, column sorting, pagination, filters).
(function () {
    var overlay = document.getElementById("data-loading-overlay");
    if (!overlay) return;

    function showNow() {
        overlay.classList.add("show");
        overlay.setAttribute("aria-hidden", "false");
    }

    // Plain (non-HTMX) form submissions - the browser is about to navigate
    // away, so show immediately rather than waiting out the anti-flicker
    // delay used for HTMX requests below.
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.hasAttribute("hx-get") || form.hasAttribute("hx-post")) return; // handled by the htmx events instead
        showNow();
    });
})();
