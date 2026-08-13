document.addEventListener("DOMContentLoaded", function () {
    // ---- Delete confirmation modal -----------------------------------
    // Uses event delegation (not per-button listeners) so it keeps working
    // for delete buttons rendered later by an HTMX swap (e.g. live search
    // results), with no re-initialization needed.
    var deleteModalEl = document.getElementById("deleteModal");
    if (deleteModalEl) {
        var deleteModal = new bootstrap.Modal(deleteModalEl);
        var deleteForm = document.getElementById("deleteForm");
        var itemNameEl = document.getElementById("deleteModalItemName");

        document.addEventListener("click", function (e) {
            var btn = e.target.closest("[data-delete-url]");
            if (!btn) return;
            deleteForm.setAttribute("action", btn.getAttribute("data-delete-url"));
            itemNameEl.textContent = btn.getAttribute("data-item-name") || "this record";
            deleteModal.show();
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
    // Delegated on document so it also covers forms added after page load.
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

// ---- Re-enable any HTMX-triggered search-form submit affordance -------
// HTMX search requests don't go through the browser's native "submit"
// event in every trigger path (e.g. keyup-triggered fetches), so there's
// nothing to re-enable there. This listener only guards against a rare
// edge case: if an htmx request errors out, restore any disabled buttons
// inside the element that issued it so the UI doesn't get stuck.
document.body.addEventListener("htmx:responseError", function (e) {
    var form = e.target.closest ? e.target.closest("form") : null;
    if (!form) return;
    form.querySelectorAll('button[disabled]').forEach(function (btn) {
        if (btn.dataset.originalHtml) {
            btn.innerHTML = btn.dataset.originalHtml;
        }
        btn.disabled = false;
    });
});
