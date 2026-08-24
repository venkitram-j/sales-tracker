from django.urls import path

from .views import UserListView, UserLoginView, UserLogoutView, UserUpdateView


app_name = 'accounts'

urlpatterns = [
	path('login/', UserLoginView.as_view(), name='login'),
	path('logout/', UserLogoutView.as_view(), name='logout'),
	path('users/', UserListView.as_view(), name='users'),
	path('users/<int:user_id>/edit/', UserUpdateView.as_view(), name='user_edit'),
]
