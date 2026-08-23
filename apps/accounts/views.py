from django.contrib.auth.views import LoginView, LogoutView

from .forms import LoginForm


class UserLoginView(LoginView):
	form_class = LoginForm
	template_name = 'registration/login.html'
	redirect_authenticated_user = True


class UserLogoutView(LogoutView):
	pass
