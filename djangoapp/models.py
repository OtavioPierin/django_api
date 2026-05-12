"""
Ordem de declaração respeita as dependências entre tabelas:
    Categoria → Produto → ProdutoImagem
    Pagamento
    Cliente → Endereco
    Pedido (FK: Cliente, Pagamento) → ItensPedido
    Avaliacao (FK: Cliente, Produto) → ProdutoAvaliacao, AvaliacaoCategoria
"""

import hashlib
import os

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum, Avg
from django.contrib.auth.models import User


def produto_imagem_path(instance, filename):
    """
    Salva em: media/produtos/<id_produto>/<filename>
    instance pode ser ProdutoImagem — por isso usamos instance.produto_id
    """
    ext      = filename.rsplit('.', 1)[-1].lower()
    nome     = f"{filename.rsplit('.', 1)[0]}.{ext}"
    produto_id = getattr(instance, 'produto_id', None) or 'tmp'
    return os.path.join('produtos', str(produto_id), nome)


# =============================================================================
# CATEGORIA
# =============================================================================
class Categoria(models.Model):
    nome = models.CharField(max_length=20)

    class Meta:
        db_table        = "categorias"
        verbose_name    = "Categoria"
        verbose_name_plural = "Categorias"
        ordering        = ["nome"]

    def __str__(self) -> str:
        return self.nome


# =============================================================================
# PRODUTO
# =============================================================================
class Produto(models.Model):
    nome_produto = models.CharField(max_length=50)
    preco        = models.DecimalField(max_digits=10, decimal_places=2)
    estoque      = models.IntegerField(default=0)
    categoria    = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="produtos",
    )

    class Meta:
        db_table        = "produto"
        verbose_name    = "Produto"
        verbose_name_plural = "Produtos"
        ordering        = ["nome_produto"]
        indexes         = [
            models.Index(fields=["categoria"], name="idx_produto_categoria"),
        ]

    def __str__(self) -> str:
        return self.nome_produto

    # ------------------------------------------------------------------
    # Propriedades de imagem
    # ------------------------------------------------------------------
    @property
    def imagem_principal(self):
        """Retorna a imagem marcada como principal, ou a primeira disponível."""
        imagem = self.imagens.filter(principal=True).first()
        if not imagem:
            imagem = self.imagens.first()
        return imagem

    # ------------------------------------------------------------------
    # Métodos de negócio
    # ------------------------------------------------------------------
    def em_estoque(self) -> bool:
        return self.estoque > 0

    def reduzir_estoque(self, quantidade: int) -> None:
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        if quantidade > self.estoque:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {self.estoque}, "
                f"Solicitado: {quantidade}."
            )
        self.estoque -= quantidade
        self.save(update_fields=["estoque"])

    def media_avaliacoes(self) -> float | None:
        resultado = self.avaliacoes.aggregate(media=Avg("nota"))
        return resultado["media"]


# =============================================================================
# PRODUTO IMAGEM  — múltiplas imagens por produto
# =============================================================================
class ProdutoImagem(models.Model):
    produto   = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,    # apaga as imagens junto com o produto
        related_name="imagens",
    )
    imagem    = models.ImageField(upload_to=produto_imagem_path)
    principal = models.BooleanField(
        default=False,
        help_text="Marque como True para exibir no card da listagem.",
    )
    ordem     = models.PositiveIntegerField(
        default=0,
        help_text="Ordem de exibição no carrossel do detalhe (menor = primeiro).",
    )
    alt       = models.CharField(
        max_length=120,
        blank=True,
        help_text="Texto alternativo para acessibilidade (alt da tag <img>).",
    )

    class Meta:
        db_table        = "produto_imagens"
        verbose_name    = "Imagem do Produto"
        verbose_name_plural = "Imagens do Produto"
        ordering        = ["ordem", "id"]   # galeria sempre na mesma ordem

    def __str__(self) -> str:
        flag = " [principal]" if self.principal else ""
        return f"Imagem #{self.id} — {self.produto.nome_produto}{flag}"

    def save(self, *args, **kwargs) -> None:
        """
        Garante que apenas uma imagem por produto seja marcada como principal.
        Se esta for marcada, desmarca as outras.
        """
        if self.principal:
            ProdutoImagem.objects.filter(
                produto=self.produto, principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Remove o arquivo físico ao deletar o registro."""
        if self.imagem and os.path.isfile(self.imagem.path):
            os.remove(self.imagem.path)
        super().delete(*args, **kwargs)


# =============================================================================
# PAGAMENTO
# =============================================================================
class Pagamento(models.Model):
    METODO_CHOICES = [
        ("pix",            "PIX"),
        ("cartao_credito", "Cartão de Crédito"),
        ("cartao_debito",  "Cartão de Débito"),
        ("boleto",         "Boleto Bancário"),
    ]
    metodo = models.CharField(max_length=45, choices=METODO_CHOICES)
    valor  = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table     = "pagamentos"
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"

    def __str__(self) -> str:
        return f"{self.get_metodo_display()} — R$ {self.valor:.2f}"


# =============================================================================
# CLIENTE
# =============================================================================
class Cliente(models.Model):
    ROLE_CHOICES = [
        ('cliente', 'Cliente'),
        ('admin',   'Administrador'),
        ('estoque', 'Gestor de Estoque'),
    ]
    user  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    nome  = models.CharField(max_length=90)
    cpf   = models.CharField(max_length=14, unique=True)
    email = models.EmailField(max_length=120, unique=True)
    role  = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cliente')

    class Meta:
        db_table        = "clientes"
        verbose_name    = "Cliente"
        verbose_name_plural = "Clientes"
        ordering        = ["nome"]

    def is_admin(self) -> bool:
        return self.role == 'admin'

    def is_gestor_estoque(self) -> bool:
        return self.role in ['admin', 'estoque']

    def __str__(self) -> str:
        return f"{self.nome} ({self.email})"

    def pedido_mais_recente(self):
        return self.pedidos.order_by("-data_pedido").first()

    def total_gasto(self):
        return self.pedidos.aggregate(total=Sum("valor_total"))["total"] or 0

    def pedidos_por_status(self, status: str):
        return self.pedidos.filter(status=status)


# =============================================================================
# ENDERECO
# =============================================================================
class Endereco(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="enderecos")
    rua     = models.CharField(max_length=50)
    cidade  = models.CharField(max_length=30)
    estado  = models.CharField(max_length=2)
    cep     = models.CharField(max_length=10)

    class Meta:
        db_table     = "enderecos"
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        indexes      = [models.Index(fields=["cliente"], name="idx_enderecos_cliente")]

    def __str__(self) -> str:
        return f"{self.rua}, {self.cidade}/{self.estado} — CEP {self.cep}"


# =============================================================================
# PEDIDO
# =============================================================================
class Pedido(models.Model):
    STATUS_CHOICES = [
        ("pendente",    "Pendente"),
        ("processando", "Processando"),
        ("enviado",     "Enviado"),
        ("entregue",    "Entregue"),
        ("cancelado",   "Cancelado"),
    ]
    cliente     = models.ForeignKey(Cliente,   on_delete=models.PROTECT, related_name="pedidos")
    pagamento   = models.ForeignKey(Pagamento, on_delete=models.PROTECT, related_name="pedidos")
    data_pedido = models.DateField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    senha       = models.CharField(max_length=200)

    class Meta:
        db_table     = "pedidos"
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering     = ["-data_pedido"]
        indexes      = [
            models.Index(fields=["cliente"], name="idx_pedidos_cliente"),
            models.Index(fields=["status"],  name="idx_pedidos_status"),
        ]

    def __str__(self) -> str:
        return f"Pedido #{self.pk} — {self.cliente.nome} [{self.get_status_display()}]"

    def save(self, *args, **kwargs) -> None:
        if self.senha and len(self.senha) != 64:
            self.senha = hashlib.sha256(self.senha.encode()).hexdigest()
        super().save(*args, **kwargs)

    def calcular_total(self) -> None:
        total = sum(item.subtotal for item in self.itens.all())
        self.valor_total = total
        self.save(update_fields=["valor_total"])

    def cancelar(self) -> None:
        if self.status == "entregue":
            raise ValueError("Pedidos já entregues não podem ser cancelados.")
        for item in self.itens.all():
            item.produto.estoque += item.quantidade
            item.produto.save(update_fields=["estoque"])
        self.status = "cancelado"
        self.save(update_fields=["status"])

    def avancar_status(self) -> None:
        fluxo = ["pendente", "processando", "enviado", "entregue"]
        if self.status not in fluxo:
            raise ValueError(f"Status '{self.status}' não pode ser avançado.")
        idx = fluxo.index(self.status)
        if idx < len(fluxo) - 1:
            self.status = fluxo[idx + 1]
            self.save(update_fields=["status"])


# =============================================================================
# ITENS DO PEDIDO
# =============================================================================
class ItensPedido(models.Model):
    pedido         = models.ForeignKey(Pedido,  on_delete=models.CASCADE,  related_name="itens")
    produto        = models.ForeignKey(Produto, on_delete=models.PROTECT,  related_name="itens_pedido")
    quantidade     = models.IntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table     = "itens_pedido"
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        indexes      = [
            models.Index(fields=["pedido"],  name="idx_itens_pedido"),
            models.Index(fields=["produto"], name="idx_itens_produto"),
        ]

    def __str__(self) -> str:
        return f"{self.quantidade}× {self.produto.nome_produto} (Pedido #{self.pedido_id})"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            self.produto.reduzir_estoque(self.quantidade)
        super().save(*args, **kwargs)


# =============================================================================
# AVALIACAO
# =============================================================================
class Avaliacao(models.Model):
    cliente    = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="avaliacoes")
    produto    = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="avaliacoes")
    nota       = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    comentario = models.CharField(max_length=100)
    categorias = models.ManyToManyField(
        Categoria, through="AvaliacaoCategoria", related_name="avaliacoes", blank=True,
    )

    class Meta:
        db_table        = "avaliacoes"
        verbose_name    = "Avaliação"
        verbose_name_plural = "Avaliações"
        unique_together = ("cliente", "produto")
        indexes         = [models.Index(fields=["produto"], name="idx_avaliacoes_produto")]

    def __str__(self) -> str:
        return f"Avaliação de {self.cliente.nome} — {self.produto.nome_produto}: {self.nota}/5"


# =============================================================================
# M2M EXPLÍCITAS
# =============================================================================
class ProdutoAvaliacao(models.Model):
    produto   = models.ForeignKey(Produto,   on_delete=models.CASCADE)
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE)

    class Meta:
        db_table        = "produto_avaliacoes"
        unique_together = ("produto", "avaliacao")


class AvaliacaoCategoria(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        db_table        = "avaliacoes_categorias"
        unique_together = ("avaliacao", "categoria")