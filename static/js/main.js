document.addEventListener("DOMContentLoaded", function () {
    // ---- Delete confirmation modal ----------------------------------
    var deleteModalEl = document.getElementById("deleteModal");
    if (deleteModalEl) {
        var deleteModal = new bootstrap.Modal(deleteModalEl);
        var deleteForm = document.getElementById("deleteForm");
        var itemNameEl = document.getElementById("deleteModalItemName");

        document.querySelectorAll("[data-delete-url]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                deleteForm.setAttribute("action", btn.getAttribute("data-delete-url"));
                itemNameEl.textContent = btn.getAttribute("data-item-name") || "this record";
                deleteModal.show();
            });
        });
    }

    // ---- Sidebar toggle (mobile) ------------------------------------
    var sidebarToggle = document.getElementById("sidebarToggle");
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            document.getElementById("appSidebar").classList.toggle("show");
        });
    }

    // ---- Disable submit buttons on form submission to prevent double clicks ----
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (form.dataset.noDisable === "true") return;
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

    // ---- Auto-dismiss alerts after a few seconds ---------------------
    document.querySelectorAll(".alert").forEach(function (alertEl) {
        setTimeout(function () {
            var alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (alert) alert.close();
        }, 6000);
    });
});
