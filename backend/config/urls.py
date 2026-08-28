from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.bids.urls")),
    path("api/v1/", include("apps.sync.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.settings_admin.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Only mounted in DEBUG — disabled entirely in production (§security: admin at
# a configurable, non-default path, and off outside DEBUG where it's not needed).
if settings.DEBUG:
    urlpatterns.append(path(settings.DJANGO_ADMIN_URL, admin.site.urls))
