from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField


def validate_file_size(image):

    file_size = image.file.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Maximum size of the image is {limit_mb} MB")


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    image = models.ImageField(upload_to='users/images/',
                              validators=[validate_file_size], null=True)
    image = CloudinaryField("image", validators=[
                            validate_file_size], null=True)

    class Meta:
        ordering = ['username']
