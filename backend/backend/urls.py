from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (UserViewSet, RecipeViewSet,
                       TagViewSet, IngredientViewSet)
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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router_v1.urls)),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
