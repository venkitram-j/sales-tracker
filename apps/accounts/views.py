from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.urls import reverse_lazy

from .forms import LoginForm


class LoginView(DjangoLoginView):
	form_class = LoginForm
	template_name = "registration/login.html"


class LogoutView(DjangoLogoutView):
	next_page = reverse_lazy("accounts:login")
