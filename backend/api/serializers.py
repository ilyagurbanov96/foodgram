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


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(default=False)
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'is_subscribed',
                  'first_name', 'last_name', 'avatar')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request.user.is_authenticated:
            representation['is_subscribed'] = Subscription.objects.filter(
                user=request.user, author=instance).exists()
        return representation


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
    author = UserSerializer(read_only=True)
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
        tags_data = self.context['request'].data.get('tags')
        if tags_data is None or (isinstance(tags_data, list) and not tags_data
                                 ):
            raise serializers.ValidationError(
                {'tags': 'Поле tags не может быть пустым'})
        if len(tags_data) != len(set(tags_data)):
            raise serializers.ValidationError(
                {'tags': 'Теги не могут повторяться'})
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
                    {'ingredients': '''Количество ингредиента
                     должно быть больше 0'''})
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients': f'''Ингредиент с id
                     {ingredient_id} уже добавлен'''})
            ingredient_ids.add(ingredient_id)
            try:
                Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    {'ingredients': f'''Ингредиент с id
                     {ingredient_id} не найден'''})
        return data

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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'password')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get(
            'first_name', instance.first_name)
        instance.last_name = validated_data.get(
            'last_name', instance.last_name)

        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
