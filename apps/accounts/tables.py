from django.utils.html import format_html
import django_tables2 as tables

from .models import User


class UserTable(tables.Table):
	email = tables.Column(verbose_name='Email')
	full_name = tables.Column(verbose_name='Name')
	is_staff = tables.BooleanColumn(verbose_name='Staff')
	date_joined = tables.DateColumn(format='M j, Y', verbose_name='Joined')
	actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

	class Meta:
		model = User
		fields = ('full_name', 'email', 'is_staff', 'is_active', 'date_joined', 'actions')
		attrs = {'class': 'table dashboard-users-table mb-0'}

	def __init__(self, *args, can_edit=False, **kwargs):
		super().__init__(*args, **kwargs)
		self.can_edit = can_edit

	def render_actions(self, record):
		if not self.can_edit:
			return ''
		return format_html(
			'<button type="button" class="btn btn-sm btn-outline-secondary" '
			'data-bs-toggle="modal" data-bs-target="#edit-user-modal" '
			'data-user-id="{}" data-user-email="{}" data-user-full-name="{}" '
			'data-user-is-staff="{}" aria-label="Edit {}" title="Edit user">'
			'<i class="bi bi-pencil-square" aria-hidden="true"></i></button>',
			record.pk, record.email, record.full_name, str(record.is_staff).lower(), record.full_name or record.email,
		)