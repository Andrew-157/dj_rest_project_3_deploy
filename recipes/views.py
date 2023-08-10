from django.db.models import Avg
from django.db.models.query_utils import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework import filters
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, MethodNotAllowed, ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, SAFE_METHODS
from recipes.models import Category, Recipe, Ingredient, RecipeImage, Review, Rating
from recipes.serializers import CategorySerializer, RecipeSerializer, CreateUpdateRecipeSerializer,\
    IngredientSerializer, CreateUpdateIngredientSerializer, RecipeImageSerializer, ReviewSerializer,\
    RatingSerializer, AuthorSerializer
from recipes.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly, IsRecipeAuthorOrReadOnly, \
    NestedIsAuthenticatedOrReadOnly, NestedIsAuthorOrReadOnly
from recipes.exceptions import ConflictException
from users.models import CustomUser


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'slug']
    ordering_fields = ['title', 'slug']

    def destroy(self, request, *args, **kwargs):
        if Recipe.objects.filter(category_id=self.kwargs['pk']):
            raise ConflictException(method='DELETE',
                                    detail='Category has recipes associated with it, cannot be deleted.')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['GET', 'HEAD', 'OPTIONS'])
    def get_recipes(self, request, *args, **kwargs):
        category = self.get_object()
        recipes = Recipe.objects.\
            select_related('category', 'author').\
            filter(category=category).all()
        if request.method == 'GET':
            serializer = RecipeSerializer(
                recipes, many=True, context={'request': request})
            return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author', 'category').all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'slug', 'instructions',
                     'category__title', 'author__username']
    ordering_fields = ['title', 'slug', 'category__title', 'author__username']

    def perform_create(self, serializer):
        serializer.save(author_id=self.request.user.id)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        else:
            return CreateUpdateRecipeSerializer

    @action(detail=True, methods=['GET', 'HEAD', 'OPTIONS'])
    def get_ingredients(self, request, *args, **kwargs):
        recipe = self.get_object()
        ingredients = Ingredient.objects.\
            select_related('recipe').filter(
                recipe=recipe).all()
        if request.method == 'GET':
            serializer = IngredientSerializer(ingredients,
                                              many=True,
                                              context={'request': request})
            return Response(serializer.data)

    @action(detail=True,  methods=['GET', 'HEAD', 'OPTIONS'])
    def get_reviews(self, request, *args, **kwargs):
        recipe = self.get_object()
        reviews = Review.objects.\
            select_related('recipe', 'author').filter(
                recipe=recipe
            ).all()
        if request.method == 'GET':
            serializer = ReviewSerializer(
                reviews, many=True,
                context={'request': request}
            )
            return Response(serializer.data)

    @action(detail=True, methods=['GET', 'HEAD', 'OPTIONS'])
    def get_ratings(self, request, *args, **kwargs):
        recipe = self.get_object()
        ratings = Rating.objects.\
            filter(recipe=recipe).select_related('author', 'recipe').all()
        if request.method == 'GET':
            serializer = RatingSerializer(
                ratings, many=True,
                context={'request': request}
            )
            return Response(serializer.data)

    @action(detail=True,  methods=['GET', 'HEAD', 'OPTIONS'])
    def get_average_rating(self, request, *args, **kwargs):
        recipe = self.get_object()
        if request.method == 'GET':
            average_rating = Rating.objects.\
                filter(recipe=recipe).aggregate(avg_rating=Avg('value'))
            return Response(average_rating)

    @action(detail=True,  methods=['GET', 'HEAD', 'OPTIONS'])
    def get_images(self, request, *args, **kwargs):
        recipe = self.get_object()
        images = RecipeImage.objects.\
            select_related('recipe').\
            filter(recipe=recipe).all()
        if request.method == 'GET':
            serializer = RecipeImageSerializer(
                images, many=True,
                context={'request': request}
            )
            return Response(serializer.data)


class IngredientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRecipeAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name, slug']
    ordering_fields = ['name', 'slug']

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return IngredientSerializer
        else:
            return CreateUpdateIngredientSerializer

    def get_queryset(self):
        return Ingredient.objects.\
            select_related('recipe', 'recipe__author').\
            filter(recipe__id=self.kwargs['recipe_pk']).all()

    def perform_create(self, serializer):
        ingredient_name = str(self.request.data['name']).lower()
        ingredient = Ingredient.objects.filter(
            Q(name=ingredient_name) &
            Q(recipe__id=self.kwargs['recipe_pk'])
        ).first()
        if ingredient:
            raise ValidationError(
                detail=f"Ingredient with name '{ingredient_name}' already exists for this recipe.")
        serializer.save(recipe_id=self.kwargs['recipe_pk'])

    def perform_update(self, serializer):
        ingredient = self.get_object()
        ingredient_name = str(self.request.data['name']).lower()
        ingredient_with_name = Ingredient.objects.filter(
            Q(recipe__id=self.kwargs['recipe_pk']) &
            Q(name=ingredient_name)
        ).first()
        if ingredient_with_name and (ingredient_with_name != ingredient):
            raise ValidationError(detail=f"Ingredient with name '{ingredient_name}' already exists\
                                    for this recipe.")
        return super().perform_update(serializer)


class RecipeImageViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.CreateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = RecipeImageSerializer
    permission_classes = [IsRecipeAuthorOrReadOnly]

    def get_queryset(self):
        return RecipeImage.objects.\
            select_related('recipe', 'recipe__author').\
            filter(recipe__id=self.kwargs['recipe_pk']).all()

    def perform_create(self, serializer):
        recipe_pk = self.kwargs['recipe_pk']
        number_of_images = RecipeImage.objects.filter(
            recipe__id=recipe_pk
        ).count()
        max_number_of_images = 3
        if number_of_images == max_number_of_images:
            raise ValidationError(
                detail=f"More than {max_number_of_images} images cannot be posted for one recipe."
            )
        else:
            serializer.save(recipe_id=self.kwargs['recipe_pk'])


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [
        NestedIsAuthenticatedOrReadOnly, NestedIsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['author__username', 'content']
    ordering_fields = ['author__username', 'content', 'published']

    def get_queryset(self):
        recipe_pk = self.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_pk).first()
        return Review.objects.select_related('recipe', 'author').\
            filter(recipe=recipe).all()

    def perform_create(self, serializer):
        recipe_pk = self.kwargs['recipe_pk']
        user_pk = self.request.user.id
        review = Review.objects.filter(
            Q(author__id=user_pk) &
            Q(recipe__id=recipe_pk)
        ).first()
        if review:
            raise ConflictException(
                method='POST',
                detail='User can only have one review for each recipe.'
            )
        serializer.save(
            recipe_id=recipe_pk,
            author_id=user_pk
        )


class RatingViewSet(viewsets.ModelViewSet):
    serializer_class = RatingSerializer
    permission_classes = [
        NestedIsAuthenticatedOrReadOnly, NestedIsAuthorOrReadOnly]

    def get_queryset(self):
        recipe_pk = self.kwargs['recipe_pk']
        recipe = Recipe.objects.filter(id=recipe_pk).first()
        return Rating.objects.select_related('recipe', 'author').\
            filter(recipe=recipe).all()

    def perform_create(self, serializer):
        recipe_pk = self.kwargs['recipe_pk']
        user_pk = self.request.user.id
        rating = Rating.objects.filter(
            Q(author__id=user_pk) &
            Q(recipe__id=recipe_pk)
        ).first()
        if rating:
            raise ConflictException(
                method='POST',
                detail='User can only have one rating for each recipe.'
            )
        serializer.save(
            recipe_id=recipe_pk,
            author_id=user_pk
        )


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.filter(is_superuser=False).all()
    serializer_class = AuthorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    searching_fields = ['username']
    ordering_fields = ['username']

    @action(detail=True, methods=['GET', 'OPTIONS', 'HEAD'])
    def get_recipes(self, request, *args, **kwargs):
        author = self.get_object()
        recipes = Recipe.objects.select_related('category', 'author').\
            filter(author=author).all()
        if request.method == 'GET':
            serializer = RecipeSerializer(recipes, many=True,
                                          context={'request': request})
            return Response(serializer.data)
