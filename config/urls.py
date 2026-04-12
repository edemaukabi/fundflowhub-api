from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "name": "FundFlowHub API",
        "version": "v1",
        "status": "operational",
        "docs": request.build_absolute_uri("/api/v1/schema/swagger-ui/"),
        "redoc": request.build_absolute_uri("/api/v1/schema/redoc/"),
    })


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", api_root, name="api-root"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/auth/", include("djoser.urls")),
    path("api/v1/auth/", include("core_apps.user_auth.urls")),
    path("api/v1/profiles/", include("core_apps.user_profile.urls")),
    path("api/v1/accounts/", include("core_apps.accounts.urls")),
    path("api/v1/cards/", include("core_apps.cards.urls")),
]

admin.site.site_header = "FundFlowHub Admin"
admin.site.site_title = "FundFlowHub Admin Portal"
admin.site.index_title = "Welcome to FundFlowHub Admin Portal"
