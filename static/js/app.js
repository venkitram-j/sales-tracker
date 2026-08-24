document.addEventListener('DOMContentLoaded', function () {
	const editModal = document.querySelector('#edit-user-modal');
	const editForm = document.querySelector('#edit-user-form');
	if (editModal && editForm) {
		let userId;
		const emailInput = editForm.querySelector('[name="email"]');
		const fullNameInput = editForm.querySelector('[name="full_name"]');
		const staffInput = editForm.querySelector('[name="is_staff"]');
		const errorBox = editForm.querySelector('[data-edit-error]');

		document.querySelectorAll('[data-user-id]').forEach(function (button) {
			button.addEventListener('click', function () {
				userId = button.dataset.userId;
				emailInput.value = button.dataset.userEmail;
				fullNameInput.value = button.dataset.userFullName;
				staffInput.checked = button.dataset.userIsStaff === 'true';
				clearEditErrors();
			});
		});

		editForm.addEventListener('submit', async function (event) {
			event.preventDefault();
			clearEditErrors();
			setEditBusy(true);
			const data = new FormData(editForm);
			try {
				const response = await fetch(editForm.dataset.editUrlTemplate.replace('/0/', `/${userId}/`), {
					method: 'POST',
					headers: {'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest'},
					body: data,
				});
				const result = await response.json();
				if (!response.ok) {
					showEditErrors(result);
					return;
				}
				window.location.reload();
			} catch (error) {
				errorBox.textContent = 'The update could not be completed. Please try again.';
				errorBox.classList.remove('d-none');
			} finally {
				setEditBusy(false);
			}
		});

		function clearEditErrors() {
			errorBox.classList.add('d-none');
			errorBox.textContent = '';
			editForm.querySelectorAll('.is-invalid').forEach(function (input) { input.classList.remove('is-invalid'); });
			editForm.querySelectorAll('[data-error-for]').forEach(function (error) { error.textContent = ''; });
		}

		function showEditErrors(result) {
			if (result.errors) {
				Object.entries(result.errors).forEach(function ([field, messages]) {
					const input = editForm.querySelector(`[name="${field}"]`);
					const error = editForm.querySelector(`[data-error-for="${field}"]`);
					if (input) input.classList.add('is-invalid');
					if (error) error.textContent = messages.map(function (message) { return message.message; }).join(' ');
				});
			} else {
				errorBox.textContent = result.error || 'Please correct the errors and try again.';
				errorBox.classList.remove('d-none');
			}
		}

		function setEditBusy(busy) {
			editForm.querySelector('[data-edit-submit]').disabled = busy;
			editForm.querySelectorAll('input, button').forEach(function (control) { control.disabled = busy; });
			if (busy) {
				const overlay = document.createElement('div');
				overlay.className = 'edit-request-overlay';
				overlay.setAttribute('aria-label', 'Saving changes');
				document.body.appendChild(overlay);
			} else {
				const overlay = document.querySelector('.edit-request-overlay');
				if (overlay) overlay.remove();
			}
		}

		function getCookie(name) {
			return document.cookie.split('; ').find(function (row) { return row.startsWith(`${name}=`); })?.split('=')[1] || '';
		}
	}

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
