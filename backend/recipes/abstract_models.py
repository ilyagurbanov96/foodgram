from django.db import models

from users.models import User


class AbstractRecipeRelation(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               verbose_name='Рецепт')

    class Meta:
        abstract = True

    def __str__(self):
        return f'''{self.user.username} - {self.recipe.name} (
        {self._meta.verbose_name})'''
