from django.urls import path, include
from . import views
from . import dashboard_views
from .auth_views import RegisterView, CurrentUserView
from .views import (
    ResidentOnlyView,
    ManagerOnlyView,
    AdminOnlyView,
    ManagerAdminView,
)

urlpatterns = [
    path("residents/", views.get_residents),
    path("residents/create/", views.create_resident),
    
    path("residents/assign-property/", views.assign_property_to_resident),
    
    path("residents/<str:resident_id>/", views.update_resident),
    path("residents/<str:resident_id>/delete/", views.delete_resident),
    

    path("properties/", views.get_properties),
    path("properties/create/", views.create_property),
    path("properties/<str:property_id>/", views.update_property),
    path("properties/<str:property_id>/delete/", views.delete_property),

    path("complaints/", views.get_complaints),
    path("complaints/create/", views.create_complaint),
    
    path("complaints/assign-property/", views.assign_property_to_complaint),
    path("complaints/assign-team/", views.assign_complaint_to_team),

    path("complaints/<str:complaint_id>/", views.update_complaint),
    path("complaints/<str:complaint_id>/delete/", views.delete_complaint),

    path("estate/", views.ai_query_v2),
    path("estates/", views.get_estates),
    path("estates/create/", views.create_estate),  
    path("estates/<str:estate_id>/update/", views.update_estate),
    path("estates/<str:estate_id>/delete/", views.delete_estate),
    path("ai/", views.ai_query_v3),
    path("ai/v2/", views.ai_query_v2),
    path("ai/v3/", views.ai_query_v3),
    
    path("dashboard/overview/", dashboard_views.dashboard_overview),
    path("dashboard/complaints-by-category/", dashboard_views.complaints_by_category),
    path("dashboard/properties-by-status/", dashboard_views.properties_by_status),
    path("dashboard/top-residents/", dashboard_views.residents_with_most_complaints),
    path("dashboard/top-properties/", dashboard_views.properties_with_most_complaints),
    path("dashboard/recent-complaints/", dashboard_views.recent_complaint_activity),

    path("dashboard/", include("dashboard.urls1")),
    
    path("managers/", views.get_managers),
    path("managers/create/", views.create_manager),
    path("managers/<str:manager_id>/", views.update_manager),
    path("managers/<str:manager_id>/delete/", views.delete_manager),
    
    path("maintenance-team/create/", views.create_maintenance_team),
    path("maintenance-teams/", views.get_maintenance_teams),
    path("maintenance-teams/<str:team_id>/", views.get_maintenance_team),
    path("maintenance-teams/<str:team_id>/update/", views.update_maintenance_team),
    path("maintenance-teams/<str:team_id>/delete/", views.delete_maintenance_team),
    
    path("resident/", ResidentOnlyView.as_view()),
    path("manager/", ManagerOnlyView.as_view()),
    path("admin/", AdminOnlyView.as_view()),
    path("manager-admin/", ManagerAdminView.as_view()),
    
    
    path("ai/test/", views.test_ai),
    
    path("register/", RegisterView.as_view(), name="register"),
path("me/", CurrentUserView.as_view(), name="current-user"),
    
]



