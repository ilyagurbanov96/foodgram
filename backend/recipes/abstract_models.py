from django.db import models
from django.contrib.auth.models import User

class AbstractRecipeRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='%(class)s',
                             verbose_name='Пользователь')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='%(class)s',
                               verbose_name='Рецепт')

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe'
            ),
        )

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name} ({self._meta.verbose_name})'
