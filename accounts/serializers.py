from rest_framework import serializers

from accounts.models import User
from projects.serializers import InputSerializer


class AccountInput(InputSerializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class AccountOutput(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "is_active"]
        read_only_fields = fields


class EmployeeOption(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, user):
        return user.get_full_name() or user.username

    class Meta:
        model = User
        fields = ["id", "name"]
        read_only_fields = fields
