# djangoproject/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
import os


def serve_media_com_header(request, path):
    """
    Serve arquivos de mídia adicionando o header ngrok-skip-browser-warning.
    Necessário porque o ngrok bloqueia requisições diretas do navegador
    que não possuem esse header, retornando 404 HTML no lugar do arquivo.
    """
    from django.views.static import serve
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response['ngrok-skip-browser-warning'] = '1'
    return response


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',   include('djangoapp.urls')),
    # Rota de mídia customizada — adiciona o header do ngrok
    path('media/<path:path>', serve_media_com_header),
]