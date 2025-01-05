import django_filters
from recipes.models import Ingredient, Recipe, ShoppingCart, Tag


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name',]


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tag.objects.all(),
        to_field_name='slug',
    )
    author = django_filters.CharFilter(lookup_expr='exact')
    is_in_shopping_cart = django_filters.CharFilter(
        method='filter_is_in_shopping_cart')
    is_favorited = django_filters.CharFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if str(value).lower() in ['1', 'true']:
            return queryset.filter(favorites__user=user)
        else:
            return queryset.exclude(favorites__user=user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        shopping_cart_recipes = ShoppingCart.objects.filter(
            user=user).values_list('recipe', flat=True)
        if str(value).lower() in ['1', 'true']:
            return queryset.filter(id__in=shopping_cart_recipes)
        else:
            return queryset.exclude(id__in=shopping_cart_recipes)
