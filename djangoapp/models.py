"""
Ordem de declaração respeita as dependências entre tabelas:
    Categoria → Produto
    Pagamento
    Cliente → Endereco
    Pedido (FK: Cliente, Pagamento) → ItensPedido
    Avaliacao (FK: Cliente, Produto) → ProdutoAvaliacao, AvaliacaoCategoria
"""

import hashlib

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User

#CATEGORIA
class Categoria(models.Model):
    nome = models.CharField(max_length=20)

    class Meta:
        db_table = "categorias"
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


#PRODUTO
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
        db_table = "produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome_produto"]
        indexes = [
            models.Index(fields=["categoria"], name="idx_produto_categoria"),
        ]

    def __str__(self) -> str:
        return self.nome_produto

    
    # Métodos de negócio
    def em_estoque(self) -> bool:
        """True se plmns uma unidade disponível."""
        return self.estoque > 0

    def reduzir_estoque(self, quantidade: int) -> None:
        """
        -- o estoque após uma venda.
        ValueError se a quantidade pedida maior q o estoque.
        """
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
        """média das notas de avaliação do produto."""
        resultado = self.avaliacoes.aggregate(media=models.Avg("nota"))
        return resultado["media"]


#PAGAMENTO
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
        db_table = "pagamentos"
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"

    def __str__(self) -> str:
        return f"{self.get_metodo_display()} — R$ {self.valor:.2f}"


#CLIENTE
class Cliente(models.Model):
    user  = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cliente",
        null=True, blank=True,
    )    
    nome  = models.CharField(max_length=90)
    cpf   = models.CharField(max_length=14, unique=True)
    email = models.EmailField(max_length=120, unique=True)

    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.email})"

    #Métodos de negócio
    def pedido_mais_recente(self) -> "Pedido | None":
        """Retorna o pedido mais recente do cliente, ou None."""
        return self.pedidos.order_by("-data_pedido").first()

    def total_gasto(self):
        """Soma o valor_total de todos os pedidos do cliente."""
        return self.pedidos.aggregate(total=Sum("valor_total"))["total"] or 0

    def pedidos_por_status(self, status: str):
        """Filtra os pedidos por status."""
        return self.pedidos.filter(status=status)


#ENDERECO
class Endereco(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,       # endereços são excluídos com o cliente
        related_name="enderecos",
    )
    rua    = models.CharField(max_length=50)
    cidade = models.CharField(max_length=30)
    estado = models.CharField(max_length=2)   # UF: 'MG', 'SP', etc.
    cep    = models.CharField(max_length=10)  # CharField preserva zeros à esquerda

    class Meta:
        db_table = "enderecos"
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        indexes = [
            models.Index(fields=["cliente"], name="idx_enderecos_cliente"),
        ]

    def __str__(self) -> str:
        return f"{self.rua}, {self.cidade}/{self.estado} — CEP {self.cep}"


#PEDIDO
class Pedido(models.Model):

    STATUS_CHOICES = [
        ("pendente",    "Pendente"),
        ("processando", "Processando"),
        ("enviado",     "Enviado"),
        ("entregue",    "Entregue"),
        ("cancelado",   "Cancelado"),
    ]

    cliente     = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    pagamento   = models.ForeignKey(
        Pagamento,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    data_pedido = models.DateField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente",
    )
    # PIN de rastreio — armazenado como SHA-256
    senha = models.CharField(max_length=200)

    class Meta:
        db_table = "pedidos"
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-data_pedido"]
        indexes = [
            models.Index(fields=["cliente"], name="idx_pedidos_cliente"),
            models.Index(fields=["status"],  name="idx_pedidos_status"),
        ]

    def __str__(self) -> str:
        return f"Pedido #{self.pk} — {self.cliente.nome} [{self.get_status_display()}]"

    # Sobrescrita de save — hash da senha antes de persistir
    def save(self, *args, **kwargs) -> None:
        """
        Aplica SHA-256 na senha antes de salvar, apenas se ainda não
        estiver em formato hexadecimal de 64 caracteres.
        """
        if self.senha and len(self.senha) != 64:
            self.senha = hashlib.sha256(self.senha.encode()).hexdigest()
        super().save(*args, **kwargs)

    # Métodos de negócio
    def calcular_total(self) -> None:
        """
        Recalcula valor_total somando quantidade*preco_unitario
        de todos os itens do pedido.
        """
        total = sum(item.subtotal for item in self.itens.all())
        self.valor_total = total
        self.save(update_fields=["valor_total"])

    def cancelar(self) -> None:
        """Cancela o pedido e volta o estoque de cada item."""
        if self.status == "entregue":
            raise ValueError("Pedidos já entregues não podem ser cancelados.")
        for item in self.itens.all():
            item.produto.estoque += item.quantidade
            item.produto.save(update_fields=["estoque"])
        self.status = "cancelado"
        self.save(update_fields=["status"])

    def avancar_status(self) -> None:
        """Avança o pedido para o próximo status na sequência."""
        fluxo = ["pendente", "processando", "enviado", "entregue"]
        if self.status not in fluxo:
            raise ValueError(f"Pedido com status '{self.status}' não pode ser avançado.")
        idx = fluxo.index(self.status)
        if idx < len(fluxo) - 1:
            self.status = fluxo[idx + 1]
            self.save(update_fields=["status"])


#ITENS DO PEDIDO
class ItensPedido(models.Model):
    pedido         = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,       # itens são excluídos com o pedido
        related_name="itens",
    )
    produto        = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="itens_pedido",
    )
    quantidade     = models.IntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "itens_pedido"
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"
        indexes = [
            models.Index(fields=["pedido"],  name="idx_itens_pedido"),
            models.Index(fields=["produto"], name="idx_itens_produto"),
        ]

    def __str__(self) -> str:
        return f"{self.quantidade}× {self.produto.nome_produto} (Pedido #{self.pedido_id})"

    # Properties
    @property
    def subtotal(self):
        """Retorna o valor total do item (quantidade × preço unitário)."""
        return self.quantidade * self.preco_unitario

    # Sobrescrita de save — reduz estoque ao criar o item
    def save(self, *args, **kwargs) -> None:
        """Reduz o estoque do produto automaticamente na criação do item."""
        is_new = self._state.adding
        if is_new:
            self.produto.reduzir_estoque(self.quantidade)
        super().save(*args, **kwargs)


#AVALIACAO
class Avaliacao(models.Model):
    cliente    = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="avaliacoes",
    )
    produto    = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="avaliacoes",
    )
    nota       = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    comentario = models.CharField(max_length=100)

    # Relação m para n com Categoria via entidade intermediária
    categorias = models.ManyToManyField(
        Categoria,
        through="AvaliacaoCategoria",
        related_name="avaliacoes",
        blank=True,
    )

    class Meta:
        db_table = "avaliacoes"
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"
        # Garante que um cliente avalie um produto apenas uma vez
        unique_together = ("cliente", "produto")
        indexes = [
            models.Index(fields=["produto"], name="idx_avaliacoes_produto"),
        ]

    def __str__(self) -> str:
        return (
            f"Avaliação de {self.cliente.nome} — "
            f"{self.produto.nome_produto}: {self.nota}/5"
        )


#PRODUTO_AVALIACOES  (M,N explícita — produto <-> avaliacao)
class ProdutoAvaliacao(models.Model):
    produto   = models.ForeignKey(Produto,   on_delete=models.CASCADE)
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE)

    class Meta:
        db_table = "produto_avaliacoes"
        verbose_name = "Produto × Avaliação"
        verbose_name_plural = "Produtos × Avaliações"
        unique_together = ("produto", "avaliacao")

    def __str__(self) -> str:
        return f"{self.produto} ↔ Avaliação #{self.avaliacao_id}"


#AVALIACOES_CATEGORIAS  (M,N explícita — avaliacao <-> categoria)
class AvaliacaoCategoria(models.Model):
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        db_table = "avaliacoes_categorias"
        verbose_name = "Avaliação × Categoria"
        verbose_name_plural = "Avaliações × Categorias"
        unique_together = ("avaliacao", "categoria")

    def __str__(self) -> str:
        return f"Avaliação #{self.avaliacao_id} ↔ {self.categoria}"