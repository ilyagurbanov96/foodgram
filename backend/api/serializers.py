from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import MIN_VALUE_1
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, ShortLink, Tag)
from users.models import Subscription, User


class UserProfileSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'avatar', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context['request']
        if request.user.is_authenticated:
            return obj.subscribers.filter(user=request.user).exists()
        return False


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortLink
        fields = ('recipe', 'short_code')


class RecipeIngredientGetSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(min_value=MIN_VALUE_1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeGetSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientGetSerializer(read_only=True, many=True,
                                                source='recipe_ingredients')
    tags = TagSerializer(read_only=True, many=True)
    author = UserProfileSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags',
                  'ingredients', 'author',
                  'name', 'text',
                  'cooking_time', 'image',
                  'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(
                user=request.user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.shoppingcarts.filter(
                user=request.user, recipe=obj).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredient = RecipeIngredientCreateSerializer(many=True,
                                                  source='recipe_ingredients')
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())
    image = Base64ImageField()
    author = UserProfileSerializer(read_only=True)
    cooking_time = serializers.IntegerField(min_value=MIN_VALUE_1)

    class Meta:
        model = Recipe
        fields = ('id', 'tags',
                  'ingredient', 'author',
                  'name', 'text',
                  'cooking_time', 'image')

    def validate(self, data):
        ingredient = data.get('ingredient')
        tags = data.get('tags')
        if tags is None:
            raise serializers.ValidationError(
                {'tags': 'Поле tags не может быть пустым'})
        if ingredient is None:
            raise serializers.ValidationError(
                {'ingredient': 'Поле ingredient не может быть пустым'})
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не могут повторяться'})
        invalid_tags = [tag_id for tag_id in tags
                        if not Tag.objects.filter(id=tag_id).exists()]
        if invalid_tags:
            invalid_tags_str = ', '.join(map(str, invalid_tags))
            raise serializers.ValidationError(
                {'tags': f'Теги с id {invalid_tags_str} не существуют'})
        ingredients_list = []
        for ing in ingredient:
            if ing['id'] in ingredients_list:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиент уже добавлен'})
            amount = ing.get('amount')
            if amount is None or int(amount) < 1:
                raise serializers.ValidationError(
                    {'ingredients': '''Количество ингредиента
                     должно быть больше 0'''})
            ing['amount'] = int(amount)
            ingredients_list.append(ingredient['id'])
        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredient = validated_data.pop('ingredient')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe_ingredients = []
        for ing in ingredient:
            amount = ing['amount']
            if isinstance(amount, str):
                amount = int(amount)
            recipe_ingredients.append(
                RecipeIngredient(
                    ingredient=ing['id'],
                    recipe=recipe,
                    amount=amount
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def update(self, recipe, validated_data):
        ingredient = validated_data.pop('ingredient')
        if 'tags' in validated_data:
            recipe.tags.set(validated_data.pop('tags'))
        if 'ingredient' in validated_data:
            recipe.ingredient.clear()
        recipe_ingredients = [
            RecipeIngredient(
                ingredient=(ingredient['id']),
                recipe=recipe,
                amount=int(ingredient['amount'])
            )
            for ingredient in ingredient
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return super().update(recipe, validated_data)

    def to_representation(self, instance):
        return RecipeGetSerializer(
            instance, context=self.context
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, attrs):
        if Favorite.objects.filter(user=attrs['user'],
                                   recipe=attrs['recipe']).exists():
            raise serializers.ValidationError("Рецепт уже в избранном.")
        return attrs


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, attrs):
        if ShoppingCart.objects.filter(user=attrs['user'],
                                       recipe=attrs['recipe']).exists():
            raise serializers.ValidationError("Рецепт уже в корзине.")
        return attrs


class SubscriptionGetSerializer(serializers.ModelSerializer):
    recipe_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'recipe_count')


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer
    user = UserProfileSerializer

    class Meta:
        model = Subscription
        fields = ('author', 'user')

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)
