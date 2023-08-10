from typing import Any
from django.contrib import admin
from django.db.models import Avg, Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils.html import format_html
from recipes.models import Recipe, RecipeImage, Rating, Review, Category, Ingredient


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'slug',
    ]
    list_filter = [
        'title', 'slug'
    ]
    search_fields = [
        'title', 'slug'
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'instructions', 'slug',
        'category', 'author', 'published'
    ]

    list_filter = [
        'category', 'published', 'author', 'title', 'slug'
    ]
    search_fields = [
        'title', 'instructions'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).\
            select_related('category', 'author')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'name', 'slug',
                    'quantity', 'units_of_measurement',]

    list_filter = ['recipe', 'name', 'slug',
                   'quantity', 'units_of_measurement']

    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).\
            select_related('recipe')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'recipe', 'author', 'content', 'published'
    ]
    list_filter = [
        'recipe', 'author', 'published'
    ]
    search_fields = [
        'content'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).\
            select_related('author', 'recipe')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = [
        'recipe', 'author', 'value', 'published'
    ]
    list_filter = [
        'recipe', 'author', 'published', 'value'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).\
            select_related('author', 'recipe')


@admin.register(RecipeImage)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = [
        'recipe', 'image_tag'
    ]
    list_filter = [
        'recipe'
    ]
    readonly_fields = ['image']

    def image_tag(self, obj):
        return format_html(f'<img src="{obj.image.url}" width="50" height="50">')

    image_tag.short_description = 'Recipe image'
