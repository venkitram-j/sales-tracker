from django.apps import AppConfig


class SalesDataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales_data"
    label = "sales_data"
    verbose_name = "Sales Data"
