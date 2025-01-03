# Generated by Django 3.2.16 on 2024-12-20 20:57

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recipes', '0012_alter_subscription_recipe'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together={('user', 'author')},
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='recipe',
        ),
    ]
