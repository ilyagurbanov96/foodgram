from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeViewSet,
                    TagViewSet, UserViewSet)

router_v1 = DefaultRouter()

router_v1.register(r'users', UserViewSet,
                   basename='user')
router_v1.register(r'recipes', RecipeViewSet,
                   basename='recipe')
router_v1.register(r'tags', TagViewSet,
                   basename='tag')
router_v1.register(r'ingredients', IngredientViewSet,
                   basename='ingredient')


urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
