from typing import cast

from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Complaint
from .serializers import (
    ComplaintSerializer,
    ResidentSerializer
)

from .permissions import (
    IsResident,
    IsManager,
    IsAdmin,
    IsManagerOrAdmin,
)

from rest_framework.exceptions import PermissionDenied
from typing import cast

# ===========================
# Role Test Views
# ===========================

class ResidentView(APIView):
    permission_classes = [IsAuthenticated, IsResident]

    def get(self, request):
        return Response({"message": "Welcome Resident"})


class ManagerView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        return Response({"message": "Welcome Manager"})


class AdminView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({"message": "Welcome Admin"})


class StaffView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        return Response({"message": "Welcome Staff"})


# ===========================
# Complaint Views
# ===========================


class ComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = user.profile.role

        if role in ["manager", "admin"]:
            return Complaint.objects.all().order_by("-created_at")

        return Complaint.objects.filter(
            resident=user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user

        if user.profile.role != "resident":
            raise PermissionDenied(
                "Only residents can submit complaints."
            )


        serializer.save(resident=user)


class ComplaintDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = cast(User, self.request.user)
        role = user.profile.role

        if role in ["manager", "admin"]:
            return Complaint.objects.all()

        return Complaint.objects.filter(resident=user)

    def perform_update(self, serializer):
        user = cast(User, self.request.user)
        role = user.profile.role

        if role == "resident":
            raise PermissionDenied(
                "Residents cannot update complaints."
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = cast(User, self.request.user)
        role = user.profile.role

        if role != "admin":
            raise PermissionDenied(
                "Only administrators can delete complaints."
            )

        instance.delete()
        

# ===========================
# Resident Management Views
# ===========================

class ResidentListView(generics.ListAPIView):
    serializer_class = ResidentSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get_queryset(self):
        return User.objects.filter(
            profile__role="resident"
        ).order_by("first_name", "last_name")


class ResidentDetailView(generics.RetrieveAPIView):
    serializer_class = ResidentSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    queryset = User.objects.filter(
        profile__role="resident"
    )


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ResidentSerializer(request.user)
        return Response(serializer.data)