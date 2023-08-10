import os
import tempfile
from PIL import Image
from io import BytesIO
from django.db.models import Avg
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import ErrorDetail
from recipes.models import Category, Recipe, Ingredient, RecipeImage, Review, Rating
from users.models import CustomUser


class CategoriesTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@gmail.com',
            password='34somepassword34',
            is_staff=True,
            is_superuser=True)
        user = CustomUser.objects.create_user(
            username='test_user',
            email='test_user@gmail.com',
            password='34somepassword34'
        )

        Category.objects.create(
            title='Soups',
            slug='soups'
        )

        Category.objects.create(
            title='Desserts',
            slug='desserts'
        )

        Category.objects.create(
            title='Snacks',
            slug='snacks'
        )

    # GET list
    def test_get_category_list(self):
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # GET detail
    def test_get_category_detail(self):
        test_server_prefix = 'http://testserver'
        category = Category.objects.filter(title='Soups').first()
        url = reverse('category-detail', kwargs={'pk': category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {'url': test_server_prefix + reverse('category-detail', kwargs={'pk': category.id}),
                         'id': category.id,
                         'title': category.title,
                         'slug': category.slug,
                         'get_recipes': test_server_prefix + reverse('category-get-recipes', kwargs={'pk': category.id})}
        self.assertEqual(response.data, expected_data)

    def test_get_nonexistent_category(self):
        url = reverse('category-detail', kwargs={'pk': 56})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_recipes_of_category_detail(self):
        category = Category.objects.filter(title='Soups').first()
        user = CustomUser.objects.filter(username='test_user').first()
        recipe_1 = Recipe.objects.create(category=category,
                                         author=user,
                                         title='Soup 1',
                                         instructions='Cook soup 1')
        recipe_2 = Recipe.objects.create(category=category,
                                         author=user,
                                         title='Soup 2',
                                         instructions='Cook soup 2')
        url = reverse('category-get-recipes', kwargs={'pk': category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipes_count_in_category = Recipe.objects.filter(
            category=category).count()
        self.assertEqual(len(response.data), recipes_count_in_category)

    def test_get_detail_of_nonexistent_category(self):
        url = reverse('category-detail', kwargs={'pk': 78})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # POST
    def test_admin_posts_category_with_not_unique_title_or_slug(self):
        category = Category.objects.filter(title='Soups').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-list')
        response = self.client.post(url, data={'title': category.title,
                                               'slug': category.slug},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_posts_category_with_empty_body(self):
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-list')
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_posts_category_with_no_body(self):
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-list')
        response = self.client.post(url, data=None, format='json')
        self.assertEqual(response.status_code, 400)

    def test_admin_posts_new_category(self):
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-list')
        response = self.client.post(url, data={'title': 'Pasta and Rissoto',
                                               'slug': 'pasta-and-rissoto'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_server_prefix = 'http://testserver'
        new_category = Category.objects.filter(
            title='Pasta and Rissoto').first()
        self.assertTrue(new_category is not None)
        expected_data = {'url': test_server_prefix + reverse('category-detail', kwargs={'pk': new_category.id}),
                         'id': new_category.id,
                         'title': new_category.title,
                         'slug': new_category.slug,
                         'get_recipes': test_server_prefix + reverse('category-get-recipes', kwargs={'pk': new_category.id})}
        self.assertEqual(response.data, expected_data)

    def test_not_admin_logged_user_posts_new_category(self):
        user = CustomUser.objects.filter(username='test_user').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-list')
        response = self.client.post(url, data={'title': 'New category',
                                               'slug': 'new-category'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_posts_new_category(self):
        url = reverse('category-list')
        response = self.client.post(url, data={'title': 'New category',
                                               'slug': 'new-category'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # PUT
    def test_admin_updates_category_with_not_unique_title_or_slug(self):
        category_to_update = Category.objects.filter(title='Soups').first()
        existing_category = Category.objects.filter(title='Desserts').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category_to_update.id})
        response = self.client.put(url, data={'title': existing_category.title,
                                              'slug': existing_category.slug}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_updates_category_with_empty_body(self):
        category_to_update = Category.objects.filter(title='Soups').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category_to_update.id})
        response = self.client.put(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_updates_category_with_no_body(self):
        category_to_update = Category.objects.filter(title='Soups').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category_to_update.id})
        response = self.client.put(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_updates_category(self):
        category_to_update = Category.objects.filter(title='Soups').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category_to_update.id})
        response = self.client.put(url, data={'title': 'Soups and Stews',
                                              'slug': 'soups-and-stews'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_category = Category.objects.filter(
            title='Soups and Stews').first()
        self.assertTrue(updated_category is not None)
        test_server_prefix = 'http://testserver'
        expected_data = {'url': test_server_prefix + reverse('category-detail', kwargs={'pk': updated_category.id}),
                         'id': updated_category.id,
                         'title': updated_category.title,
                         'slug': updated_category.slug,
                         'get_recipes': test_server_prefix + reverse('category-get-recipes', kwargs={'pk': updated_category.id})}
        self.assertEqual(response.data, expected_data)

    def test_admin_updates_nonexistent_category(self):
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': 67})
        response = self.client.put(url, data={'title': 'Soups and Stews',
                                              'slug': 'soups-and-stews'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_admin_logged_user_updates_category(self):
        user = CustomUser.objects.filter(username='test_user').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': 67})
        response = self.client.put(url, data={'title': 'Soups and Stews',
                                              'slug': 'soups-and-stews'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_updates_category(self):
        category = Category.objects.get(title='Soups')
        url = reverse('category-detail', kwargs={'pk': 67})
        response = self.client.put(url, data={'title': 'Soups and Stews',
                                              'slug': 'soups-and-stews'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_admin_deletes_nonexistent_category(self):
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': 67})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_deletes_category_with_associated_recipes(self):
        user = CustomUser.objects.filter(username='test_user').first()
        category = Category.objects.filter(title='Soups').first()
        recipe = Recipe.objects.create(
            author=user,
            category=category,
            title='Some random recipe',
            instructions='Follow instructions'
        )
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['detail'],
                         'Category has recipes associated with it, cannot be deleted.')

    def test_admin_deletes_category(self):
        category = Category.objects.filter(title='Soups').first()
        admin = CustomUser.objects.filter(username='admin').first()
        token = AccessToken.for_user(admin)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': category.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_not_admin_logged_user_deletes_category(self):
        user = CustomUser.objects.filter(username='test_user').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('category-detail', kwargs={'pk': 673})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_deletes_category(self):
        url = reverse('category-detail', kwargs={'pk': 673})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RecipesTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user_1 = CustomUser.objects.\
            create_user(username='user1',
                        email='user1@gmail.com',
                        password='34somepassword34')
        test_user_2 = CustomUser.objects.\
            create_user(username='user2',
                        email='user2@gmail.com',
                        password='34somepassword34')

        category_1 = Category.objects.create(
            title='Pasta',
            slug='pasta'
        )

        Recipe.objects.create(
            author=test_user_1,
            category=category_1,
            title='Pasta 1',
            instructions='Cook pasta 1'
        )

    # GET list
    def test_get_recipe_list(self):
        url = reverse('recipe-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # GET detail
    def test_get_recipe_detail(self):
        test_server_prefix = 'http://testserver'
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {'url': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id}),
                         'id': recipe.id,
                         'title': recipe.title,
                         'slug': recipe.slug,
                         'instructions': recipe.instructions,
                         'published': recipe.published.replace(tzinfo=None).isoformat() + 'Z',
                         'updated': recipe.updated.replace(tzinfo=None).isoformat() + 'Z',
                         'author_name': recipe.author.username,
                         'author': test_server_prefix + reverse('author-detail', kwargs={'pk': recipe.author.id}),
                         'category_title': recipe.category.title,
                         'category': test_server_prefix + reverse('category-detail',
                                                                  kwargs={'pk': recipe.category.id}),
                         'get_ingredients': test_server_prefix + reverse('recipe-get-ingredients',
                                                                         kwargs={'pk': recipe.id}),
                         'get_reviews': test_server_prefix + reverse('recipe-get-reviews',
                                                                     kwargs={'pk': recipe.id}),
                         'get_ratings': test_server_prefix + reverse('recipe-get-ratings',
                                                                     kwargs={'pk': recipe.id}),
                         'get_average_rating': test_server_prefix + reverse('recipe-get-average-rating',
                                                                            kwargs={'pk': recipe.id}),
                         'get_images': test_server_prefix + reverse('recipe-get-images',
                                                                    kwargs={'pk': recipe.id})}
        self.assertEqual(response.data, expected_data)

    def test_get_ingredients_of_recipe_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient_1 = Ingredient.objects.create(name='eggs',
                                                 quantity=2.00,
                                                 recipe=recipe)
        ingredient_2 = Ingredient.objects.create(name='cheese',
                                                 quantity='100.00',
                                                 units_of_measurement='gm',
                                                 recipe=recipe)
        url = reverse('recipe-get-ingredients', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ingredients_count_for_recipe = Ingredient.objects.filter(
            recipe=recipe).count()
        self.assertEqual(len(response.data), ingredients_count_for_recipe)

    def test_get_reviews_of_recipe_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user_1 = CustomUser.objects.filter(username='user1').first()
        user_2 = CustomUser.objects.filter(username='user2').first()
        review_1 = Review.objects.create(recipe=recipe, author=user_1,
                                         content='Recipe review 1')
        review_2 = Review.objects.create(recipe=recipe, author=user_2,
                                         content='Recipe review 2')
        url = reverse('recipe-get-reviews', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reviews_count_for_recipe = Review.objects.filter(
            recipe=recipe).count()
        self.assertEqual(len(response.data), reviews_count_for_recipe)

    def test_get_ratings_of_recipe_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user_1 = CustomUser.objects.filter(username='user1').first()
        user_2 = CustomUser.objects.filter(username='user2').first()
        rating_1 = Rating.objects.create(recipe=recipe, author=user_1,
                                         value=9)
        rating_2 = Rating.objects.create(recipe=recipe, author=user_2,
                                         value=8)
        url = reverse('recipe-get-ratings', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ratings_count_for_recipe = Rating.objects.filter(
            recipe=recipe).count()
        self.assertEqual(len(response.data), ratings_count_for_recipe)

    def test_get_average_rating_of_recipe_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user_1 = CustomUser.objects.filter(username='user1').first()
        user_2 = CustomUser.objects.filter(username='user2').first()
        rating_1 = Rating.objects.create(recipe=recipe, author=user_1,
                                         value=9)
        rating_2 = Rating.objects.create(recipe=recipe, author=user_2,
                                         value=8)
        url = reverse('recipe-get-average-rating', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        average_recipe_rating = Rating.objects.filter(
            recipe=recipe).aggregate(avg_rating=Avg('value'))
        self.assertEqual(response.data, average_recipe_rating)

    def test_get_images_of_recipe_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image_1 = RecipeImage.objects.create(recipe=recipe,
                                             image=tempfile.NamedTemporaryFile(suffix=".jpg").name)
        image_2 = RecipeImage.objects.create(recipe=recipe,
                                             image=tempfile.NamedTemporaryFile(suffix=".jpg").name)
        url = reverse('recipe-get-images', kwargs={'pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        images_count_for_recipe = RecipeImage.objects.filter(
            recipe=recipe).count()
        self.assertEqual(len(response.data), images_count_for_recipe)

    def test_get_nonexistent_recipe(self):
        url = reverse('recipe-detail', kwargs={'pk': 789})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # POST
    def test_logged_user_posts_recipe_with_not_valid_category(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-list')
        response = self.client.post(url, data={'title': 'Random recipe',
                                               'instructions': 'Cook recipe',
                                               'category': 'Not real category'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_recipe_with_empty_body(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-list')
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_recipe_with_no_body(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-list')
        response = self.client.post(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_recipe(self):
        category = Category.objects.filter(title='Pasta').first()
        category_url = reverse('category-detail', kwargs={'pk': category.id})
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-list')
        response = self.client.post(url, data={'title': 'Pasta 3',
                                               'instructions': 'Cook pasta 3',
                                               'category': category_url},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_server_prefix = 'http://testserver'
        recipe: Recipe = Recipe.objects.filter(title='Pasta 3').first()
        expected_data = {'url': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id}),
                         'id': recipe.id,
                         'title': recipe.title,
                         'instructions': recipe.instructions,
                         'published': recipe.published.replace(tzinfo=None).isoformat() + 'Z',
                         'updated': recipe.updated.replace(tzinfo=None).isoformat() + 'Z',
                         'category_title': recipe.category.title,
                         'category': test_server_prefix + reverse('category-detail', kwargs={'pk': category.id})}
        self.assertEqual(response.data, expected_data)

    def test_not_authorized_user_posts_recipe(self):
        url = reverse('recipe-list')
        response = self.client.post(url, data={'title': 'Some recipe',
                                               'instructions': 'Cook recipe',
                                               'category': 'Some category'},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # PUT
    def test_logged_user_updates_recipe_with_not_valid_category(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(author=user).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.put(url, data={'title': recipe.title,
                                              'instructions': recipe.instructions,
                                              'category': 'Some category'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_recipe_with_empty_body(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(author=user).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.put(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_recipe_with_no_body(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(author=user).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.put(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_without_permission_updates_recipe(self):
        user_1 = CustomUser.objects.filter(username='user1').first()
        user_2 = CustomUser.objects.filter(username='user2').first()
        user_1_recipe = Recipe.objects.filter(author=user_1).first()
        token = AccessToken.for_user(user_2)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': user_1_recipe.id})
        response = self.client.put(url, data={'title': user_1_recipe.title,
                                              'instructions': user_1_recipe.instructions,
                                              'category': user_1_recipe.category.title},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logged_user_updates_recipe(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        category_url = reverse(
            'category-detail', kwargs={'pk': recipe.category.id})
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.put(url, data={'title': 'Pasta 1 with cheese',
                                              'instructions': recipe.instructions,
                                              'category': category_url},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        recipe: Recipe = Recipe.objects.filter(
            title='Pasta 1 with cheese').first()
        expected_data = {'url': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id}),
                         'id': recipe.id,
                         'title': recipe.title,
                         'instructions': recipe.instructions,
                         'published': recipe.published.replace(tzinfo=None).isoformat() + 'Z',
                         'updated': recipe.updated.replace(tzinfo=None).isoformat() + 'Z',
                         'category_title': recipe.category.title,
                         'category': test_server_prefix + reverse('category-detail', kwargs={'pk': recipe.category.id})}
        self.assertEqual(response.data, expected_data)

    def test_logged_user_updates_nonexistent_recipe(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': 56})
        response = self.client.put(url, data={'title': 'Recipe',
                                              'instructions': 'Some instructions',
                                              'category': 'Some category'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_authorized_user_updates_recipe(self):
        url = reverse('recipe-detail', kwargs={'pk': 89})
        response = self.client.put(url, data={'title': 'Recipe',
                                              'instructions': 'Some instructions',
                                              'category': 'Some category'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_logged_user_deletes_nonexistent_recipe(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': 78})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_logged_user_without_permission_deletes_recipe(self):
        user_1 = CustomUser.objects.filter(username='user1').first()
        user_2 = CustomUser.objects.filter(username='user2').first()
        user_1_recipe = Recipe.objects.filter(author=user_1).first()
        token = AccessToken.for_user(user_2)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': user_1_recipe.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logged_user_deletes_recipe(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(author=user).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_not_authorized_user_deletes_recipe(self):
        url = reverse('recipe-detail', kwargs={'pk': 45})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IngredientsTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user_1 = CustomUser.objects.create_user(username='user1',
                                                     email='user1@gmail.com',
                                                     password='34somepassword34')
        test_user_2 = CustomUser.objects.create_user(username='user2',
                                                     email='user2@gmail.com',
                                                     password='34somepassword34')

        category = Category.objects.create(title='Pasta',
                                           slug='pasta')
        recipe = Recipe.objects.create(author=test_user_1,
                                       category=category,
                                       title='Pasta 1',
                                       instructions='Cook pasta')
        ingredient_1 = Ingredient.objects.create(recipe=recipe,
                                                 name='eggs',
                                                 quantity=3)
        ingredient_2 = Ingredient.objects.create(recipe=recipe,
                                                 name='cheese',
                                                 quantity=500,
                                                 units_of_measurement='gm')

    # GET list
    def test_get_ingredient_list(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_ingredient_list_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 78
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': nonexistent_recipe_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f"Recipe with id {nonexistent_recipe_id} was not found."
        self.assertEqual(response.data['detail'], error_detail)

    # GET detail
    def test_get_ingredient_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(recipe=recipe).first()
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ingredient_with_quantity = None
        if ingredient.units_of_measurement:
            ingredient_with_quantity = f'{ingredient.quantity} {ingredient.units_of_measurement} of {ingredient.name}'
        else:
            ingredient_with_quantity = f'{ingredient.quantity} {ingredient.name}'
        test_server_prefix = 'http://testserver'
        expected_data = {
            'url': test_server_prefix + reverse('recipe-ingredient-detail',
                                                kwargs={'recipe_pk': recipe.id, 'pk': ingredient.id}),
            'id': ingredient.id,
            'name': ingredient.name,
            'slug': ingredient.slug,
            'quantity': str(ingredient.quantity),
            'units_of_measurement': ingredient.units_of_measurement,
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id}),
            'ingredient_with_quantity': ingredient_with_quantity
        }
        self.assertEqual(response.data, expected_data)

    def test_get_nonexistent_ingredient_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 76})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_ingredient_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 98
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 86})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    # POST
    def test_logged_user_posts_ingredient_with_not_unique_name_for_recipe(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(recipe=recipe).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'name': ingredient.name,
                                               'quantity': 10}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = f"Ingredient with name '{ingredient.name}' already exists for this recipe."
        self.assertEqual(response.data[0], error_detail)

    def test_logged_user_posts_ingredient_with_quantity_lower_than_zero(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'name': 'butter',
                                               'quantity': -1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_ingredient_with_empty_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_ingredient_with_no_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_new_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'name': 'butter',
                                               'quantity': 100,
                                               'units_of_measurement': 'gm'
                                               }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        test_server_prefix = 'http://testserver'
        ingredient = Ingredient.objects.filter(Q(recipe=recipe) &
                                               Q(name='butter')).first()
        expected_data = {'url': test_server_prefix + reverse('recipe-ingredient-detail',
                                                             kwargs={'recipe_pk': recipe.id,
                                                                     'pk': ingredient.id}),
                         'id': ingredient.id,
                         'name': ingredient.name,
                         'quantity': str(ingredient.quantity),
                         'units_of_measurement': ingredient.units_of_measurement,
                         'recipe_title': ingredient.recipe.title,
                         'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
                         }
        self.assertEqual(response.data, expected_data)

    def test_post_ingredient_for_nonexistent_recipe(self):
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        nonexistent_recipe_id = 67
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': nonexistent_recipe_id})
        response = self.client.post(url, data={'name': 'basil',
                                               'quantity': 20,
                                               'units_of_measurement': 'gm'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f"Recipe with id {nonexistent_recipe_id} was not found."
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_posts_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'name': 'new name',
                                               'quantity': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_posts_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-ingredient-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'name': 'new name',
                                               'quantity': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # PUT
    def test_logged_user_updates_ingredient_with_not_unique_name(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient_1 = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='eggs')
        ).first()
        ingredient_2 = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')
        ).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail', kwargs={'recipe_pk': recipe.id,
                                                          'pk': ingredient_1.id})
        response = self.client.put(url, data={'name': ingredient_2.name,
                                              'quantity': 35,
                                              'unit_of_measurement': 'gm'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_ingredient_with_quantity_less_than_zero(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(Q(recipe=recipe)
                                               & Q(name='eggs')).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail', kwargs={'recipe_pk': recipe.id,
                                                          'pk': ingredient.id})
        response = self.client.put(url, data={'name': ingredient.name,
                                              'quantity': -1},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail', kwargs={'recipe_pk': recipe.id,
                                                          'pk': ingredient.id})
        response = self.client.put(url, data={'name': 'cheddar',
                                              'quantity': ingredient.quantity,
                                              'units_of_measurement': ingredient.units_of_measurement})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        ingredient = Ingredient.objects.filter(Q(recipe=recipe) &
                                               Q(name='cheddar')).first()
        expected_data = {
            'url': test_server_prefix + reverse('recipe-ingredient-detail',
                                                kwargs={'recipe_pk': recipe.id,
                                                        'pk': ingredient.id}),
            'id': ingredient.id,
            'name': ingredient.name,
            'quantity': str(ingredient.quantity),
            'units_of_measurement': ingredient.units_of_measurement,
            'recipe_title': ingredient.recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_updates_nonexistent_ingredient(self):
        user = CustomUser.objects.filter(username='user1').first()
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 99})
        response = self.client.put(url, data={'name': 'cheddar',
                                              'quantity': 50,
                                              'units_of_measurement': 'gm'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_ingredient_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 78
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 67})
        response = self.client.put(url, data={'name': 'cheddar',
                                              'quantity': 50,
                                              'units_of_measurement': 'gm'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f"Recipe with id {nonexistent_recipe_id} was not found."
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_updates_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.put(url, data={'name': 'cheddar',
                                              'quantity': ingredient.quantity,
                                              'units_of_measurement': ingredient.units_of_measurement},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_updates_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.put(url, data={'name': 'cheddar',
                                              'quantity': ingredient.quantity,
                                              'units_of_measurement': ingredient.units_of_measurement},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_logged_user_deletes_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logged_user_deletes_nonexistent_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 90})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_ingredient_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 90
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 67})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f"Recipe with id {nonexistent_recipe_id} was not found."
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_deletes_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_deletes_ingredient(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        ingredient = Ingredient.objects.filter(
            Q(recipe=recipe) & Q(name='cheese')).first()
        url = reverse('recipe-ingredient-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': ingredient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RecipeImagesTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user_1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@gmail.com',
            password='34somepassword34'
        )
        test_user_2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@gmail.com',
            password='34somepassword34'
        )

        category = Category.objects.create(title='Pasta',
                                           slug='pasta')
        recipe = Recipe.objects.create(author=test_user_1,
                                       category=category,
                                       title='Pasta 1',
                                       instructions='Cook pasta')

        RecipeImage.objects.create(recipe=recipe,
                                   image=tempfile.NamedTemporaryFile(suffix=".jpg").name)

        RecipeImage.objects.create(recipe=recipe,
                                   image=tempfile.NamedTemporaryFile(suffix=".jpg").name)

    def tearDown(self) -> None:
        try:
            os.remove('media/recipes/images/test_image.jpg')
        except FileNotFoundError:
            pass
        return super().tearDown()

    # GET list
    def test_get_image_list(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_image_list_for_nonexistent_recipe(self):
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': 67})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # GET detail
    def test_get_image_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image = RecipeImage.objects.filter(recipe=recipe).first()
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': image.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        # get image path how it would look like in response
        image_path_on_test_server = str(image.image).replace('\\', '/')
        image_path_on_test_server = image_path_on_test_server.replace(
            'C:', 'C%3A')
        image_path_on_test_server = test_server_prefix + \
            '/media/' + image_path_on_test_server
        expected_data = {
            'url': test_server_prefix + reverse('recipe-image-detail',
                                                kwargs={'recipe_pk': recipe.id,
                                                        'pk': image.id}),
            'id': image.id,
            'image': image_path_on_test_server,
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail',
                                                   kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_get_nonexistent_image_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 78})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_image_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 70
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 89})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    # POST
    def test_logged_user_posts_new_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))

        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, 'jpeg')
        image_file.seek(0)

        uploaded_file = SimpleUploadedFile(
            'test_image.jpg', image_file.read(), content_type='image/jpeg')

        response = self.client.post(
            url, data={'image': uploaded_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        image = recipe.images.all().order_by('-id')[0]
        test_server_prefix = 'http://testserver'
        expected_data = {
            'url': test_server_prefix + reverse('recipe-image-detail', kwargs={'recipe_pk': recipe.id,
                                                                               'pk': image.id}),
            'id': image.id,
            'image': test_server_prefix + '/media/' + str(image.image),
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail',
                                                   kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_posts_fourth_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image = RecipeImage.objects.create(recipe=recipe,
                                           image=tempfile.NamedTemporaryFile(suffix=".jpg").name)
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))

        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, 'jpeg')
        image_file.seek(0)

        uploaded_file = SimpleUploadedFile(
            'test_image.jpg', image_file.read(), content_type='image/jpeg')

        response = self.client.post(
            url, data={'image': uploaded_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_detail = "More than 3 images cannot be posted for one recipe."
        self.assertEqual(response.data[0], error_detail)

    def test_logged_user_posts_image_with_empty_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_image_with_no_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 92
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': nonexistent_recipe_id})
        # ViewSet will raise a 404 error so it does not really
        # matter if real image is sent and if right format is used
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_posts_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        # ViewSet will raise a 403 error so it does not really
        # matter if real image is sent and if right format is used
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_posts_image_for_recipe(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-image-list',
                      kwargs={'recipe_pk': recipe.id})
        # ViewSet will raise a 401 error so it does not really
        # matter if real image is sent and if right format is used
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_logged_user_deletes_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image = RecipeImage.objects.filter(recipe=recipe).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': image.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logged_user_deletes_nonexistent_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 56})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_image_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 87
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 67})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_deletes_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image = RecipeImage.objects.filter(recipe=recipe).first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': image.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_deletes_image(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        image = RecipeImage.objects.filter(recipe=recipe).first()
        url = reverse('recipe-image-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': image.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReviewsTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user_1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@gmail.com',
            password='34somepassword34'
        )
        test_user_2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@gmail.com',
            password='34somepassword34'
        )

        category = Category.objects.create(title='Pasta',
                                           slug='pasta')

        recipe = Recipe.objects.create(author=test_user_1,
                                       category=category,
                                       title='Pasta 1',
                                       instructions='Cook pasta')

        Review.objects.create(recipe=recipe,
                              author=test_user_2,
                              content='Cool recipe')

    # GET list
    def test_get_review_list(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_review_list_for_nonexistent_recipe(self):
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': 89})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # GET detail
    def test_get_review_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        review = Review.objects.filter(author__username='user2').first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        expected_data = {'url': test_server_prefix + reverse('recipe-review-detail',
                                                             kwargs={'recipe_pk': recipe.id, 'pk': review.id}),
                         'id': review.id,
                         'content': review.content,
                         'author_name': review.author.username,
                         'author': test_server_prefix + reverse('author-detail',
                                                                kwargs={'pk': review.author.id}),
                         'published': review.published.replace(tzinfo=None).isoformat() + 'Z',
                         'updated': review.updated.replace(tzinfo=None).isoformat() + 'Z',
                         'recipe_title': recipe.title,
                         'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
                         }
        self.assertEqual(response.data, expected_data)

    def test_get_nonexistent_review_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 67})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_review_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 98
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 90})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    # POST
    def test_logged_user_posts_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'content':
                                               'My recipe is cool'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.filter(author=user).first()
        test_server_prefix = 'http://testserver'
        expected_data = {
            'url': test_server_prefix + reverse('recipe-review-detail',
                                                kwargs={'recipe_pk': recipe.id, 'pk': review.id}),
            'id': review.id,
            'content': review.content,
            'author_name': review.author.username,
            'author': test_server_prefix + reverse('author-detail',
                                                   kwargs={'pk': review.author.id}),
            'published': review.published.replace(tzinfo=None).isoformat() + 'Z',
            'updated': review.updated.replace(tzinfo=None).isoformat() + 'Z',
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_posts_review_with_invalid_data(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'content': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_review_with_empty_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_review_with_no_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_with_review_posts_new_review_on_recipe(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(
            url, data={'content': 'New content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        error_detail = 'User can only have one review for each recipe.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_not_authorized_user_posts_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url,
                                    data={'content': 'Content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logged_user_posts_review_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 90
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-list',
                      kwargs={'recipe_pk': nonexistent_recipe_id})
        response = self.client.post(
            url, data={'content': 'content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    # PUT
    def test_logged_user_updates_review_with_invalid_data(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url, data={'content': ''},
                                   format='json')
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_review_with_empty_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        review = Review.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_review_with_no_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        review = Review.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url,
                                   data={'content': 'Pretty cool recipe.'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        review = Review.objects.filter(content='Pretty cool recipe.').first()
        expected_data = {
            'url': test_server_prefix + reverse('recipe-review-detail',
                                                kwargs={'recipe_pk': recipe.id, 'pk': review.id}),
            'id': review.id,
            'content': review.content,
            'author_name': review.author.username,
            'author': test_server_prefix + reverse('author-detail',
                                                   kwargs={'pk': review.author.id}),
            'published': review.published.replace(tzinfo=None).isoformat() + 'Z',
            'updated': review.updated.replace(tzinfo=None).isoformat() + 'Z',
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_updates_nonexistent_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 67})
        response = self.client.put(
            url, data={'content': 'Content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_review_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 99
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 67})
        response = self.client.put(url, data={'content': 'Content'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_updates_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url, data={'content': 'Another content'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_updates_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.put(url, data={'content': 'Another content'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_logged_user_deletes_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(author=user) & Q(recipe=recipe)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logged_user_deletes_nonexistent_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 99})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_review_for_nonexistent_review(self):
        nonexistent_recipe_id = 64
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 78})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_logged_user_without_permission_deletes_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_deletes_review(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        review = Review.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        url = reverse('recipe-review-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': review.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RatingsTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user_1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@gmail.com',
            password='34somepassword34'
        )
        test_user_2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@gmail.com',
            password='34somepassword34'
        )

        category = Category.objects.create(title='Pasta',
                                           slug='pasta')

        recipe = Recipe.objects.create(author=test_user_1,
                                       category=category,
                                       title='Pasta 1',
                                       instructions='Cook pasta')

        Rating.objects.create(recipe=recipe,
                              author=test_user_2,
                              value=9)

    # GET list
    def test_get_rating_list(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_rating_list_for_nonexistent_recipe(self):
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': 89})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # GET detail
    def test_get_rating_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        rating = Rating.objects.filter(author__username='user2').first()
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        expected_data = {'url': test_server_prefix + reverse('recipe-rating-detail',
                                                             kwargs={'recipe_pk': recipe.id, 'pk': rating.id}),
                         'id': rating.id,
                         'value': rating.value,
                         'author_name': rating.author.username,
                         'author': test_server_prefix + reverse('author-detail',
                                                                kwargs={'pk': rating.author.id}),
                         'published': rating.published.replace(tzinfo=None).isoformat() + 'Z',
                         'updated': rating.updated.replace(tzinfo=None).isoformat() + 'Z',
                         'recipe_title': recipe.title,
                         'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
                         }
        self.assertEqual(response.data, expected_data)

    def test_get_nonexistent_rating_detail(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 67})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_rating_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 45
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': nonexistent_recipe_id,
                              'pk': 85})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        error_detail = f'Recipe with id {nonexistent_recipe_id} was not found.'
        self.assertEqual(response.data['detail'], error_detail)

    # POST
    def test_logged_user_posts_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'value': 9}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        rating = Rating.objects.filter(author=user).first()
        test_server_prefix = 'http://testserver'
        expected_data = {
            'url': test_server_prefix + reverse('recipe-rating-detail',
                                                kwargs={'recipe_pk': recipe.id, 'pk': rating.id}),
            'id': rating.id,
            'value': rating.value,
            'author_name': rating.author.username,
            'author': test_server_prefix + reverse('author-detail',
                                                   kwargs={'pk': rating.author.id}),
            'published': rating.published.replace(tzinfo=None).isoformat() + 'Z',
            'updated': rating.updated.replace(tzinfo=None).isoformat() + 'Z',
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_posts_rating_with_rating_less_than_0(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'value': -1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_rating_with_rating_greater_than_10(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={'value': 11}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_rating_with_empty_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_rating_with_no_body(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url, data=None, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logged_user_posts_rating_for_nonexistent_recipe(self):
        nonexistent_recipe_id = 90

    def test_logged_user_with_rating_posts_new_rating_on_recipe(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(
            url, data={'value': 8}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        error_detail = 'User can only have one rating for each recipe.'
        self.assertEqual(response.data['detail'], error_detail)

    def test_not_authorized_user_posts_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        url = reverse('recipe-rating-list',
                      kwargs={'recipe_pk': recipe.id})
        response = self.client.post(url,
                                    data={'value': 10}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # PUT
    def test_logged_user_updates_rating_with_rating_less_than_0(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.put(url, data={'value': -1},
                                   format='json')
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_rating_with_rating_greater_than_10(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.put(url, data={'value': 11},
                                   format='json')
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_logged_user_updates_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.put(url,
                                   data={'value': 8}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        rating = Rating.objects.filter(
            Q(recipe=recipe) & Q(author=user)).first()
        expected_data = {
            'url': test_server_prefix + reverse('recipe-rating-detail',
                                                kwargs={'recipe_pk': recipe.id, 'pk': rating.id}),
            'id': rating.id,
            'value': rating.value,
            'author_name': rating.author.username,
            'author': test_server_prefix + reverse('author-detail',
                                                   kwargs={'pk': rating.author.id}),
            'published': rating.published.replace(tzinfo=None).isoformat() + 'Z',
            'updated': rating.updated.replace(tzinfo=None).isoformat() + 'Z',
            'recipe_title': recipe.title,
            'recipe': test_server_prefix + reverse('recipe-detail', kwargs={'pk': recipe.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_logged_user_updates_nonexistent_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 67})
        response = self.client.put(
            url, data={'value': 8}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_rating_for_nonexistent_recipe(self):
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': 89,
                              'pk': 67})
        response = self.client.put(url, data={'value': 7},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_logged_user_without_permission_updates_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.put(url, data={'value': 9},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_updates_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.put(url, data={'value': 9},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # DELETE
    def test_logged_user_deletes_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(author=user) & Q(recipe=recipe)).first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logged_user_deletes_nonexistent_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': 99})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_rating_for_nonexistent_recipe(self):
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': 99,
                              'pk': 78})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_logged_user_without_permission_deletes_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        user = CustomUser.objects.filter(username='user1').first()
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_authorized_user_deletes_rating(self):
        recipe = Recipe.objects.filter(title='Pasta 1').first()
        author = CustomUser.objects.filter(username='user2').first()
        rating = Rating.objects.filter(
            Q(author=author) & Q(recipe=recipe)).first()
        url = reverse('recipe-rating-detail',
                      kwargs={'recipe_pk': recipe.id,
                              'pk': rating.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorsTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        test_user = CustomUser.objects.create_user(username='user',
                                                   email='user@gmail.com',
                                                   password='34somepassword34')

    # GET list
    def test_get_author_list(self):
        url = reverse('author-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # GET detail
    def test_get_author_detail(self):
        author = CustomUser.objects.filter(username='user').first()
        url = reverse('author-detail',
                      kwargs={'pk': author.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_server_prefix = 'http://testserver'
        expected_data = {
            'url': test_server_prefix + reverse('author-detail',
                                                kwargs={'pk': author.id}),
            'id': author.id,
            'username': author.username,
            'image': None,
            'get_recipes': test_server_prefix + reverse('author-get-recipes',
                                                        kwargs={'pk': author.id})
        }
        self.assertEqual(response.data, expected_data)

    def test_get_recipes_of_author_detail(self):
        category = Category.objects.create(title='Pasta',
                                           slug='pasta')
        author = CustomUser.objects.filter(username='user').first()
        recipe_1 = Recipe.objects.create(author=author,
                                         category=category,
                                         title='Pasta 1',
                                         instructions='Cook pasta 1')
        recipe_2 = Recipe.objects.create(author=author,
                                         category=category,
                                         title='Pasta 2',
                                         instructions='Cook pasta 2')
        url = reverse('author-get-recipes',
                      kwargs={'pk': author.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        number_of_recipes_by_author = Recipe.objects.filter(
            author=author).count()
        self.assertEqual(len(response.data),
                         number_of_recipes_by_author)

    def test_nonexistent_author_detail(self):
        url = reverse('author-get-recipes',
                      kwargs={'pk': 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
