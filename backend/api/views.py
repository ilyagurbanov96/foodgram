import os
import tempfile

from djoser.views import UserViewSet as DjoserUser
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, ShortLink, Tag)
from users.models import Subscription, User
from .filters import IngredientFilter, RecipeFilter
from .paginations import ApiPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeCreateSerializer, RecipeGetSerializer,
                          ShoppingCartSerializer, FavoriteSerializer,
                          TagSerializer, UserProfileSerializer,
                          SubscriptionCreateSerializer, SubscriptionGetSerializer,)


class UserViewSet(DjoserUser):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = LimitOffsetPagination


    def retrieve(self, request, pk=None):
        if pk == 'me':
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)
        user = get_object_or_404(User, pk=pk)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)


    @action(
        detail=False,
        methods=('put',),
        url_path='me/avatar',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def avatar(self, request):
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
    
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return Response({"detail": "Аватар успешно удален."}, status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Аватар не найден."}, status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=True,
        methods=('post',),
        url_path='subscribe',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscribe(self, request, pk):
        author = self.get_object()
        user = request.user
        serializer = SubscriptionCreateSerializer(data={'user': user.id, 'author': author.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Вы успешно подписались на автора.'}, status=status.HTTP_201_CREATED)
    
    @subscribe.mapping.delete
    def unsubscribe(self, request, pk):
        author = self.get_object()
        user = request.user
        subscription = Subscription.objects.filter(user=user, author=author).first()
        if subscription:
            subscription.delete()
            return Response({'detail': 'Вы успешно отписались от автора.'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Вы не подписаны на этого автора.'}, status=status.HTTP_400_BAD_REQUEST)
        

    @action(
        detail=False,
        methods=('get',),
        url_path='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        authors = User.objects.filter(subscribers__user=request.user)
        authors = authors.annotate(recipe_count=Count('recipes'))
        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionGetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionGetSerializer(authors, many=True)
        return Response(serializer.data)
    

def create_entry(serializer_class, user, recipe_pk, context=None):
    recipe = get_object_or_404(Recipe, pk=recipe_pk)
    data = {
        'user': user.id,
        'recipe': recipe.id
    }
    serializer = serializer_class(data=data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related('tags', 'ingredients')
    permission_classes = (IsAuthorOrReadOnly,
                          permissions.IsAuthenticatedOrReadOnly)
    pagination_class = ApiPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeGetSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'get'),
        url_path='get-link'
    )
    def get_link(self, request, pk=None): 
        url = request.build_absolute_uri(reverse('recipe-detail', args=[pk]))
        short_link, created = ShortLink.objects.get_or_create(original_url=url)
        base_url = request.build_absolute_uri('/s/').rstrip('/')
        return Response({'short-link': f'{base_url}/{short_link.short_code}'})

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return create_entry(ShoppingCartSerializer, request.user, pk, context={'request': request})
    
    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        shopping_cart = ShoppingCart.objects.filter(user=request.user, recipe_id=pk)
        if shopping_cart.exists():
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Рецепт не найден в корзине.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_carts__user=request.user
        ).values('ingredients__name', 'ingredients__measurement_unit'
        ).annotate(total_amount=Sum('amount')
        ).order_by('ingredients__name')
        ingredients_text = self.format_ingredients_text(ingredients)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(ingredients_text)
            temp_file_path = temp_file.name
        response = FileResponse(open(temp_file_path, 'rb'), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        response['X-Accel-Buffering'] = 'no'
        response['Content-Length'] = os.path.getsize(temp_file_path)
        os.remove(temp_file_path)
        return response
    
    @staticmethod
    def format_ingredients_text(ingredients):
        ingredients_text = "Список покупок:\n\n"
        for ingredient in ingredients:
            ingredient_name = ingredient['ingredients__name']
            measurement_unit = ingredient['ingredients__measurement_unit']
            total_amount = ingredient['total_amount']
            ingredients_text += f"{ingredient_name} ({measurement_unit}) - {total_amount}\n"
        return ingredients_text

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        return create_entry(FavoriteSerializer, request.user, pk, context={'request': request})
    
    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        favorite = Favorite.objects.filter(user=request.user, recipe_id=pk)
        if favorite.exists():
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Рецепт не найден в избранном.'}, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None
