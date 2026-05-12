# djangoproject/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static   # ← serve arquivos de mídia em dev

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',   include('djangoapp.urls')),
]

# Em desenvolvimento, o Django serve os arquivos de mídia diretamente.
# Em produção o Nginx assume essa responsabilidade (ver nginx.conf).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)