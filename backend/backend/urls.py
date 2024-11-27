from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (UserViewSet, RecipeViewSet,
                       TagViewSet, IngredientViewSet,
                       FavoriteViewSet, ShoppingCartViewSet,
                       SubscribeView, SubscriptionListView)
from django.conf.urls.static import static
from django.conf import settings


router_v1 = DefaultRouter()

router_v1.register(r'users', UserViewSet,
                   basename='user')
router_v1.register(r'recipes', RecipeViewSet,
                   basename='recipe')
router_v1.register(r'tags', TagViewSet,
                   basename='tag')
router_v1.register(r'ingredients', IngredientViewSet,
                   basename='ingredient')
router_v1.register(r'recipes/(\d+)/favorite/$', FavoriteViewSet,  # неправильно
                   basename='favorite')
router_v1.register(r'recipes/(\d+)/shopping_cart/$', ShoppingCartViewSet,
                   basename='shopping-list')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router_v1.urls)),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/recipes/download_shopping_cart/', ShoppingCartViewSet.as_view(
        {'get': 'download'}), name='download_shopping_cart'),
    path('api/users/<int:id>/subscribe/', SubscribeView.as_view(),
         name='subscribe'),
    path('api/users/subscriptions/', SubscriptionListView.as_view(),
         name='user-subscriptions'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
