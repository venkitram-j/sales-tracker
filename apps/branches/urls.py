from django.urls import path

from . import views

app_name = "branches"

urlpatterns = [
    path("", views.BranchListView.as_view(), name="list"),
    path("add/", views.BranchCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.BranchUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.BranchDeleteView.as_view(), name="delete"),
    path("upload/", views.BranchExcelUploadView.as_view(), name="upload"),
]
