from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException
from rest_framework import status


class ConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _(
        'Method "{method}" could not be processed as it would result in conflict.')
    default_code = 'conflict'

    def __init__(self, method, detail=None, code=None):
        if detail is None:
            detail = force_str(self.default_detail).format(method=method)
        super().__init__(detail, code)
