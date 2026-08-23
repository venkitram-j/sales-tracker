from django import forms
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField

from .models import User


class UserCreationForm(forms.ModelForm):
	password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
	password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

	class Meta:
		model = User
		fields = ('email', 'full_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')

	def clean_password2(self):
		password1 = self.cleaned_data.get('password1')
		password2 = self.cleaned_data.get('password2')
		if password1 and password1 != password2:
			raise forms.ValidationError('The two password fields did not match.')
		return password2

	def save(self, commit=True):
		user = super().save(commit=False)
		user.set_password(self.cleaned_data['password1'])
		if commit:
			user.save()
			self.save_m2m()
		return user


class UserChangeForm(forms.ModelForm):
	password = ReadOnlyPasswordHashField(label='Password')

	class Meta:
		model = User
		fields = ('email', 'full_name', 'password', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')


class LoginForm(AuthenticationForm):
	username = forms.EmailField(
		label='Email',
		widget=forms.EmailInput(attrs={
			'class': 'form-control',
			'placeholder': 'Email address',
			'autocomplete': 'email',
		}),
	)
	password = forms.CharField(
		label='Password',
		strip=False,
		widget=forms.PasswordInput(attrs={
			'class': 'form-control',
			'placeholder': 'Password',
			'autocomplete': 'current-password',
		}),
	)
