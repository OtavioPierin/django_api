#permite que o django encontre as urls do app
#serão importadas no arquivo urls.py do projeto, para que o django saiba onde encontrar as urls do app

# djangoapp/urls.py

from django.urls import path, include
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework_nested import routers as nested_routers

from .views import (
    LoginView, RegistroView, RefreshView, LogoutView,
    CategoriaViewSet, ProdutoViewSet, ProdutoImagemViewSet,
    PagamentoViewSet, ClienteViewSet, EnderecoViewSet,
    PedidoViewSet, ItensPedidoViewSet, AvaliacaoViewSet,
    ProdutoAvaliacaoViewSet, AvaliacaoCategoriaViewSet,
)

# =============================================================================
# Router principal
# =============================================================================
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'categorias',           CategoriaViewSet,         basename='categoria')
router.register(r'produtos',             ProdutoViewSet,           basename='produto')
router.register(r'pagamentos',           PagamentoViewSet,         basename='pagamento')
router.register(r'clientes',             ClienteViewSet,           basename='cliente')
router.register(r'pedidos',              PedidoViewSet,            basename='pedido')
router.register(r'avaliacoes',           AvaliacaoViewSet,         basename='avaliacao')
router.register(r'produto-avaliacoes',   ProdutoAvaliacaoViewSet,  basename='produto-avaliacao')
router.register(r'avaliacao-categorias', AvaliacaoCategoriaViewSet,basename='avaliacao-categoria')

# =============================================================================
# Routers aninhados
# =============================================================================

# /produtos/{produto_pk}/imagens/
produtos_router = nested_routers.NestedDefaultRouter(router, r'produtos', lookup='produto')
produtos_router.register(r'imagens', ProdutoImagemViewSet, basename='produto-imagens')

# /clientes/{cliente_pk}/enderecos/
clientes_router = nested_routers.NestedDefaultRouter(router, r'clientes', lookup='cliente')
clientes_router.register(r'enderecos', EnderecoViewSet, basename='cliente-enderecos')

# /pedidos/{pedido_pk}/itens/
pedidos_router = nested_routers.NestedDefaultRouter(router, r'pedidos', lookup='pedido')
pedidos_router.register(r'itens', ItensPedidoViewSet, basename='pedido-itens')

# =============================================================================
# URL patterns
# =============================================================================
urlpatterns = [
    path('auth/registro/', RegistroView.as_view(),   name='auth-registro'),
    path('auth/login/',    LoginView.as_view(),      name='auth-login'),
    path('auth/refresh/',  RefreshView.as_view(),    name='auth-refresh'),
    path('auth/logout/',   LogoutView.as_view(),     name='auth-logout'),
    path('auth/verify/',   TokenVerifyView.as_view(),name='auth-verify'),

    path('', include(router.urls)),
    path('', include(produtos_router.urls)),
    path('', include(clientes_router.urls)),
    path('', include(pedidos_router.urls)),
]