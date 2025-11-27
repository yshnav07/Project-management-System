from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    # logins
    path("login/", views.user_login, name="user_login"),
    path("admin-login/", views.admin_login, name="admin_login"),

    # dashboards
    path("student-dashboard/", views.student_dashboard, name="student-dashboard"),
    path("guide-dashboard/", views.guide_dashboard, name="guide-dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("notification/<int:notif_id>/read/", views.read_notification, name="read-notification"),

    # logouts
    path("student-logout/", views.user_logout, name="student-logout"),
    path("guide-logout/", views.user_logout, name="guide-logout"),
    path("admin-logout/", views.admin_logout, name="admin-logout"),

    # student features
    path("student-assignments/", views.student_assignments, name="student-assignments"),
    path("submit-assignment/<int:assignment_id>/", views.submit_assignment, name="submit-assignment"),
    path("student-profile/", views.student_profile, name="student-profile"),
    path("student/projects/", views.student_projects, name="student-projects"),
    path("student/projects/update/<int:pk>/", views.update_project, name="update-project"),
    path("text-summarizer/", views.text_summarizer, name="text-summarizer"),
    path("summarize-video/", views.summarize_video, name="summarize-video"),




    # admin manage
    path("manage-guides/", views.manage_guides, name="manage-guides"),
    path("manage-students/", views.manage_students, name="manage-students"),
    path("update-guide/<int:id>/", views.update_guide, name="update-guide"),
    path("delete-guide/<int:id>/", views.delete_guide, name="delete-guide"),
    path("update-student/<int:id>/", views.update_student, name="update-student"),
    path("delete-student/<int:id>/", views.delete_student, name="delete-student"),
    path("add-user/", views.add_user, name="add-user"),

    # guide manage
    path("guide-students/", views.guide_students, name="guide-students"),
    path("guide-assignments/", views.guide_assignments, name="guide-assignments"),
    path("guide-submissions/<int:assignment_id>/", views.guide_view_submissions, name="guide-submissions"),
    path("guide-profile/", views.guide_profile, name="guide-profile"),
    path("delete-project/<int:project_id>/", views.delete_project, name="delete-project"),


    #update
    # urls.py
    path("update-assignment/<int:id>/", views.update_assignment, name="update-assignment"),
    path("delete-assignment/<int:id>/", views.delete_assignment, name="delete-assignment"),

    # Guide project management
    path("guide-projects/", views.guide_projects, name="guide-projects"),

    # Student project updates
    path("update-project/<int:project_id>/", views.update_project_progress, name="update-project"),
    path("guide/projects/update/<int:project_id>/", views.update_project, name="guide-update-project"),
    path("guide-queries/", views.guide_queries, name="guide-queries"),    
    path("reply-query/<int:query_id>/", views.reply_query, name="reply_query"),
    path("student/queries/", views.student_queries, name="student-queries"),

]

