from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ==========================================================
# PROFILE
# ==========================================================

class Profile(models.Model):
    ROLE_CHOICES = [
        ("resident", "Resident"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="resident",
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ==========================================================
# PROPERTY
# ==========================================================

class Property(models.Model):

    PROPERTY_TYPE_CHOICES = [
        ("apartment", "Apartment"),
        ("duplex", "Duplex"),
        ("bungalow", "Bungalow"),
        ("shop", "Shop"),
        ("office", "Office"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("maintenance", "Maintenance"),
    ]

    property_id = models.CharField(
        max_length=20,
        unique=True,
    )

    property_number = models.CharField(
        max_length=50,
        unique=True,
    )

    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES,
    )

    bedrooms = models.PositiveIntegerField(default=1)

    bathrooms = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )

    resident = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.property_number


# ==========================================================
# COMPLAINT
# ==========================================================

class Complaint(models.Model):

    CATEGORY_CHOICES = [
        ("water", "Water"),
        ("electricity", "Electricity"),
        ("security", "Security"),
        ("plumbing", "Plumbing"),
        ("waste", "Waste Management"),
        ("cleaning", "Cleaning"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("rejected", "Rejected"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    resident = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="complaints",
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="complaints",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="other",
    )

    location = models.CharField(max_length=255)

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )

    resolution_note = models.TextField(
        blank=True,
        null=True,
    )

    expected_completion = models.DateField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.title} ({self.status})"


# ==========================================================
# SIGNALS
# ==========================================================

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()