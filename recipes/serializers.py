from django.db.models import Avg
from rest_framework import serializers
from rest_framework_nested.relations import NestedHyperlinkedIdentityField, NestedHyperlinkedRelatedField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from recipes.models import Category, Recipe, Ingredient, RecipeImage, Review, Rating
from users.models import CustomUser


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    get_recipes = serializers.HyperlinkedIdentityField(
        view_name='category-get-recipes', read_only=True
    )

    class Meta:
        model = Category
        fields = ['url', 'id', 'title', 'slug', 'get_recipes']


class RecipeSerializer(serializers.HyperlinkedModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author = serializers.HyperlinkedRelatedField(view_name='author-detail',
                                                 read_only=True)
    category_title = serializers.ReadOnlyField(source='category.title')
    category = serializers.HyperlinkedRelatedField(view_name='category-detail',
                                                   read_only=True)
    get_ingredients = serializers.HyperlinkedIdentityField(
        view_name='recipe-get-ingredients', read_only=True
    )

    get_reviews = serializers.HyperlinkedIdentityField(
        view_name='recipe-get-reviews', read_only=True
    )

    get_ratings = serializers.HyperlinkedIdentityField(
        view_name='recipe-get-ratings', read_only=True
    )

    get_average_rating = serializers.HyperlinkedIdentityField(
        view_name='recipe-get-average-rating', read_only=True
    )

    get_images = serializers.HyperlinkedIdentityField(
        view_name='recipe-get-images', read_only=True
    )

    class Meta:
        model = Recipe
        fields = ['url', 'id', 'title', 'slug',
                  'instructions', 'published', 'updated',
                  'author_name', 'author',
                  'category_title', 'category',
                  'get_ingredients', 'get_reviews',
                  'get_ratings', 'get_average_rating',
                  'get_images']


class CreateUpdateRecipeSerializer(serializers.HyperlinkedModelSerializer):
    category_title = serializers.ReadOnlyField(source='category.title')

    class Meta:
        model = Recipe
        fields = ['url', 'id', 'title', 'instructions', 'published', 'updated',
                  'category_title', 'category']


class IngredientSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='recipe-ingredient-detail',
        lookup_field='pk',
        parent_lookup_kwargs={
            'recipe_pk': 'recipe__pk'
        }
    )
    recipe_title = serializers.ReadOnlyField(source='recipe.title')
    recipe = serializers.HyperlinkedRelatedField(
        view_name='recipe-detail', read_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'url', 'id', 'name', 'slug', 'quantity',
            'units_of_measurement', 'recipe_title',
            'recipe', 'ingredient_with_quantity'
        ]

    ingredient_with_quantity = serializers.SerializerMethodField(
        method_name='ingredient_repr'
    )

    def ingredient_repr(self, ingredient: Ingredient):
        if ingredient.units_of_measurement:
            return f'{ingredient.quantity} {ingredient.units_of_measurement} of {ingredient.name}'
        else:
            return f'{ingredient.quantity} {ingredient.name}'


class CreateUpdateIngredientSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='recipe-ingredient-detail',
        lookup_field='pk',
        parent_lookup_kwargs={
            'recipe_pk': 'recipe__pk'
        }
    )

    recipe_title = serializers.ReadOnlyField(source='recipe.title')
    recipe = serializers.HyperlinkedRelatedField(
        view_name='recipe-detail', read_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'url', 'id', 'name', 'quantity',
            'units_of_measurement', 'recipe_title', 'recipe'
        ]


class RecipeImageSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='recipe-image-detail',
        lookup_field='pk',
        parent_lookup_kwargs={
            'recipe_pk': 'recipe__pk'
        }
    )

    recipe_title = serializers.ReadOnlyField(source='recipe.title')
    recipe = serializers.HyperlinkedRelatedField(
        view_name='recipe-detail', read_only=True
    )

    class Meta:
        model = RecipeImage
        fields = [
            'url', 'id', 'image', 'recipe_title', 'recipe'
        ]


class ReviewSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='recipe-review-detail',
        lookup_field='pk',
        parent_lookup_kwargs={
            'recipe_pk': 'recipe__pk'
        }
    )

    recipe_title = serializers.ReadOnlyField(source='recipe.title')
    recipe = serializers.HyperlinkedRelatedField(
        view_name='recipe-detail', read_only=True
    )
    author_name = serializers.ReadOnlyField(source='author.username')
    author = serializers.HyperlinkedRelatedField(
        view_name='author-detail', read_only=True
    )

    class Meta:
        model = Review
        fields = [
            'url', 'id', 'content', 'author_name', 'author',
            'published', 'updated', 'recipe_title', 'recipe',
        ]


class RatingSerializer(NestedHyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='recipe-rating-detail',
        lookup_field='pk',
        parent_lookup_kwargs={
            'recipe_pk': 'recipe__pk'
        }
    )

    recipe_title = serializers.ReadOnlyField(source='recipe.title')
    recipe = serializers.HyperlinkedRelatedField(
        view_name='recipe-detail', read_only=True
    )
    author_name = serializers.ReadOnlyField(source='author.username')
    author = serializers.HyperlinkedRelatedField(
        view_name='author-detail', read_only=True
    )

    class Meta:
        model = Rating
        fields = [
            'url', 'id', 'value', 'author_name', 'author',
            'published', 'updated', 'recipe_title', 'recipe'
        ]


class AuthorSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='author-detail', read_only=True)

    get_recipes = serializers.HyperlinkedIdentityField(
        view_name='author-get-recipes', read_only=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'url', 'id', 'username', 'image', 'get_recipes'
        ]
