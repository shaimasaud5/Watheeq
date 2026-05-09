from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('', include('frontend.urls')),
    path("api/", include("project.urls")),
    path("api/", include("preprocessing.urls")),
    path('api/', include('extract.urls')),
    path('api/generation/', include('generation.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)