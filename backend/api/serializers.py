from django.shortcuts import get_object_or_404
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
            return obj.authors.filter(user=request.user).exists()
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
    amount = serializers.IntegerField(max_value=MIN_VALUE_1)

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
            return Favorite.objects.filter(
                user=request.user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user, recipe=obj).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(read_only=True, many=True,
                                                   source='recipe_ingredients')
    tags = TagSerializer(read_only=True, many=True)
    image = Base64ImageField()
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags',
                  'ingredients', 'author',
                  'name', 'text',
                  'cooking_time', 'image')

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        recipe_ingredients = [
            RecipeIngredient(
                ingredients=get_object_or_404(Ingredient, id=ingredient['id']),
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data if ingredient.get(
                'id'
            ) and ingredient.get('amount')
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def update(self, recipe, validated_data):
        RecipeIngredient.objects.filter(recipe=recipe).delete()
        recipe.tags.set(validated_data.pop('tags', []))
        ingredients_data = validated_data.pop('ingredients', [])
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                ingredients=get_object_or_404(Ingredient, id=ingredient['id']),
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients_data if ingredient.get(
                'id'
            ) and ingredient.get('amount')
        )
        return super().update(recipe, validated_data)

    def validate(self, data):
        self.validate_tags()
        self.validate_ingredients()
        return data

    def validate_tags(self):
        tags_data = self.context['request'].data.get('tags')
        if not tags_data or not isinstance(tags_data, list):
            raise serializers.ValidationError(
                {'tags': 'Поле tags не может быть пустым'})
        if len(tags_data) != len(set(tags_data)):
            raise serializers.ValidationError(
                {'tags': 'Теги не могут повторяться'})
        invalid_tags = [tag_id for tag_id in tags_data
                        if not Tag.objects.filter(id=tag_id).exists()]
        if invalid_tags:
            invalid_tags_str = ', '.join(map(str, invalid_tags))
            raise serializers.ValidationError(
                {'tags': f'Теги с id {invalid_tags_str} не существуют'})

    def validate_ingredients(self):
        ingredients_data = self.context['request'].data.get('ingredients')
        if ingredients_data is None:
            raise serializers.ValidationError(
                {'ingredients': 'Поле ingredients отсутствует'})
        if not isinstance(ingredients_data, list) or not ingredients_data:
            raise serializers.ValidationError(
                {'ingredients': 'Поле ingredients не может быть пустым'})
        ingredient_ids = set()
        error_message = []
        error = False
        for ingredient in ingredients_data:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')
            if amount is None or not str(amount).isdigit() or int(amount) < 1:
                error_message.append('''Количество ингредиента
                                     не может быть равен 0''')
                error = True
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients': f'''
                    Ингредиент с id {ingredient_id} уже добавлен'''})
            ingredient_ids.add(ingredient_id)
            try:
                ingredient_id = int(ingredient_id)
            except ValueError:
                raise serializers.ValidationError(
                    {'ingredients': f'''
                    Ингредиент с id {ingredient_id} не найден'''})
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'''
                    Ингредиент с id {ingredient_id} не найден'''})
        if error:
            raise serializers.ValidationError(
                {'ingredients': [
                    {'любая шляпа': error_message},
                ]})

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
