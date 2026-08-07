from django.conf import settings


def app_meta(request):
    """Expose application-wide constants to every template."""
    return {"APP_NAME": settings.APP_NAME}
