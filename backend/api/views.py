from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from recipes.models import (User, Recipe, Tag, Ingredient,
                            Favorite, ShoppingCart, Subscription,
                            RecipeIngredient, ShortLink)
from .serializers import (UserSerializer, RecipeSerializer,
                          TagSerializer, IngredientSerializer,
                          FavoriteSerializer, ShoppingCartSerializer,
                          SubscriptionSerializer, SubscribeSerializer,
                          ShortLinkSerializer)
from .permissions import IsAuthorOrReadOnly
from .filters import IngredientFilter, RecipeFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import action
from collections import defaultdict
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = LimitOffsetPagination

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['put'], url_path='me/avatar')
    def update_avatar(self, request):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_data = {
                'avatar': user.avatar.url if user.avatar else None,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return self.queryset.filter(id=self.request.user.id)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)


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

    @action(detail=True, methods=['post'], url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'error': 'Рецепт уже в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)
        Favorite.objects.create(user=user, recipe=recipe)
        return Response({'status': 'рецепт добавлен в избранное'},
                        status=status.HTTP_201_CREATED)

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
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не найден.'},
                            status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if created:
            return Response(FavoriteSerializer(favorite).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Рецепт уже в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        try:
            favorite = Favorite.objects.get(user=request.user,
                                            recipe_id=recipe_id)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'detail': 'Избранное не найдено.'},
                            status=status.HTTP_404_NOT_FOUND)


class ShortLinkViewSet(viewsets.ViewSet):
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


class ShoppingCartViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingCartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не найден.'}, status=404)

        shopping_cart_item, created = ShoppingCart.objects.get_or_create(
            user=request.user, recipe=recipe)
        if created:
            return Response(ShoppingCartSerializer(shopping_cart_item).data,
                            status=201)
        else:
            return Response({'detail': 'Рецепт уже в списке покупок.'},
                            status=400)

    def destroy(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        try:
            shopping_cart_item = ShoppingCart.objects.get(user=request.user,
                                                          recipe_id=recipe_id)
            shopping_cart_item.delete()
            return Response(status=204)
        except ShoppingCart.DoesNotExist:
            return Response({'detail': 'Товар в корзине не найден.'},
                            status=404)

    def download(self, request):
        shopping_items = self.get_queryset()
        ingredients = defaultdict(int)

        for item in shopping_items:
            for ingredient in item.recipe.ingredients:
                ingredients[ingredient['name']] += ingredient['amount']

        response = Response(content_type='text/plain')
        response['Content-Disposition'] = '''attachment;
        filename="shopping_cart.txt"'''

        for name, amount in ingredients.items():
            response.write(f"{name} — {amount}\n")

        return response


class SubscribeView(generics.CreateAPIView):
    serializer_class = SubscribeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        author_id = self.request.data.get('author')
        user = self.request.user

        if Subscription.objects.filter(user=user,
                                       author_id=author_id).exists():
            return Response({
                "detail": "Вы уже подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST)

        serializer.save(user=user, author_id=author_id)


class SubscriptionListView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Subscription.objects.filter(user=user)
