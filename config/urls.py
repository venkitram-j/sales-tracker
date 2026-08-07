from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("departments/", include("apps.departments.urls", namespace="departments")),
    path("products/", include("apps.products.urls", namespace="products")),
    path("branches/", include("apps.branches.urls", namespace="branches")),
    path("store-admins/", include("apps.store_admins.urls", namespace="store_admins")),
    path("buyers/", include("apps.buyers.urls", namespace="buyers")),
    path("sales-data/", include("apps.salesdata.urls", namespace="salesdata")),
    path("", include("apps.dashboard.urls", namespace="dashboard")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Sales Tracker Administration"
admin.site.site_title = "Sales Tracker Admin"
admin.site.index_title = "Application Data Management"
