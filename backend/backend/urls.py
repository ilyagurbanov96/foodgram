from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (UserViewSet, RecipeViewSet,
                       TagViewSet, IngredientViewSet,
                       SubscriptionViewSet, SubscriptionListViewSet)
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
router_v1.register(r'users/subscriptions', SubscriptionListViewSet,
                   basename='subscriptionslist')
router_v1.register(r'users/(?P<id>\d+)/subscribe', SubscriptionViewSet,
                   basename='subscription')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router_v1.urls)),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/recipes/<int:pk>/get-link/', RecipeViewSet.as_view(
        {'post': 'create_short_link', 'get': 'create_short_link'}),
        name='get-link'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
