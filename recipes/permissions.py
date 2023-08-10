from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import NotFound
from recipes.models import Recipe, Ingredient


class IsAdminOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_superuser


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user


class NestedIsAuthenticatedOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        recipe_id = view.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_id).first()
        if not recipe:
            raise NotFound(
                detail=f"Recipe with id {recipe_id} was not found.")
        if request.method in SAFE_METHODS:
            return True
        else:
            return request.user.is_authenticated


class NestedIsAuthorOrReadOnly(BasePermission):

    def has_object_permission(self, request, view, obj):
        recipe_id = view.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_id).first()
        if not recipe:
            raise NotFound(detail=f"Recipe with id {recipe_id} was not found.")
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user


class IsRecipeAuthorOrReadOnly(BasePermission):
    # Permission to check that only user that created Recipe
    # can create, update or delete objects that reference that recipe
    def has_permission(self, request, view):
        # If recipe that is referenced in url does not exist,
        # then it does not matter if user is authenticated or not
        recipe_id = view.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_id).first()
        if not recipe:
            raise NotFound(
                detail=f"Recipe with id {recipe_id} was not found.")
        if request.method in SAFE_METHODS:
            return True
        return recipe.author == request.user

    def has_object_permission(self, request, view, obj: Ingredient):
        # If recipe that is referenced in url does not exist,
        # then it does not matter if user is authenticated or not
        recipe_id = view.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_id).first()
        if not recipe:
            raise NotFound(
                detail=f"Recipe with id {recipe_id} was not found.")
        if request.method in SAFE_METHODS:
            return True
        return obj.recipe.author == request.user
