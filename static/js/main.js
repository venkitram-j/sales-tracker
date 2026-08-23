document.addEventListener("DOMContentLoaded", function () {

    // ---- Sidebar toggle (mobile) ------------------------------------
    var sidebarToggle = document.getElementById("sidebarToggle");
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            document.getElementById("appSidebar").classList.toggle("show");
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

    // ---- Auto-dismiss alerts after a few seconds ---------------------
    document.querySelectorAll(".alert").forEach(function (alertEl) {
        setTimeout(function () {
            var alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (alert) alert.close();
        }, 6000);
    });
});
