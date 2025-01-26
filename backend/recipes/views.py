from django.shortcuts import get_object_or_404, redirect

from backend.recipes.models import ShortLink

def redirect_to_recipe(request, code): 
    return redirect(get_object_or_404(ShortLink, short_code=code).original_url)
