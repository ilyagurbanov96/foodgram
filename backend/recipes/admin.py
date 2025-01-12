from django.contrib import admin
from django.contrib.auth.models import Group
from .models import (User, Recipe, Tag,
                     Ingredient, Subscription, RecipeIngredient)

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'first_name', 'last_name')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('username', 'email')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')


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


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    search_fields = ('name', )
    list_display = (
        'id', 'author', 'name', 'image', 'text')
    list_display_links = ('id', 'name')
    inlines = [
        RecipeIngredientInline,
    ]


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'amount')
