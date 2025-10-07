from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

# Simple fallback/test view — used only to confirm deployment
def _fallback_home(request):
    return HttpResponse("Django is running — fallback home", status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('cart/', include('cart.urls')),

    # fallback root (will be used only if store.urls doesn't provide '')
    path('', _fallback_home),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
