from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subscription, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'email', 'username', 'first_name', 'last_name')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('username', 'email')

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('avatar',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets

    @admin.display(description='Кол-во рецептов')
    def recipe_count(self, obj):
        count = obj.recipes.count()
        return f'{count} {"рецепт" if count == 1 else "рецепта" if 2 <= count <= 4 else "рецептов"}'

    @admin.display(description='Кол-во подписчиков')
    def subscription_count(self, obj):
        count = obj.subscribers.count()
        return f'{count} {"подписчик" if count == 1 else "подписчика" if 2 <= count <= 4 else "подписчиков"}'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')
