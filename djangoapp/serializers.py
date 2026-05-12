# djangoapp/serializers.py

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import (
    Categoria, Produto, ProdutoImagem, Pagamento, Cliente,
    Endereco, Pedido, ItensPedido, Avaliacao,
    ProdutoAvaliacao, AvaliacaoCategoria,
)


# =============================================================================
# AUTH
# =============================================================================

class RegistroSerializer(serializers.ModelSerializer):
    cpf      = serializers.CharField(write_only=True)
    nome     = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ['username', 'email', 'password', 'nome', 'cpf']

    def create(self, validated_data):
        nome = validated_data.pop('nome')
        cpf  = validated_data.pop('cpf')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        Cliente.objects.create(user=user, nome=nome, cpf=cpf, email=user.email)
        return user


class MeuTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email']    = user.email
        try:
            token['cliente_id'] = user.cliente.id
            token['nome']       = user.cliente.nome
            token['role']       = user.cliente.role
        except Cliente.DoesNotExist:
            pass
        return token


# =============================================================================
# CATEGORIA
# =============================================================================

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Categoria
        fields = ['id', 'nome']


# =============================================================================
# PRODUTO IMAGEM
# =============================================================================

class ProdutoImagemSerializer(serializers.ModelSerializer):
    """
    Serializer completo — usado na view de gerenciamento de imagens (admin).
    Retorna a URL absoluta e permite upload, ordenação e marcação de principal.
    """
    imagem_url = serializers.SerializerMethodField()
    imagem     = serializers.ImageField(write_only=True)

    class Meta:
        model  = ProdutoImagem
        fields = ['id', 'imagem', 'imagem_url', 'principal', 'ordem', 'alt']

    def get_imagem_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.imagem and request:
            return request.build_absolute_uri(obj.imagem.url)
        return obj.imagem.url if obj.imagem else None

    def validate_imagem(self, value):
        formatos_validos = ['image/jpeg', 'image/png', 'image/webp']
        if hasattr(value, 'content_type') and value.content_type not in formatos_validos:
            raise serializers.ValidationError("Formato inválido. Use JPG, PNG ou WEBP.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Tamanho máximo: 5 MB.")
        return value


class ProdutoImagemCardSerializer(serializers.ModelSerializer):
    """
    Serializer reduzido — usado na LISTAGEM de produtos (card).
    Retorna apenas a imagem principal com URL absoluta.
    """
    imagem_url = serializers.SerializerMethodField()

    class Meta:
        model  = ProdutoImagem
        fields = ['id', 'imagem_url', 'alt']

    def get_imagem_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.imagem and request:
            return request.build_absolute_uri(obj.imagem.url)
        return obj.imagem.url if obj.imagem else None


# =============================================================================
# PRODUTO — LISTAGEM (card)
# Retorna apenas a imagem principal para montar o card na listagem.
# =============================================================================

class ProdutoListSerializer(serializers.ModelSerializer):
    """Usado em GET /produtos/ — resposta leve para montar os cards."""
    categoria_nome   = serializers.CharField(source='categoria.nome', read_only=True)
    media_avaliacoes = serializers.SerializerMethodField()
    em_estoque       = serializers.SerializerMethodField()
    imagem_principal = serializers.SerializerMethodField()

    class Meta:
        model  = Produto
        fields = [
            'id',
            'nome_produto',
            'preco',
            'estoque',
            'em_estoque',
            'categoria',
            'categoria_nome',
            'media_avaliacoes',
            'imagem_principal',   # ← apenas 1 imagem para o card
        ]

    def get_media_avaliacoes(self, obj) -> float | None:
        return obj.media_avaliacoes()

    def get_em_estoque(self, obj) -> bool:
        return obj.em_estoque()

    def get_imagem_principal(self, obj) -> dict | None:
        imagem = obj.imagem_principal
        if not imagem:
            return None
        return ProdutoImagemCardSerializer(imagem, context=self.context).data


# =============================================================================
# PRODUTO — DETALHE
# Retorna todas as imagens para montar o carrossel na página de detalhe.
# =============================================================================

class ProdutoDetalheSerializer(serializers.ModelSerializer):
    """Usado em GET /produtos/{id}/ — resposta completa com galeria de imagens."""
    categoria_nome   = serializers.CharField(source='categoria.nome', read_only=True)
    media_avaliacoes = serializers.SerializerMethodField()
    em_estoque       = serializers.SerializerMethodField()
    imagens          = ProdutoImagemSerializer(many=True, read_only=True)  # galeria completa

    class Meta:
        model  = Produto
        fields = [
            'id',
            'nome_produto',
            'preco',
            'estoque',
            'em_estoque',
            'categoria',
            'categoria_nome',
            'media_avaliacoes',
            'imagens',            # ← todas as imagens para o carrossel
        ]

    def get_media_avaliacoes(self, obj) -> float | None:
        return obj.media_avaliacoes()

    def get_em_estoque(self, obj) -> bool:
        return obj.em_estoque()


# =============================================================================
# PRODUTO — CRIAÇÃO / EDIÇÃO (write)
# =============================================================================

class ProdutoWriteSerializer(serializers.ModelSerializer):
    """Usado em POST e PUT /produtos/ — apenas campos editáveis."""
    class Meta:
        model  = Produto
        fields = ['id', 'nome_produto', 'preco', 'estoque', 'categoria']


# =============================================================================
# PAGAMENTO
# =============================================================================

class PagamentoSerializer(serializers.ModelSerializer):
    metodo_display = serializers.CharField(source='get_metodo_display', read_only=True)

    class Meta:
        model  = Pagamento
        fields = ['id', 'metodo', 'metodo_display', 'valor']


# =============================================================================
# ENDERECO
# =============================================================================

class EnderecoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Endereco
        fields = ['id', 'rua', 'cidade', 'estado', 'cep']


# =============================================================================
# CLIENTE
# =============================================================================

class ClienteSerializer(serializers.ModelSerializer):
    enderecos           = EnderecoSerializer(many=True, read_only=True)
    total_gasto         = serializers.SerializerMethodField()
    pedido_mais_recente = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = ['id', 'nome', 'cpf', 'email', 'role',
                  'enderecos', 'total_gasto', 'pedido_mais_recente']

    def get_total_gasto(self, obj):
        return obj.total_gasto()

    def get_pedido_mais_recente(self, obj):
        pedido = obj.pedido_mais_recente()
        if pedido:
            return {'id': pedido.id, 'status': pedido.status, 'data': pedido.data_pedido}
        return None


# =============================================================================
# ITENS DO PEDIDO
# =============================================================================

class ItensPedidoSerializer(serializers.ModelSerializer):
    produto_nome   = serializers.CharField(source='produto.nome_produto', read_only=True)
    produto_imagem = serializers.SerializerMethodField()
    subtotal       = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model  = ItensPedido
        fields = ['id', 'produto', 'produto_nome', 'produto_imagem',
                  'quantidade', 'preco_unitario', 'subtotal']

    def get_produto_imagem(self, obj) -> str | None:
        """Retorna só a URL da imagem principal para exibir no carrinho."""
        imagem = obj.produto.imagem_principal
        if not imagem:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(imagem.imagem.url)
        return imagem.imagem.url

    def validate_quantidade(self, value):
        if value <= 0:
            raise serializers.ValidationError("A quantidade deve ser maior que zero.")
        return value

    def validate(self, data):
        produto    = data.get('produto')
        quantidade = data.get('quantidade', 0)
        if produto and quantidade > produto.estoque:
            raise serializers.ValidationError(
                f"Estoque insuficiente para '{produto.nome_produto}'. "
                f"Disponível: {produto.estoque}."
            )
        return data


# =============================================================================
# PEDIDO
# =============================================================================

class PedidoSerializer(serializers.ModelSerializer):
    itens          = ItensPedidoSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cliente_nome   = serializers.CharField(source='cliente.nome', read_only=True)
    pagamento_info = PagamentoSerializer(source='pagamento', read_only=True)

    class Meta:
        model  = Pedido
        fields = ['id', 'cliente', 'cliente_nome', 'pagamento', 'pagamento_info',
                  'data_pedido', 'valor_total', 'status', 'status_display', 'senha', 'itens']
        extra_kwargs = {
            'senha':       {'write_only': True},
            'valor_total': {'read_only': True},
            'cliente':     {'write_only': True},
            'pagamento':   {'write_only': True},
        }

    def validate_status(self, value):
        instancia = self.instance
        if instancia and instancia.status == 'cancelado':
            raise serializers.ValidationError("Pedidos cancelados não podem ser alterados.")
        if instancia and instancia.status == 'entregue' and value == 'cancelado':
            raise serializers.ValidationError("Pedidos entregues não podem ser cancelados.")
        return value


class PedidoCreateSerializer(serializers.ModelSerializer):
    itens = ItensPedidoSerializer(many=True)
    senha = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model  = Pedido
        fields = ['cliente', 'pagamento', 'senha', 'itens']

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        pedido     = Pedido.objects.create(**validated_data)
        for item_data in itens_data:
            ItensPedido.objects.create(pedido=pedido, **item_data)
        pedido.calcular_total()
        return pedido


# =============================================================================
# AVALIACAO
# =============================================================================

class AvaliacaoSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome_produto', read_only=True)
    categorias   = CategoriaSerializer(many=True, read_only=True)

    class Meta:
        model  = Avaliacao
        fields = ['id', 'cliente', 'cliente_nome', 'produto', 'produto_nome',
                  'nota', 'comentario', 'categorias']
        extra_kwargs = {
            'cliente': {'write_only': True},
            'produto': {'write_only': True},
        }

    def validate_nota(self, value):
        if not (0 <= value <= 5):
            raise serializers.ValidationError("A nota deve estar entre 0 e 5.")
        return value

    def validate(self, data):
        cliente = data.get('cliente')
        produto = data.get('produto')
        comprou = ItensPedido.objects.filter(
            pedido__cliente=cliente, produto=produto
        ).exists()
        if not comprou:
            raise serializers.ValidationError(
                "O cliente só pode avaliar produtos que já comprou."
            )
        return data


# =============================================================================
# M2M EXPLÍCITAS
# =============================================================================

class ProdutoAvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProdutoAvaliacao
        fields = ['id', 'produto', 'avaliacao']


class AvaliacaoCategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AvaliacaoCategoria
        fields = ['id', 'avaliacao', 'categoria']