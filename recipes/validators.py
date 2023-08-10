from django.core.exceptions import ValidationError


def validate_file_size(file):
    max_kb_size = 1000000

    if file.size > max_kb_size * 1024:
        raise ValidationError(f'Files cannot be larger than {max_kb_size}KB')
