# Generated by Django 3.2.16 on 2024-12-20 15:35

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipes', '0010_alter_shortlink_recipe'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='recipe',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subscribers', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together={('user', 'author', 'recipe')},
        ),
    ]
