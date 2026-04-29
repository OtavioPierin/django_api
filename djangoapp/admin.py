from django.contrib import admin
from .models import Produto, Pedido, Cliente, Categoria, ItensPedido, Endereco, Pagamento, Avaliacao, ProdutoAvaliacao, AvaliacaoCategoria

admin.site.register(Produto)
admin.site.register(Pedido)
admin.site.register(Cliente)
admin.site.register(Categoria)
admin.site.register(ItensPedido)
admin.site.register(Endereco)
admin.site.register(Pagamento)
admin.site.register(Avaliacao)
admin.site.register(ProdutoAvaliacao)
admin.site.register(AvaliacaoCategoria)