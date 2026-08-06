from django.contrib import admin
from .models import Profile, Property, Complaint


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "property_number",
        "property_type",
        "status",
        "resident",
    )


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "resident",
        "property",
        "status",
        "priority",
        "created_at",
    )