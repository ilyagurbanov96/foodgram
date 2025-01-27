from django.conf import settings
from django.db import models


class AbstractRecipeRelation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='%(class)s',
                             verbose_name='Пользователь')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='%(class)s',
                               verbose_name='Рецепт')

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name} ({self._meta.verbose_name})'
