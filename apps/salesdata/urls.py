from django.urls import path

from . import views

app_name = "salesdata"

urlpatterns = [
    path("", views.SalesDataListView.as_view(), name="list"),
    path("branch-wise/", views.SalesDataBranchWiseView.as_view(), name="branch_wise"),
    path("add/", views.SalesDataCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.SalesDataUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.SalesDataDeleteView.as_view(), name="delete"),
    path("upload/", views.SalesDataExcelUploadView.as_view(), name="upload"),
]
