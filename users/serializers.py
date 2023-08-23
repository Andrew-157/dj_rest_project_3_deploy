from rest_framework import serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer,\
    UserSerializer as BaseUserSerializer


class UserCreateSerializer(BaseUserCreateSerializer):

    class Meta(BaseUserCreateSerializer.Meta):
        fields = [
            'id', 'username', 'password', 'email', 'image'
        ]


class UserSerializer(BaseUserSerializer):
    image = serializers.ImageField()
    class Meta(BaseUserSerializer.Meta):
        fields = [
            'id', 'username', 'email', 'image'
        ]
