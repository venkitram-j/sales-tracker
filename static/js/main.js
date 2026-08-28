document.addEventListener("DOMContentLoaded", function () {
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