from django.urls import path

from . import views

app_name = "buyers"

urlpatterns = [
    path("", views.BuyerListView.as_view(), name="list"),
    path("add/", views.BuyerCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.BuyerUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.BuyerDeleteView.as_view(), name="delete"),
    path("upload/", views.BuyerExcelUploadView.as_view(), name="upload"),
]
