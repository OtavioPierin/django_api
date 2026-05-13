# djangoapp/migrations/0005_produtoimagem.py
#
# Migration de segurança: garante que a tabela produto_imagens exista no banco.
# Execute: python manage.py migrate
#
# Se você já tem uma migration que cria ProdutoImagem, esta será ignorada
# pelo Django pois dependencies aponta para a migration anterior.

from django.db import migrations, models
import django.db.models.deletion
import djangoapp.models   # importa a função produto_imagem_path


class Migration(migrations.Migration):

    dependencies = [
        ('djangoapp', '0004_alter_avaliacaocategoria_options_and_more'),  # ajuste para o nome da sua última migration
    ]

    operations = [
        migrations.CreateModel(
            name='ProdutoImagem',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem',    models.ImageField(upload_to=djangoapp.models.produto_imagem_path)),
                ('principal', models.BooleanField(
                    default=False,
                    help_text='Marque como True para exibir no card da listagem.',
                )),
                ('ordem',     models.PositiveIntegerField(
                    default=0,
                    help_text='Ordem de exibição no carrossel do detalhe (menor = primeiro).',
                )),
                ('alt',       models.CharField(
                    blank=True,
                    max_length=120,
                    help_text='Texto alternativo para acessibilidade (alt da tag <img>).',
                )),
                ('produto',   models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='imagens',
                    to='djangoapp.produto',
                )),
            ],
            options={
                'verbose_name':        'Imagem do Produto',
                'verbose_name_plural': 'Imagens do Produto',
                'db_table':            'produto_imagens',
                'ordering':            ['ordem', 'id'],
            },
        ),
    ]