from django.core.exceptions import ValidationError


def validate_file_size(image):

    file_size = image.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Maximum size of the image is {limit_mb} MB")
