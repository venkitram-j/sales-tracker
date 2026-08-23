document.addEventListener('DOMContentLoaded', function () {
	const form = document.querySelector('.login-form form');
	if (!form) {
		return;
	}

	form.addEventListener('submit', function () {
		const button = form.querySelector('[data-login-submit]');
		if (!button) {
			return;
		}

		button.disabled = true;
		button.querySelector('[data-login-label]').textContent = 'Signing in...';
		button.querySelector('[data-login-spinner]').classList.remove('d-none');
		button.querySelector('[data-login-status]').textContent = 'Signing in...';
	});
});
