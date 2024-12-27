from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from recipes.models import (User, Recipe, Tag, Ingredient,
                            Favorite, ShoppingCart,
                            RecipeIngredient, ShortLink,
                            Subscription)
from .serializers import (UserRegistrationSerializer, UserListSerializer,
                          UserProfileSerializer, TagSerializer,
                          IngredientSerializer, RecipeSerializer,
                          ShortLinkSerializer, FavoriteRecipeSerializer,
                          AvatarSerializer, SetPasswordSerializer,
                          UserSubscribeSerializer, ShoppingCartSerializer)
from .permissions import IsAuthorOrReadOnly
from .filters import IngredientFilter, RecipeFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404


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
                    status=status.HTTP_401_UNAUTHORIZED)
            user = request.user
            serializer = UserProfileSerializer(
                user, context={'request': request}
            )
            return Response(serializer.data)
        else:
            try:
                user = self.get_object()
            except User.DoesNotExist:
                return Response({"detail": "Пользователь не найден."},
                                status=status.HTTP_404_NOT_FOUND)
            serializer = UserProfileSerializer(user,
                                               context={'request': request})
            return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='set_password',
            permission_classes=[permissions.IsAuthenticated])
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=204)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['put'], url_path='me/avatar',
            permission_classes=[permissions.IsAuthenticated])
    def update_avatar(self, request):
        serializer = AvatarSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.avatar = serializer.validated_data['avatar']
            user.save()
            avatar_url = request.build_absolute_uri(user.avatar.url
                                                    ) if user.avatar else None
            return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='me/avatar',
            permission_classes=[permissions.IsAuthenticated])
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Учетные данные не были предоставлены."},
                        status=status.HTTP_404_NOT_FOUND)


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

    def create_short_link(self, request, pk=None):
        try:
            recipe = self.get_object()
            short_link, created = ShortLink.objects.get_or_create(
                recipe=recipe)
            short_url = request.build_absolute_uri(
                f"/api/recipes/links/{short_link.short_code}/")
            return Response({'short-link': short_url},
                            status=status.HTTP_201_CREATED
                            if created else status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Рецепт уже в корзине'},
                            status=status.HTTP_400_BAD_REQUEST)
        ShoppingCart.objects.create(user=user, recipe=recipe)
        return Response({'status': 'рецепт добавлен в корзину'},
                        status=status.HTTP_201_CREATED)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'request': self.request
        })
        return context

    @action(detail=True, methods=['post'], url_path='favorite',
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        favorite, created = Favorite.objects.get_or_create(user=user,
                                                           recipe=recipe)
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
            return Response({'detail': 'Recipe is already in favorites.'},
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


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteRecipeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        if not recipe_id:
            return Response({'detail': 'Не указан ID рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(Recipe, id=recipe_id)
        favorite_item, created = Favorite.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if created:
            return Response(FavoriteRecipeSerializer(favorite_item).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Рецепт уже в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        if not recipe_id:
            return Response({'detail': 'Не указан ID рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)
        favorite_item = get_object_or_404(Favorite, user=request.user,
                                          recipe_id=recipe_id)
        favorite_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingCartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, recipe_id):
        return Response(status=status.HTTP_201_CREATED)

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        if not recipe_id:
            return Response({'detail': 'Не указан ID рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(Recipe, id=recipe_id)
        shopping_cart_item, created = ShoppingCart.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if created:
            return Response(ShoppingCartSerializer(shopping_cart_item).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Рецепт уже в корзине.'},
                            status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        if not recipe_id:
            return Response({'detail': 'Не указан ID рецепта.'},
                            status=status.HTTP_400_BAD_REQUEST)
        shopping_cart_item = get_object_or_404(ShoppingCart, user=request.user,
                                               recipe_id=recipe_id)
        shopping_cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShortLinkViewSet(viewsets.ModelViewSet):
    serializer_class = ShortLinkSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, id=None):
        try:
            recipe = Recipe.objects.get(id=id)
            short_link, created = ShortLink.objects.get_or_create(
                recipe=recipe
            )
            short_url = request.build_absolute_uri(
                f"/api/recipes/{short_link.short_code}/")
            if created:
                return Response({'short_link': short_url},
                                status=status.HTTP_201_CREATED)
            else:
                return Response({'short_link': short_url},
                                status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response({'error': 'Рецепт не найден'},
                            status=status.HTTP_404_NOT_FOUND)


class SubscriptionViewSet(viewsets.ViewSet):
    pagination_class = LimitOffsetPagination
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, id=None):
        author = get_object_or_404(User, id=id)
        subscription, created = Subscription.objects.get_or_create(
            user=request.user, author=author)
        return Response(UserSubscribeSerializer(
            author, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def destroy(self, request, id=None):
        author = get_object_or_404(User, id=id)
        subscription = get_object_or_404(
            Subscription, user=request.user, author=author)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_user_data(self, user, request):
        user_data = UserSubscribeSerializer(
            user, context={'request': request}).data
        recipes = Recipe.objects.filter(user=user).values(
            'id', 'name', 'image', 'cooking_time')
        user_data['recipes'] = list(recipes)
        return user_data


class SubscriptionListViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LimitOffsetPagination

    def list(self, request):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user).select_related(
            'author'
        )
        authors = [subscription.author for subscription in subscriptions]
        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = UserSubscribeSerializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = UserSubscribeSerializer(
            authors, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_paginated_response(self, data):
        return Response({
            'count': self.paginator.page.paginator.count,
            'next': self.paginator.get_next_link(),
            'previous': self.paginator.get_previous_link(),
            'results': data
        })
