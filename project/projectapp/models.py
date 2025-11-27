# projectapp/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now


# CUSTOM USER MODEL
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("guide", "Guide"),
        ("admin", "Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    assigned_guide = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'guide'},
        related_name="students",
        verbose_name="Assigned Guide",
    )

    profile_picture = models.ImageField(
        upload_to="profile_pics/", null=True, blank=True, default="profile_pics/default.png"
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"


# ASSIGNMENT MODEL
User = settings.AUTH_USER_MODEL

class Assignment(models.Model):
    guide = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'guide'},
        related_name="assignments"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name="student_assignments",
        null=True, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    TARGET_CHOICES = (
        ("all", "All Students"),
        ("my_students", "Only My Students"),
    )
    target_group = models.CharField(
        max_length=20, choices=TARGET_CHOICES, default="my_students"
    )

    def __str__(self):
        return f"{self.title} ({self.guide.username})"


# SUBMISSION MODEL (with AI Detection)
class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    text_answer = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="submissions/", blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    # NEW FIELD: AI detection score (0–100%)
    ai_score = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.student} → {self.assignment}"


# PROJECT MODEL
class Project(models.Model):
    guide = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'guide'},
        related_name="guided_projects"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name="student_projects",
        null=True, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)
    report_file = models.FileField(upload_to="project_reports/", null=True, blank=True)


    def __str__(self):
        return f"{self.title} ({self.guide.username})"


# QUERY MODEL
class Query(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_queries")
    guide = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guide_queries")
    message = models.TextField()
    reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} → {self.guide.username} : {self.message[:20]}"


# NOTIFICATION MODEL
class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"
