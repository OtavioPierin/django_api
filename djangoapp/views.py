# djangoapp/views.py

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404

from .models import (
    Categoria, Produto, Pagamento, Cliente,
    Endereco, Pedido, ItensPedido, Avaliacao,
    ProdutoAvaliacao, AvaliacaoCategoria,
)
from .serializers import (
    RegistroSerializer, MeuTokenSerializer,
    CategoriaSerializer, ProdutoSerializer,
    PagamentoSerializer, ClienteSerializer,
    EnderecoSerializer, PedidoSerializer,
    PedidoCreateSerializer, ItensPedidoSerializer,
    AvaliacaoSerializer, ProdutoAvaliacaoSerializer,
    AvaliacaoCategoriaSerializer,
)


# AUTH
class LoginView(TokenObtainPairView):
    """
    POST /auth/login/
    Body: { "username": "...", "password": "..." }
    Retorna: { "access": "...", "refresh": "..." }
    """
    permission_classes = [AllowAny]
    serializer_class   = MeuTokenSerializer


class RegistroView(APIView):
    """
    POST /auth/registro/
    Body: { "username", "email", "password", "nome", "cpf" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"mensagem": "Usuário criado com sucesso."},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshView(APIView):
    """
    POST /auth/refresh/
    Body: { "refresh": "..." }
    Retorna: { "access": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"erro": "Refresh token obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token)})
        except Exception:
            return Response(
                {"erro": "Token inválido ou expirado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    POST /auth/logout/
    Body: { "refresh": "..." }
    Invalida o refresh token no blacklist.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"erro": "Refresh token obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
            return Response({"mensagem": "Logout realizado com sucesso."})
        except Exception:
            return Response(
                {"erro": "Token inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

# CATEGORIA
class CategoriaViewSet(viewsets.ModelViewSet):
    """
    GET    /categorias/           → lista todas
    POST   /categorias/           → cria (admin)
    GET    /categorias/{id}/      → detalhe
    PUT    /categorias/{id}/      → atualiza (admin)
    DELETE /categorias/{id}/      → remove (admin)
    GET    /categorias/{id}/produtos/ → produtos da categoria
    """
    queryset         = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['nome']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='produtos')
    def produtos(self, request, pk=None):
        """GET /categorias/{id}/produtos/"""
        categoria = self.get_object()
        produtos  = categoria.produtos.all()
        serializer = ProdutoSerializer(produtos, many=True)
        return Response(serializer.data)


# PRODUTO

class ProdutoViewSet(viewsets.ModelViewSet):
    """
    GET    /produtos/                     → lista todos
    POST   /produtos/                     → cria (admin)
    GET    /produtos/{id}/                → detalhe
    PUT    /produtos/{id}/                → atualiza (admin)
    DELETE /produtos/{id}/                → remove (admin)
    GET    /produtos/{id}/avaliacoes/     → avaliações do produto
    POST   /produtos/{id}/reduzir-estoque/→ reduz estoque manualmente (admin)
    """
    queryset         = Produto.objects.select_related('categoria').all()
    serializer_class = ProdutoSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['nome_produto', 'categoria__nome']
    ordering_fields  = ['preco', 'estoque', 'nome_produto']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'reduzir_estoque']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='avaliacoes')
    def avaliacoes(self, request, pk=None):
        """GET /produtos/{id}/avaliacoes/"""
        produto    = self.get_object()
        avaliacoes = produto.avaliacoes.select_related('cliente').all()
        serializer = AvaliacaoSerializer(avaliacoes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reduzir-estoque')
    def reduzir_estoque(self, request, pk=None):
        """
        POST /produtos/{id}/reduzir-estoque/
        Body: { "quantidade": 5 }
        """
        produto    = self.get_object()
        quantidade = request.data.get('quantidade')
        if not quantidade or int(quantidade) <= 0:
            return Response(
                {"erro": "Informe uma quantidade válida (> 0)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            produto.reduzir_estoque(int(quantidade))
            return Response({"mensagem": f"Estoque atualizado. Novo estoque: {produto.estoque}."})
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# PAGAMENTO

class PagamentoViewSet(viewsets.ModelViewSet):
    """
    GET    /pagamentos/       → lista todos (admin)
    POST   /pagamentos/       → cria
    GET    /pagamentos/{id}/  → detalhe
    PUT    /pagamentos/{id}/  → atualiza (admin)
    DELETE /pagamentos/{id}/  → remove (admin)
    """
    queryset         = Pagamento.objects.all()
    serializer_class = PagamentoSerializer

    def get_permissions(self):
        if self.action in ['list', 'destroy', 'update', 'partial_update']:
            return [IsAdminUser()]
        return [IsAuthenticated()]


# CLIENTE

class ClienteViewSet(viewsets.ModelViewSet):
    """
    GET    /clientes/                        → lista (admin)
    GET    /clientes/{id}/                   → detalhe (dono ou admin)
    PUT    /clientes/{id}/                   → atualiza (dono ou admin)
    DELETE /clientes/{id}/                   → remove (admin)
    GET    /clientes/{id}/pedidos/           → pedidos do cliente
    GET    /clientes/{id}/enderecos/         → endereços do cliente
    GET    /clientes/{id}/avaliacoes/        → avaliações feitas pelo cliente
    GET    /clientes/me/                     → perfil do cliente autenticado
    """
    queryset         = Cliente.objects.prefetch_related('enderecos').all()
    serializer_class = ClienteSerializer

    def get_permissions(self):
        if self.action in ['list', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_object(self):
        """Garante que o cliente só acessa seus próprios dados (exceto admin)."""
        obj = super().get_object()
        user = self.request.user
        if not user.is_staff and obj.user != user:
            self.permission_denied(self.request)
        return obj

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """GET /clientes/me/ — retorna o perfil do usuário autenticado."""
        cliente    = get_object_or_404(Cliente, user=request.user)
        serializer = self.get_serializer(cliente)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='pedidos')
    def pedidos(self, request, pk=None):
        """GET /clientes/{id}/pedidos/?status=pendente"""
        cliente   = self.get_object()
        status_filtro = request.query_params.get('status')
        if status_filtro:
            qs = cliente.pedidos_por_status(status_filtro)
        else:
            qs = cliente.pedidos.all()
        serializer = PedidoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='enderecos')
    def enderecos(self, request, pk=None):
        """GET /clientes/{id}/enderecos/"""
        cliente    = self.get_object()
        serializer = EnderecoSerializer(cliente.enderecos.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='avaliacoes')
    def avaliacoes(self, request, pk=None):
        """GET /clientes/{id}/avaliacoes/"""
        cliente    = self.get_object()
        serializer = AvaliacaoSerializer(cliente.avaliacoes.all(), many=True)
        return Response(serializer.data)


# ENDERECO

class EnderecoViewSet(viewsets.ModelViewSet):
    """
    GET    /clientes/{cliente_pk}/enderecos/       → lista endereços do cliente
    POST   /clientes/{cliente_pk}/enderecos/       → adiciona endereço
    GET    /clientes/{cliente_pk}/enderecos/{id}/  → detalhe
    PUT    /clientes/{cliente_pk}/enderecos/{id}/  → atualiza
    DELETE /clientes/{cliente_pk}/enderecos/{id}/  → remove
    """
    serializer_class = EnderecoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Endereco.objects.filter(cliente_id=self.kwargs['cliente_pk'])

    def perform_create(self, serializer):
        cliente = get_object_or_404(Cliente, pk=self.kwargs['cliente_pk'])
        serializer.save(cliente=cliente)



# PEDIDO

class PedidoViewSet(viewsets.ModelViewSet):
    """
    GET    /pedidos/                  → lista (admin vê todos; cliente vê os seus)
    POST   /pedidos/                  → cria pedido com itens
    GET    /pedidos/{id}/             → detalhe
    GET    /pedidos/{id}/itens/       → itens do pedido
    POST   /pedidos/{id}/cancelar/    → cancela e devolve estoque
    POST   /pedidos/{id}/avancar/     → avança o status
    """
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['data_pedido', 'valor_total', 'status']

    def get_queryset(self):
        user = self.request.user
        qs   = Pedido.objects.select_related('cliente', 'pagamento').prefetch_related('itens')
        if user.is_staff:
            return qs.all()
        return qs.filter(cliente__user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return PedidoCreateSerializer
        return PedidoSerializer

    @action(detail=True, methods=['get'], url_path='itens')
    def itens(self, request, pk=None):
        """GET /pedidos/{id}/itens/"""
        pedido     = self.get_object()
        serializer = ItensPedidoSerializer(pedido.itens.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """POST /pedidos/{id}/cancelar/"""
        pedido = self.get_object()
        try:
            pedido.cancelar()
            return Response({"mensagem": "Pedido cancelado com sucesso."})
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='avancar')
    def avancar(self, request, pk=None):
        """POST /pedidos/{id}/avancar/ — avança o status para o próximo."""
        pedido = self.get_object()
        try:
            pedido.avancar_status()
            return Response({
                "mensagem": "Status atualizado.",
                "status": pedido.status,
            })
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)


#ITENS DO PEDIDO
class ItensPedidoViewSet(viewsets.ModelViewSet):
    """
    Rota aninhada em pedido: /pedidos/{pedido_pk}/itens/
    GET    → lista itens do pedido
    POST   → adiciona item
    GET    /{id}/ → detalhe
    DELETE /{id}/ → remove item
    """
    serializer_class   = ItensPedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ItensPedido.objects.filter(pedido_id=self.kwargs['pedido_pk'])

    def perform_create(self, serializer):
        pedido = get_object_or_404(Pedido, pk=self.kwargs['pedido_pk'])
        item   = serializer.save(pedido=pedido)
        pedido.calcular_total()
        return item

    def perform_destroy(self, instance):
        pedido = instance.pedido
        instance.delete()
        pedido.calcular_total()  # recalcula após remoção do item


# AVALIACAO
class AvaliacaoViewSet(viewsets.ModelViewSet):
    """
    GET    /avaliacoes/       → lista todas
    POST   /avaliacoes/       → cria avaliação
    GET    /avaliacoes/{id}/  → detalhe
    PUT    /avaliacoes/{id}/  → atualiza (dono ou admin)
    DELETE /avaliacoes/{id}/  → remove (dono ou admin)
    """
    queryset         = Avaliacao.objects.select_related('cliente', 'produto').all()
    serializer_class = AvaliacaoSerializer
    filter_backends  = [filters.OrderingFilter]
    ordering_fields  = ['nota']
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'list':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        cliente = get_object_or_404(Cliente, user=self.request.user)
        serializer.save(cliente=cliente)

    def get_object(self):
        """Garante que só o dono ou admin pode editar/deletar."""
        obj  = super().get_object()
        user = self.request.user
        if not user.is_staff and obj.cliente.user != user:
            self.permission_denied(self.request)
        return obj


# M,N EXPLÍCITAS
class ProdutoAvaliacaoViewSet(viewsets.ModelViewSet):
    queryset           = ProdutoAvaliacao.objects.all()
    serializer_class   = ProdutoAvaliacaoSerializer
    permission_classes = [IsAdminUser]


class AvaliacaoCategoriaViewSet(viewsets.ModelViewSet):
    queryset           = AvaliacaoCategoria.objects.all()
    serializer_class   = AvaliacaoCategoriaSerializer
    permission_classes = [IsAdminUser]
