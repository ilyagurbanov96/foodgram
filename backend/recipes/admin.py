from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from .models import (Favorite, Ingredient, Recipe,
                     RecipeIngredient, ShoppingCart, Tag)

admin.site.unregister(Group)


class IngredientsInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user', 'recipe')
    list_filter = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user', 'recipe')
    list_filter = ('user', 'recipe')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name', 'slug')
    list_display = (
        'id', 'name', 'slug')
    list_display_links = ('id', 'name')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ('name', )
    list_display = (
        'id', 'name', 'measurement_unit')
    list_display_links = ('id', 'name')
    list_filter = ('measurement_unit',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    search_fields = ('name', )
    list_display = (
        'id', 'author', 'name', 'get_image', 'text', 'favorite_count')
    list_display_links = ('id', 'name')
    inlines = (IngredientsInline,)

    @admin.display(description='Изображение')
    def get_image(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src={obj.image.url} width="80" height="60">')
        return '(none)'

    @admin.display(description='Кол-во добавлений в Избранное')
    def favorite_count(self, obj):
        count = obj.favorites.count()
        return f'{count} {"раз" if count != 1 else "раза"}'


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'amount')
