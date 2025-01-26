from django.conf import settings 
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from recipes.views import redirect_to_recipe

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('s/<str:code>/', redirect_to_recipe,
         name='redirect-to-recipe'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
