from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list"),
    path("add/", views.ProductCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.ProductUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ProductDeleteView.as_view(), name="delete"),
    path("upload/", views.ProductExcelUploadView.as_view(), name="upload"),
]
