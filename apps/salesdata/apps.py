from django.apps import AppConfig


class SalesDataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.salesdata"
    label = "salesdata"
    verbose_name = "Sales Data"
