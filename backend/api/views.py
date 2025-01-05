from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from recipes.models import (User, Recipe,
                            Tag, Ingredient,
                            Favorite, ShoppingCart,
                            RecipeIngredient, ShortLink,
                            Subscription)
from .serializers import (UserRegistrationSerializer, UserListSerializer,
                          UserProfileSerializer, TagSerializer,
                          IngredientSerializer, RecipeSerializer,
                          AvatarSerializer, SetPasswordSerializer)
from .permissions import IsAuthorOrReadOnly
from .filters import IngredientFilter, RecipeFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.http import HttpResponse


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = LimitOffsetPagination

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserRegistrationSerializer(user).data
            return Response(user_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        if pk == 'me':
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Учетные данные не были предоставлены."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            user = request.user
            serializer = UserProfileSerializer(
                user, context={'request': request})
            return Response(serializer.data)
        else:
            user = get_object_or_404(User, pk=pk)
            serializer = UserProfileSerializer(
                user, context={'request': request})
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password',
        permission_classes=[permissions.IsAuthenticated]
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=204)
        return Response(serializer.errors, status=400)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated],
    )
    def avatar(self, request):
        if request.method == 'DELETE':
            user = request.user
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({
                "detail": "Учетные данные не были предоставлены."},
                status=status.HTTP_404_NOT_FOUND)
        elif request.method == 'PUT':
            serializer = AvatarSerializer(data=request.data)
            if serializer.is_valid():
                user = request.user
                user.avatar = serializer.validated_data['avatar']
                user.save()
                avatar_url = request.build_absolute_uri(
                    user.avatar.url) if user.avatar else None
                return Response({"avatar": avatar_url},
                                status=status.HTTP_200_OK)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, pk):
        author = self.get_object()
        user = request.user
        if user.id == author.id:
            return Response(
                {'detail': 'Вы не можете подписаться на себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes_limit = int(recipes_limit
                            ) if recipes_limit is not None else None
        if request.method == 'POST':
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author).first()
            if subscription:
                subscription.delete()
            else:
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        recipes = author.recipes.all()
        if recipes_limit is not None:
            recipes = recipes[:recipes_limit]
        recipes_data = [
            {
                "id": recipe.id,
                "name": recipe.name,
                "image": self.request.build_absolute_uri(recipe.image.url),
                "cooking_time": recipe.cooking_time
            }
            for recipe in recipes
        ]
        if request.method == 'POST':
            response_status = status.HTTP_201_CREATED
        else:
            response_status = status.HTTP_204_NO_CONTENT

        return Response({
            "email": author.email,
            "id": author.id,
            "username": author.username,
            "first_name": author.first_name,
            "last_name": author.last_name,
            "is_subscribed": Subscription.objects.filter(
                user=self.request.user, author=author).exists(),
            "recipes": recipes_data,
            "recipes_count": recipes.count(),
            "avatar": self.request.build_absolute_uri(
                author.avatar.url) if author.avatar else None
        }, status=response_status)

    @action(
        detail=False,
        methods=['get',],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        user = request.user
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes_limit = int(
            recipes_limit) if recipes_limit is not None else None
        subscriptions = Subscription.objects.filter(
            user=user).select_related('author')
        paginator = self.pagination_class()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request)
        data = []
        for sub in paginated_subscriptions:
            author = sub.author
            recipes = author.recipes.all()
            if recipes_limit is not None:
                recipes = recipes[:recipes_limit]
            author_data = {
                'id': author.id,
                'email': author.email,
                'username': author.username,
                'first_name': author.first_name,
                'last_name': author.last_name,
                'is_subscribed': Subscription.objects.filter(
                    user=user, author=author).exists(),
                'recipes': [
                    {
                        'id': recipe.id,
                        'name': recipe.name,
                        'image': recipe.image.url if recipe.image else None,
                        'cooking_time': recipe.cooking_time
                    }
                    for recipe in recipes
                ],
                'recipes_count': author.recipes.count(),
                'avatar': author.avatar.url if author.avatar else None,
            }
            data.append(author_data)
        return paginator.get_paginated_response(data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        tags_data = self.request.data.get('tags', [])
        for tag_id in tags_data:
            tag = get_object_or_404(Tag, id=tag_id)
            recipe.tags.add(tag)
        ingredients_data = self.request.data.get('ingredients', [])
        for ingredient in ingredients_data:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')
            if ingredient_id is not None and amount is not None:
                current_ingredient = get_object_or_404(Ingredient,
                                                       id=ingredient_id)
                RecipeIngredient.objects.create(
                    ingredients=current_ingredient,
                    recipe=recipe,
                    amount=amount
                )

    @action(
        detail=True,
        methods=['post', 'get'],
        url_path='get-link'
    )
    def create_short_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link, created = ShortLink.objects.get_or_create(recipe=recipe)
        short_url = request.build_absolute_uri(
            f"/api/recipes/links/{short_link.short_code}/")
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe)
            if created:
                shopping_cart_data = {
                    "id": recipe.id,
                    "name": recipe.name,
                    "image": request.build_absolute_uri(recipe.image.url),
                    "cooking_time": recipe.cooking_time
                }
                return Response(shopping_cart_data,
                                status=status.HTTP_201_CREATED)
            else:
                return Response({'detail': 'Рецепт уже в корзине.'},
                                status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            shopping_cart = ShoppingCart.objects.filter(
                user=user, recipe=recipe)
            if shopping_cart.exists():
                shopping_cart.delete()
                return Response({'detail': 'Рецепт удален из корзины.'},
                                status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'detail': 'Рецепт не найден в корзине.'},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        recipes = [item.recipe for item in shopping_cart_items]
        ingredients_dict = {}
        for recipe in recipes:
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
            for ri in recipe_ingredients:
                ingredient_name = ri.ingredients.name
                measurement_unit = ri.ingredients.measurement_unit
                key = f'{ingredient_name} ({measurement_unit})'
                if key in ingredients_dict:
                    ingredients_dict[key] += ri.amount
                else:
                    ingredients_dict[key] = ri.amount
        ingredients_text = "Список покупок:\n\n"
        for ingredient, amount in ingredients_dict.items():
            ingredients_text += f"{ingredient} - {amount}\n"
        response = HttpResponse(ingredients_text, content_type='text/plain')
        response['Content-Disposition'
                 ] = 'attachment; filename="shopping_cart.txt"'
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                user=user, recipe=recipe)
            if created:
                favorite_recipe_data = {
                    "id": recipe.id,
                    "name": recipe.name,
                    "image": request.build_absolute_uri(recipe.image.url),
                    "cooking_time": recipe.cooking_time
                }
                return Response(favorite_recipe_data,
                                status=status.HTTP_201_CREATED)
            else:
                return Response({'detail': 'Рецепт уже в избранном.'},
                                status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if favorite.exists():
                favorite.delete()
                return Response({'detail': 'Рецепт удален из избранного.'},
                                status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'detail': 'Рецепт не найден в избранном.'},
                                status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None
