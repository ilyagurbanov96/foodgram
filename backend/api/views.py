from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from recipes.models import (User, Recipe, Tag, Ingredient,
                            Favorite, ShoppingCart, Subscription)
from .serializers import (UserSerializer, RecipeSerializer,
                          TagSerializer, IngredientSerializer,
                          FavoriteSerializer, ShoppingCartSerializer,
                          SubscriptionSerializer, SubscribeSerializer)
from .permissions import IsAuthorOrReadOnly
from rest_framework.pagination import (LimitOffsetPagination,
                                       PageNumberPagination)
from collections import defaultdict


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = PageNumberPagination


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthorOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)


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
