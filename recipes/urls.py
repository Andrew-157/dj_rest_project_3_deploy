from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from recipes import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'recipes', views.RecipeViewSet, basename='recipe')
router.register(r'authors', views.AuthorViewSet, basename='author')

recipes_router = routers.NestedSimpleRouter(
    router, r'recipes', lookup='recipe'
)
recipes_router.register(
    r'ingredients', views.IngredientViewSet, basename='recipe-ingredient'
)
recipes_router.register(
    r'images', views.RecipeImageViewSet, basename='recipe-image'
)
recipes_router.register(
    r'reviews', views.ReviewViewSet, basename='recipe-review'
)

recipes_router.register(
    r'ratings', views.RatingViewSet, basename='recipe-rating'
)


urlpatterns = [
    path('', include(router.urls)),
    path('', include(recipes_router.urls))
]
