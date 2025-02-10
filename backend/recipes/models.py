import hashlib

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.timezone import now

from recipes.constants import (MAX_LENGTH_20, MAX_LENGTH_32, MAX_LENGTH_64,
                               MAX_LENGTH_128, MAX_LENGTH_256, MIN_VALUE_1)
from users.models import User


class Tag(models.Model):
    name = models.CharField('Название', max_length=MAX_LENGTH_32, unique=True)
    slug = models.SlugField('Слаг', max_length=MAX_LENGTH_32, unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name[:MAX_LENGTH_20]


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=MAX_LENGTH_128, unique=True)
    measurement_unit = models.CharField(
        'Единица измерения', max_length=MAX_LENGTH_64
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_measurement_unit'
            ),
        )
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name[:MAX_LENGTH_20]


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='recipes', verbose_name='Автор')
    name = models.CharField('Название', max_length=MAX_LENGTH_256)
    image = models.ImageField('Картинка', upload_to='recipes/images/')
    text = models.TextField('Текст')
    ingredient = models.ManyToManyField(Ingredient,
                                        through='RecipeIngredient',
                                        verbose_name='Ингредиенты')
    tags = models.ManyToManyField(Tag, verbose_name='Теги')
    cooking_time = models.PositiveIntegerField(
        'Время приготовления', validators=(
            MinValueValidator(
                MIN_VALUE_1, f'''Время приготовления не должно
                быть меньше {MIN_VALUE_1} минуты'''
            ),
        ))
    pub_date = models.DateTimeField('Дата и время публикации', default=now,)

    def get_absolute_url(self):
        return reverse('recipe-detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('pub_date',)

    def __str__(self):
        return self.name[:MAX_LENGTH_20]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               related_name='recipe_ingredients',
                               verbose_name='Рецепт')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE,
                                   related_name='recipe_ingredients',
                                   verbose_name='Ингредиент')
    amount = models.PositiveIntegerField(
        'Количество', default=MIN_VALUE_1, validators=(MinValueValidator(
            MIN_VALUE_1, f'''Количество ингредиентов не может
            быть меньше {MIN_VALUE_1}'''
        ),))

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )
        verbose_name = 'ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return f'{self.recipe} - {self.ingredient.name}'


class AbstractRecipeRelation(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               verbose_name='Рецепт')

    class Meta:
        abstract = True

    def __str__(self):
        return f'''{self.user.username} - {self.recipe.name} (
        {self._meta.verbose_name})'''


class Favorite(AbstractRecipeRelation):
    class Meta(AbstractRecipeRelation.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_user_recipe'
            ),
        )
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'


class ShoppingCart(AbstractRecipeRelation):
    class Meta(AbstractRecipeRelation.Meta):
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shoppingcart_user_recipe'
            ),
        )
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shoppingcarts'


class ShortLink(models.Model):
    original_url = models.URLField(max_length=MAX_LENGTH_256, unique=True,
                                   null=True, verbose_name='Оригинальный URL')
    short_code = models.CharField(max_length=MAX_LENGTH_20, unique=True,
                                  verbose_name='Короткий код')

    def generate_short_code(self):
        return hashlib.md5(self.original_url.encode()
                           ).hexdigest()[:MAX_LENGTH_20]

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def __str__(self):
        return f'{self.original_url} -> {self.short_code}'
