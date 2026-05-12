# djangoapp/views.py

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404

from .models import (
    Categoria, Produto, ProdutoImagem, Pagamento, Cliente,
    Endereco, Pedido, ItensPedido, Avaliacao,
    ProdutoAvaliacao, AvaliacaoCategoria,
)
from .serializers import (
    RegistroSerializer, MeuTokenSerializer,
    CategoriaSerializer,
    ProdutoListSerializer, ProdutoDetalheSerializer, ProdutoWriteSerializer,
    ProdutoImagemSerializer,
    PagamentoSerializer, ClienteSerializer,
    EnderecoSerializer, PedidoSerializer,
    PedidoCreateSerializer, ItensPedidoSerializer,
    AvaliacaoSerializer, ProdutoAvaliacaoSerializer,
    AvaliacaoCategoriaSerializer,
)
from .permissions import IsAdminRole, IsGestorEstoque, IsOwnerOrAdmin


# =============================================================================
# AUTH
# =============================================================================

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class   = MeuTokenSerializer


class RegistroView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"mensagem": "Usuário criado com sucesso."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"erro": "Refresh token obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token)})
        except Exception:
            return Response({"erro": "Token inválido ou expirado."}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"erro": "Refresh token obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
            return Response({"mensagem": "Logout realizado com sucesso."})
        except Exception:
            return Response({"erro": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# CATEGORIA
# =============================================================================

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset         = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    filter_backends  = [filters.SearchFilter]
    search_fields    = ['nome']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRole()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='produtos')
    def produtos(self, request, pk=None):
        categoria  = self.get_object()
        serializer = ProdutoListSerializer(
            categoria.produtos.all(), many=True, context={'request': request}
        )
        return Response(serializer.data)


# =============================================================================
# PRODUTO
# Serializer diferente para listagem, detalhe e criação/edição.
# Imagens gerenciadas por rota separada: /produtos/{id}/imagens/
# =============================================================================

class ProdutoViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['nome_produto', 'categoria__nome']
    ordering_fields = ['preco', 'estoque', 'nome_produto']

    def get_queryset(self):
        # prefetch das imagens evita N+1 queries na listagem
        return Produto.objects.select_related('categoria').prefetch_related('imagens').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProdutoListSerializer      # card — só imagem principal
        if self.action == 'retrieve':
            return ProdutoDetalheSerializer   # detalhe — galeria completa
        return ProdutoWriteSerializer         # create/update — sem imagens

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsGestorEstoque()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='avaliacoes')
    def avaliacoes(self, request, pk=None):
        produto    = self.get_object()
        serializer = AvaliacaoSerializer(
            produto.avaliacoes.select_related('cliente').all(),
            many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reduzir-estoque')
    def reduzir_estoque(self, request, pk=None):
        produto    = self.get_object()
        quantidade = request.data.get('quantidade')
        if not quantidade or int(quantidade) <= 0:
            return Response({"erro": "Informe uma quantidade válida (> 0)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            produto.reduzir_estoque(int(quantidade))
            return Response({"mensagem": f"Novo estoque: {produto.estoque}."})
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# PRODUTO IMAGEM
# Rota aninhada: /produtos/{produto_pk}/imagens/
#
# GET    /produtos/{id}/imagens/          → lista todas as imagens
# POST   /produtos/{id}/imagens/          → adiciona uma imagem
# PATCH  /produtos/{id}/imagens/{img_id}/ → atualiza (ordem, principal, alt)
# DELETE /produtos/{id}/imagens/{img_id}/ → remove a imagem
# POST   /produtos/{id}/imagens/{img_id}/tornar-principal/ → define como principal
# =============================================================================

class ProdutoImagemViewSet(viewsets.ModelViewSet):
    serializer_class   = ProdutoImagemSerializer
    # MultiPartParser e FormParser necessários para receber arquivos
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsGestorEstoque()]   # apenas admin/estoque gerencia imagens

    def get_queryset(self):
        return ProdutoImagem.objects.filter(produto_id=self.kwargs['produto_pk'])

    def perform_create(self, serializer):
        produto = get_object_or_404(Produto, pk=self.kwargs['produto_pk'])
        # Se for a primeira imagem, marca como principal automaticamente
        e_primeira = not produto.imagens.exists()
        serializer.save(produto=produto, principal=e_primeira)

    @action(detail=True, methods=['post'], url_path='tornar-principal')
    def tornar_principal(self, request, produto_pk=None, pk=None):
        """
        POST /produtos/{id}/imagens/{img_id}/tornar-principal/
        Marca esta imagem como principal e desmarca as outras.
        """
        imagem = self.get_object()
        imagem.principal = True
        imagem.save()   # o save() do model já desmarca as outras
        return Response({"mensagem": "Imagem definida como principal."})


# =============================================================================
# PAGAMENTO
# =============================================================================

class PagamentoViewSet(viewsets.ModelViewSet):
    queryset         = Pagamento.objects.all()
    serializer_class = PagamentoSerializer

    def get_permissions(self):
        if self.action in ['list', 'destroy', 'update', 'partial_update']:
            return [IsAdminRole()]
        return [IsAuthenticated()]


# =============================================================================
# CLIENTE
# =============================================================================

class ClienteViewSet(viewsets.ModelViewSet):
    serializer_class = ClienteSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            if user.cliente.is_admin():
                return Cliente.objects.prefetch_related('enderecos').all()
        except Exception:
            pass
        return Cliente.objects.filter(user=user)

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        cliente    = get_object_or_404(Cliente, user=request.user)
        serializer = self.get_serializer(cliente)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='pedidos')
    def pedidos(self, request, pk=None):
        cliente       = self.get_object()
        status_filtro = request.query_params.get('status')
        qs = cliente.pedidos_por_status(status_filtro) if status_filtro else cliente.pedidos.all()
        return Response(PedidoSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='enderecos')
    def enderecos(self, request, pk=None):
        return Response(EnderecoSerializer(self.get_object().enderecos.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='avaliacoes')
    def avaliacoes(self, request, pk=None):
        return Response(AvaliacaoSerializer(self.get_object().avaliacoes.all(), many=True).data)

    @action(detail=True, methods=['patch'], url_path='alterar-role')
    def alterar_role(self, request, pk=None):
        if not request.user.cliente.is_admin():
            return Response({"erro": "Apenas administradores podem alterar papéis."}, status=status.HTTP_403_FORBIDDEN)
        cliente       = self.get_object()
        novo_role     = request.data.get('role')
        roles_validos = ['cliente', 'admin', 'estoque']
        if novo_role not in roles_validos:
            return Response({"erro": f"Role inválido. Escolha entre: {roles_validos}"}, status=status.HTTP_400_BAD_REQUEST)
        cliente.role = novo_role
        cliente.save(update_fields=['role'])
        return Response({"mensagem": f"Role de {cliente.nome} atualizado para '{novo_role}'."})


# =============================================================================
# ENDERECO
# =============================================================================

class EnderecoViewSet(viewsets.ModelViewSet):
    serializer_class   = EnderecoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Endereco.objects.filter(cliente_id=self.kwargs['cliente_pk'])

    def perform_create(self, serializer):
        cliente = get_object_or_404(Cliente, pk=self.kwargs['cliente_pk'])
        serializer.save(cliente=cliente)


# =============================================================================
# PEDIDO
# =============================================================================

class PedidoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['data_pedido', 'valor_total', 'status']

    def get_queryset(self):
        user = self.request.user
        qs   = Pedido.objects.select_related('cliente', 'pagamento').prefetch_related('itens')
        try:
            if user.cliente.is_admin():
                return qs.all()
        except Exception:
            pass
        return qs.filter(cliente__user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return PedidoCreateSerializer
        return PedidoSerializer

    @action(detail=True, methods=['get'], url_path='itens')
    def itens(self, request, pk=None):
        return Response(ItensPedidoSerializer(self.get_object().itens.all(), many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.cancelar()
            return Response({"mensagem": "Pedido cancelado com sucesso."})
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='avancar')
    def avancar(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.avancar_status()
            return Response({"mensagem": "Status atualizado.", "status": pedido.status})
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# ITENS DO PEDIDO
# =============================================================================

class ItensPedidoViewSet(viewsets.ModelViewSet):
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
        pedido.calcular_total()


# =============================================================================
# AVALIACAO
# =============================================================================

class AvaliacaoViewSet(viewsets.ModelViewSet):
    queryset           = Avaliacao.objects.select_related('cliente', 'produto').all()
    serializer_class   = AvaliacaoSerializer
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['nota']
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        cliente = get_object_or_404(Cliente, user=self.request.user)
        serializer.save(cliente=cliente)

    def get_object(self):
        obj  = super().get_object()
        user = self.request.user
        try:
            if user.cliente.is_admin():
                return obj
        except Exception:
            pass
        if obj.cliente.user != user:
            self.permission_denied(self.request)
        return obj


# =============================================================================
# M2M EXPLÍCITAS
# =============================================================================

class ProdutoAvaliacaoViewSet(viewsets.ModelViewSet):
    queryset           = ProdutoAvaliacao.objects.all()
    serializer_class   = ProdutoAvaliacaoSerializer
    permission_classes = [IsAdminRole]


class AvaliacaoCategoriaViewSet(viewsets.ModelViewSet):
    queryset           = AvaliacaoCategoria.objects.all()
    serializer_class   = AvaliacaoCategoriaSerializer
    permission_classes = [IsAdminRole]