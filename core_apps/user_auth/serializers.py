from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
)

User = get_user_model()


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = [
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
            "id_no",
            "security_question",
            "security_answer",
        ]

    def create(self, validated_data):
        validated_data["security_answer"] = make_password(
            validated_data["security_answer"]
        )
        user = User.objects.create_user(**validated_data)
        return user
