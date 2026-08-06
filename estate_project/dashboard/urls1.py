from django.urls import path
from .views import (
    ResidentView,
    ManagerView,
    AdminView,
    StaffView,
    ComplaintListCreateView,
    ComplaintDetailView,
    ResidentListView,
    ResidentDetailView,
    MyProfileView
)

urlpatterns = [
    path("resident/", ResidentView.as_view(), name="resident"),
    path("manager/", ManagerView.as_view(), name="manager"),
    path("admin/", AdminView.as_view(), name="admin"),
    path("staff/", StaffView.as_view(), name="staff"),

    path("complaints/", ComplaintListCreateView.as_view(), name="complaints"),
    path("complaints/<int:pk>/", ComplaintDetailView.as_view(), name="complaint-detail"),
    
path("residents/", ResidentListView.as_view(), name="resident-list"),
    path("residents/<int:pk>/", ResidentDetailView.as_view(), name="resident-detail"),
    path("my-profile/", MyProfileView.as_view(), name="my-profile"),
]