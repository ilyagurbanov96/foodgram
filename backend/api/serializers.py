from rest_framework import serializers
from recipes.models import (Recipe, Ingredient,
                            Tag, Favorite,
                            ShoppingCart, Subscription,
                            RecipeIngredient, ShortLink)
from users.models import User
import base64
from django.core.files.base import ContentFile


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username',
                  'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Электронная почта уже существует."
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Имя пользователя уже существует."
            )
        return value

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserListSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'avatar')


class UserProfileSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(default=False)
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'is_subscribed',
                  'first_name', 'last_name', 'avatar')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            representation['is_subscribed'] = Subscription.objects.filter(
                user=request.user,
                author=instance
            ).exists()
        else:
            representation['is_subscribed'] = False
        return representation


class UserSubscribeSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(default=False)
    avatar = Base64ImageField(required=False)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'is_subscribed',
                  'first_name', 'last_name', 'avatar',
                  'recipes', 'recipes_count')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            representation['is_subscribed'] = Subscription.objects.filter(
                user=request.user,
                author=instance
            ).exists()
        else:
            representation['is_subscribed'] = False
        return representation

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes = Recipe.objects.filter(author=obj)
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            except ValueError:
                pass
        return RecipeSubscribeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']


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


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer()

    class Meta:
        model = RecipeIngredient
        fields = ('ingredients', 'amount')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredient_data = representation.pop('ingredients')
        return {
            'id': ingredient_data['id'],
            'name': ingredient_data['name'],
            'measurement_unit': ingredient_data['measurement_unit'],
            'amount': representation['amount']
        }


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(read_only=True, many=True,
                                             source='recipe_ingredients')
    tags = TagSerializer(read_only=True, many=True)
    image = Base64ImageField()
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
        for ingredient in ingredients_data:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')
            if amount is None or amount < 1:
                raise serializers.ValidationError(
                    {'ingredients': '''
                     Количество ингредиента должно быть больше 0'''})
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients': f'''
                     Ингредиент с id {ingredient_id} уже добавлен'''})
            ingredient_ids.add(ingredient_id)

            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'''
                     Ингредиент с id {ingredient_id} не найден'''})

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


class RecipeSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.context['request'].user
        current_password = attrs.get('current_password')
        if not user.check_password(current_password):
            raise serializers.ValidationError("Текущий пароль неверен.")
        return attrs

    def save(self):
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe')


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
