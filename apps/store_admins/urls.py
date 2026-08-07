from django.urls import path

from . import views

app_name = "store_admins"

urlpatterns = [
    path("", views.StoreAdminListView.as_view(), name="list"),
    path("add/", views.StoreAdminCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.StoreAdminUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.StoreAdminDeleteView.as_view(), name="delete"),
    path("upload/", views.StoreAdminExcelUploadView.as_view(), name="upload"),
]
