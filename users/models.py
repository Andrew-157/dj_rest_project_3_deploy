from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser


def validate_file_size(file):
    max_kb_size = 500

    if file.size > max_kb_size * 1024:
        raise ValidationError(f'Files cannot be larger than {max_kb_size}KB')

    # file_size = image.file.size
    # limit_mb = 8
    # if file_size > limit_mb * 1024 * 1024:
    #     raise ValidationError(f"Maximum size of the image is {limit_mb} MB")


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    image = models.ImageField(upload_to='users/images/',
                              validators=[validate_file_size], null=True)

    class Meta:
        ordering = ['username']
