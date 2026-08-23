from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	form = UserChangeForm
	add_form = UserCreationForm
	ordering = ('email',)
	list_display = ('email', 'full_name', 'is_staff', 'is_active', 'date_joined')
	list_filter = ('is_staff', 'is_superuser', 'is_active')
	search_fields = ('email', 'full_name')
	readonly_fields = ('last_login', 'date_joined')

	fieldsets = (
		(None, {'fields': ('email', 'full_name', 'password')}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Important dates', {'fields': ('last_login', 'date_joined')}),
	)
	add_fieldsets = (
		(
			None,
			{'classes': ('wide',), 'fields': ('email', 'full_name', 'password1', 'password2')},
		),
		(
			'Permissions',
			{'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')},
		),
	)
