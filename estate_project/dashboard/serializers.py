from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile, Complaint, Property


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
        ]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_staff",
            "is_superuser",
        ]


class ResidentSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
        ]


class ComplaintSerializer(serializers.ModelSerializer):
    resident = UserSerializer(read_only=True)

    property = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all()
    )

    class Meta:
        model = Complaint

        fields = [
            "id",
            "resident",
            "property",
            "title",
            "description",
            "category",
            "location",
            "priority",
            "status",
            "assigned_to",
            "resolution_note",
            "expected_completion",
            "created_at",
            "updated_at",
            "resolved_at",
        ]

        read_only_fields = [
            "resident",
            "created_at",
            "updated_at",
            "resolved_at",
        ]

    def get_fields(self):
        """
        Residents cannot edit management-only fields.
        Managers/Admins can.
        """
        fields = super().get_fields()

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return fields

        role = request.user.profile.role

        if role == "resident":
            fields["status"].read_only = True
            fields["assigned_to"].read_only = True
            fields["resolution_note"].read_only = True
            fields["expected_completion"].read_only = True

        return fields