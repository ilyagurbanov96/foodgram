from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from recipes.views import redirect_to_recipe

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('s/<str:code>/', redirect_to_recipe,
         name='redirect-to-recipe'),
    path(
        'redoc/',
        TemplateView.as_view(template_name='redoc.html'),
        name='redoc'
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
