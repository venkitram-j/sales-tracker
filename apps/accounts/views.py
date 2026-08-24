from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.views.generic import View
from django_tables2.views import SingleTableView

from .forms import LoginForm, UserModalChangeForm
from .models import User
from .tables import UserTable


class UserLoginView(LoginView):
	form_class = LoginForm
	template_name = 'registration/login.html'
	redirect_authenticated_user = True


class UserLogoutView(LogoutView):
	pass


class UserListView(LoginRequiredMixin, SingleTableView):
	table_class = UserTable
	template_name = 'accounts/users_list.html'
	context_object_name = 'users'

	def get_queryset(self):
		users = User.objects.exclude(pk=self.request.user.pk).order_by('full_name', 'email')
		if self.request.user.is_superuser:
			return users
		if self.request.user.is_staff:
			return users.filter(is_superuser=False)
		return users

	def get_table_kwargs(self):
		return {'can_edit': self.request.user.is_superuser or self.request.user.is_staff}


class UserUpdateView(LoginRequiredMixin, View):
	model = User

	def get_queryset(self):
		users = User.objects.exclude(pk=self.request.user.pk)
		if self.request.user.is_superuser:
			return users
		if self.request.user.is_staff:
			return users.filter(is_superuser=False)
		return users.none()

	def post(self, request, user_id):
		user = self.get_queryset().filter(pk=user_id).first()
		if user is None:
			return JsonResponse({'error': 'You do not have permission to edit this user.'}, status=403)

		form = UserModalChangeForm(request.POST, instance=user)
		if not form.is_valid():
			return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

		form.save()
		return JsonResponse({'success': True})
