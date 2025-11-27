# projectapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.utils.timezone import now
from .models import Assignment, Submission, CustomUser, Project, Query,Notification
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import Notification
from .utils import detect_ai_usage
# projectapp/views.py (append near other views)
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import torch
import whisper
import tempfile
from moviepy.editor import VideoFileClip
import os
os.environ["IMAGEIO_FFMPEG_EXE"] = r"C:\ffmpeg\bin\ffmpeg.exe"
from transformers import T5ForConditionalGeneration, T5Tokenizer
from django.shortcuts import render
from django.http import FileResponse


def about(request):
    return render(request, "manage/about.html")

def ai_detection_view(request):
    ai_score = None

    if request.method == 'POST':
        user_text = request.POST.get('text_input', '')
        ai_score = detect_ai_usage(user_text)

    return render(request, 'ai_detection.html', {'ai_score': ai_score})

User = get_user_model()

# -----------------------------
# ROLE CHECKS
# -----------------------------
def admin_required(user):
    return user.role == "admin" or user.is_superuser

def guide_required(user):
    return user.role == "guide"

def student_required(user):
    return user.role == "student"

# -----------------------------
# HOME
# -----------------------------
@never_cache
def index(request):
    return render(request, "auth/home.html")

# -----------------------------
# USER LOGIN (Role based redirect)
# -----------------------------
@never_cache
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}! ✅")

            if user.role == "student":
                return redirect("student-dashboard")
            elif user.role == "guide":
                return redirect("guide-dashboard")
            elif user.role == "admin" or user.is_superuser:
                return redirect("admin-dashboard")

        messages.error(request, "Invalid username or password ❌")
    return render(request, "auth/login.html")

# -----------------------------
# ADMIN LOGIN
# -----------------------------
@never_cache
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user and (user.role == "admin" or user.is_superuser):
            login(request, user)
            messages.success(request, "Admin login successful ✅")
            return redirect("admin-dashboard")

        messages.error(request, "Invalid admin credentials ❌")
    return render(request, "auth/admin_login.html")

# -----------------------------
# LOGOUTS
# -----------------------------
@never_cache
@login_required
def user_logout(request):
    logout(request)
    request.session.flush()
    return redirect("user_login")

@never_cache
@login_required
def admin_logout(request):
    logout(request)
    request.session.flush()
    return redirect("admin_login")

# -----------------------------
# DASHBOARDS
# -----------------------------


@login_required
def read_notification(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect(notif.link)

def notifications_processor(request):
    if request.user.is_authenticated:
        return {
            "notifications": Notification.objects.filter(
                user=request.user, is_read=False
            )
        }
    return {"notifications": []}

@never_cache
@login_required
@user_passes_test(lambda u: u.role == "student")
def student_dashboard(request):
    student = request.user

    # Fetch projects assigned to this student
    projects = Project.objects.filter(student=student)

    # ✅ Only fetch unread notifications
    notifications = Notification.objects.filter(user=student, is_read=False)

    context = {
        "projects": projects,
        "notifications": notifications,  # Used in base.html bell 🔔
    }
    return render(request, "auth/student_dashboard.html", context)


# ✅ Mark notification as read and redirect
@login_required
def read_notification(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)

    # Mark as read
    notif.is_read = True
    notif.save()

    # Redirect to the original link if exists
    if notif.link:
        return redirect(notif.link)
    return redirect("auth/student-dashboard")
@never_cache
@login_required
@user_passes_test(guide_required)
def guide_dashboard(request):
    guide = request.user

    # Students under this guide
    students = CustomUser.objects.filter(role="student", assigned_guide=guide)
    student_count = students.count()

    # New students this month
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_students_this_month = students.filter(date_joined__gte=start_of_month).count()

    # Assignments created by this guide
    assignments = Assignment.objects.filter(guide=guide)

    # Pending assignments (not all students submitted)
    pending_assignments = [
        a for a in assignments
        if Submission.objects.filter(assignment=a).count() < student_count
    ]

    # ✅ Assignment stats for chart
    assignment_stats = []
    for a in assignments:
        submitted = Submission.objects.filter(assignment=a).count()
        pending = max(student_count - submitted, 0)
        assignment_stats.append({
            "title": a.title,
            "submitted": submitted,
            "pending": pending,
        })

    # Projects supervised
    projects = Project.objects.filter(guide=guide)
    project_count = projects.count()
    completed_projects = projects.filter(progress=100).count()

    # ✅ Project progress distribution for pie chart
    progress_counts = {
        "0_25": projects.filter(progress__lte=25).count(),
        "26_50": projects.filter(progress__gt=25, progress__lte=50).count(),
        "51_75": projects.filter(progress__gt=50, progress__lte=75).count(),
        "76_100": projects.filter(progress__gt=75).count(),
    }

    # Queries raised to this guide
    queries = Query.objects.filter(guide=guide)
    query_count = queries.count()
    urgent_queries = queries.filter(reply__isnull=True).count()  # no reply yet

    context = {
        "assignments": assignments,
        "students": students,
        "student_count": student_count,
        "new_students_this_month": new_students_this_month,
        "assignments_pending": len(pending_assignments),
        "project_count": project_count,
        "completed_projects": completed_projects,
        "query_count": query_count,
        "urgent_queries": urgent_queries,
        "projects": projects,
        "assignment_stats": assignment_stats,   # ✅ bar chart data
        "progress_counts": progress_counts,     # ✅ pie chart data
    }
    return render(request, "auth/guide_dashboard.html", context)


@never_cache
@login_required
@user_passes_test(admin_required)
def admin_dashboard(request):
    guides = CustomUser.objects.filter(role="guide")
    students_count = CustomUser.objects.filter(role="student").count()
    guides_count = guides.count()

    selected_guide_id = request.GET.get("guide")  # from dropdown
    selected_guide = None
    guide_students = []
    guide_assignments = []
    guide_projects = []

    if selected_guide_id:
        try:
            selected_guide = CustomUser.objects.get(id=selected_guide_id, role="guide")
            guide_students = CustomUser.objects.filter(assigned_guide=selected_guide)
            guide_assignments = Assignment.objects.filter(guide=selected_guide)
            guide_projects = Project.objects.filter(guide=selected_guide)
        except CustomUser.DoesNotExist:
            selected_guide = None

    context = {
        "students_count": students_count,
        "guides_count": guides_count,
        "guides": guides,
        "selected_guide": selected_guide,
        "guide_students": guide_students,
        "guide_assignments": guide_assignments,
        "guide_projects": guide_projects,
    }
    return render(request, "auth/admin_dashboard.html", context)
# -----------------------------
# ADMIN MANAGEMENT
# -----------------------------
@never_cache
@login_required
@user_passes_test(admin_required)
def add_user(request):
    guides = User.objects.filter(role='guide')
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")
        assigned_guide_id = request.POST.get("assigned_guide")

        if User.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username already exists")
        else:
            new_user = User.objects.create_user(username=username, email=email, password=password, role=role)
            if role == "student" and assigned_guide_id:
                guide = User.objects.filter(id=assigned_guide_id, role="guide").first()
                if guide:
                    new_user.assigned_guide = guide
                    new_user.save()
            messages.success(request, f"{role.capitalize()} '{username}' added successfully ✅")
            return redirect("admin-dashboard")

    return render(request, "auth/add_user.html", {"guides": guides})

@never_cache
@login_required
@user_passes_test(admin_required)
def manage_guides(request):
    guides = User.objects.filter(role="guide")
    return render(request, "manage/manage_guides.html", {"guides": guides})

@never_cache
@login_required
@user_passes_test(admin_required)
def update_guide(request, id):
    guide = get_object_or_404(User, id=id, role="guide")
    if request.method == "POST":
        guide.first_name = request.POST.get("first_name")
        guide.email = request.POST.get("email")
        guide.save()
        messages.success(request, "Guide updated successfully ✅")
        return redirect("manage-guides")
    return render(request, "manage/update_guide.html", {"guide": guide})

@never_cache
@login_required
@user_passes_test(admin_required)
def delete_guide(request, id):
    guide = get_object_or_404(User, id=id, role="guide")
    guide.delete()
    messages.success(request, "Guide deleted successfully ❌")
    return redirect("manage-guides")

@never_cache
@login_required
@user_passes_test(admin_required)
def manage_students(request):
    students = User.objects.filter(role="student")
    return render(request, "manage/manage_students.html", {"students": students})

@never_cache
@login_required
@user_passes_test(admin_required)
def update_student(request, id):
    student = get_object_or_404(User, id=id, role="student")
    if request.method == "POST":
        student.first_name = request.POST.get("first_name")
        student.username = request.POST.get("username")
        student.email = request.POST.get("email")
        student.save()
        messages.success(request, "Student updated successfully ✅")
        return redirect("manage-students")
    return render(request, "manage/update_student.html", {"student": student})

@never_cache
@login_required
@user_passes_test(admin_required)
def delete_student(request, id):
    student = get_object_or_404(User, id=id, role="student")
    student.delete()
    messages.success(request, "Student deleted successfully ❌")
    return redirect("manage-students")

# -----------------------------
# GUIDE VIEWS
# -----------------------------
@never_cache
@login_required
@user_passes_test(guide_required)
def guide_students(request):
    students = User.objects.filter(role='student', assigned_guide=request.user)
    return render(request, 'manage/guide_student.html', {'students': students})

@never_cache
@login_required
@user_passes_test(lambda u: u.role == "guide")
def guide_assignments(request):
    guide = request.user  

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        due_date = request.POST.get("due_date")
        target = request.POST.get("target_group")

        Assignment.objects.create(
            guide=guide,
            title=title,
            description=description,
            due_date=due_date if due_date else None,
            target_group=target,
        )
        messages.success(request, "✅ Assignment created successfully!")
        return redirect("guide-assignments")

    assignments = Assignment.objects.filter(guide=guide)

    rows = []
    for assignment in assignments:
        submitted_count = Submission.objects.filter(assignment=assignment).count()

        if assignment.target_group == "all":
            total_students = CustomUser.objects.filter(role="student").count()
        else:
            total_students = CustomUser.objects.filter(role="student", assigned_guide=guide).count()

        rows.append({
            "assignment": assignment,
            "submitted": submitted_count,
            "total": total_students,
        })

    return render(request, "auth/guide_assignments.html", {"rows": rows})

@never_cache
@login_required
@user_passes_test(guide_required)
def update_assignment(request, id):
    assignment = get_object_or_404(Assignment, id=id, guide=request.user)

    if request.method == "POST":
        assignment.title = request.POST.get("title")
        assignment.description = request.POST.get("description")
        assignment.due_date = request.POST.get("due_date")
        assignment.target_group = request.POST.get("target")
        assignment.save()
        messages.success(request, "✏ Assignment updated successfully!")
        return redirect("guide-assignments")

    return render(request, "manage/update_assignment.html", {"assignment": assignment})

@never_cache
def delete_assignment(request, id):
    assignment = get_object_or_404(Assignment, id=id)
    assignment.delete()
    messages.warning(request, "🗑 Assignment deleted successfully!")
    return redirect("guide-assignments")

@never_cache
@login_required
@user_passes_test(guide_required)
def guide_view_submissions(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id, guide=request.user)

    # Get relevant students
    if assignment.target_group == "all":
        students = User.objects.filter(role="student")
    else:
        students = User.objects.filter(role="student", assigned_guide=request.user)

    subs = Submission.objects.filter(assignment=assignment).select_related("student")
    submitted_students = {s.student_id: s for s in subs}

    student_status = []
    for s in students:
        if s.id in submitted_students:
            sub = submitted_students[s.id]

            # ✅ Dynamically calculate AI score from the text answer
            ai_score = detect_ai_usage(sub.text_answer or "")

            student_status.append({
                "student": s,
                "status": "submitted",
                "submitted_at": sub.submitted_at,
                "file": sub.file,
                "text_answer": sub.text_answer,
                "ai_score": ai_score,
            })
        else:
            student_status.append({
                "student": s,
                "status": "pending",
                "submitted_at": None,
                "file": None,
                "text_answer": None,
                "ai_score": None,
            })

    return render(request, "manage/view_submissions.html", {
        "assignment": assignment,
        "student_status": student_status
    })

@never_cache
@login_required
@user_passes_test(guide_required)
def guide_profile(request):
    if request.method == "POST" and request.FILES.get("profile_picture"):
        request.user.profile_picture = request.FILES["profile_picture"]
        request.user.save()
        return redirect("guide-profile")

    return render(request, "auth/guide_profile.html")

# -----------------------------
# STUDENT VIEWS
# -----------------------------
@never_cache
@login_required
def student_assignments(request):
    """Show all assignments for the logged-in student."""
    student = request.user
    assignments = Assignment.objects.filter(
        student=student
    ) | Assignment.objects.filter(
        target_group="all"
    ) | Assignment.objects.filter(
        target_group="my_students", guide=student.assigned_guide
    )

    assignments = assignments.distinct().order_by("-created_at")

    # attach submission info for current student
    for a in assignments:
        a.submission = Submission.objects.filter(assignment=a, student=student).first()

    return render(request, "manage/student_assignments.html", {"assignments": assignments})

@never_cache


@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # Check deadline
    if assignment.due_date and timezone.now().date() > assignment.due_date:
        messages.error(request, "⏳ Deadline has passed! You cannot upload this assignment anymore.")
        return redirect("student-assignments")

    if request.method == "POST":
        text_answer = request.POST.get("text_answer")
        file = request.FILES.get("file")

        Submission.objects.create(
            assignment=assignment,
            student=request.user,
            text_answer=text_answer,
            file=file
        )
        messages.success(request, "✅ Assignment submitted successfully!")
        return redirect("student-assignments")

    return render(request, "manage/submit_assignment.html", {"assignment": assignment})



@never_cache
@login_required
@user_passes_test(student_required)
def student_profile(request):
    if request.method == "POST" and request.FILES.get("profile_picture"):
        request.user.profile_picture = request.FILES["profile_picture"]
        request.user.save()
        return redirect("student-profile")

    return render(request, "manage/student_profile.html")

@never_cache
@login_required
@user_passes_test(guide_required)
def guide_projects(request):
    guide = request.user
    students = CustomUser.objects.filter(role="student", assigned_guide=guide)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        due_date = request.POST.get("due_date") 
        student_id = request.POST.get("student")
        student = get_object_or_404(CustomUser, id=student_id, role="student", assigned_guide=guide)

        Project.objects.create(
            guide=guide,
            student=student,
            title=title,
            description=description,
            due_date=due_date if due_date else None   
        )
        Notification.objects.create(
        user=student,
        message=f"New project '{title}' assigned by {guide.username}",
        link=reverse("student-projects")
        )
        messages.success(request, "✅ Project assigned successfully!")
        return redirect("guide-projects")

    projects = Project.objects.filter(guide=guide).select_related("student")
    return render(request, "manage/guide_projects.html", {"students": students, "projects": projects})

@never_cache
@login_required
def update_project_progress(request, project_id):
    project = get_object_or_404(Project, id=project_id, student=request.user)

    if request.method == "POST":
        progress = int(request.POST.get("progress", 0))
        project.progress = max(0, min(progress, 100))

        # ✅ Handle file upload
        if "report_file" in request.FILES:
            project.report_file = request.FILES["report_file"]

        project.save()
        messages.success(request, "✅ Progress updated and report uploaded successfully!")
        return redirect("student-projects")

    return redirect("manage/student-projects")

@never_cache
@login_required
def student_projects(request):
    student = request.user
    projects = Project.objects.filter(student=student).order_by("-created_at")
    return render(request, "manage/student_projects.html", {"projects": projects})

# ---------------- STUDENT ----------------


# ---------------- GUIDE ----------------
@never_cache
@login_required
# def guide_support(request):
#     queries = Query.objects.filter(guide=request.user)

#     if request.method == "POST":
#         query_id = request.POST.get("query_id")
#         response = request.POST.get("response")
#         query = get_object_or_404(Query, id=query_id, guide=request.user)
#         query.response = response
#         query.responded_at = now()
#         query.save()
#         return redirect("guide-support")

#     return render(request, "auth/guide_support.html", {"queries": queries})

@never_cache
@login_required
def student_queries(request):
    if request.method == "POST":
        message = request.POST.get("message")
        guide = request.user.assigned_guide   # ✅ use assigned guide

        if message and guide:
            Query.objects.create(
                student=request.user,
                guide=guide,
                message=message
            )
            Notification.objects.create(
                user=guide,
                message=f"New query from {request.user.username}",
                link=reverse("guide-queries")
            )
            return redirect("student-queries")

    queries = Query.objects.filter(student=request.user).order_by("-created_at")
    return render(request, "manage/student_queries.html", {"queries": queries})

@never_cache
@login_required
def guide_queries(request):
    queries = Query.objects.filter(guide=request.user)

    if request.method == "POST":
        query_id = request.POST.get("query_id")
        response = request.POST.get("response")
        query = get_object_or_404(Query, id=query_id, guide=request.user)
        query.response = response
        query.responded_at = now()
        query.save()
        return redirect("guide-queries")

    return render(request, "manage/guide_queries.html", {"queries": queries})

@never_cache
@login_required
def reply_query(request, query_id):
    query = get_object_or_404(Query, id=query_id)

    if request.method == "POST":
        reply = request.POST.get("reply")
        if reply:
            query.reply = reply
            query.replied_at = timezone.now()
            query.save()
            Notification.objects.create(
            user=query.student,
            message=f"Reply received from {request.user.username}: {reply[:30]}...",
            link=reverse("student-queries")
            )
    
    return redirect("guide-queries")

@never_cache
@login_required
def update_project(request, pk):
    project = get_object_or_404(Project, id=pk, student=request.user)
    if request.method == "POST":
        progress = int(request.POST.get("progress", 0))
        project.progress = progress
        project.save()
    return redirect("student-projects")

@never_cache
@login_required
@user_passes_test(lambda u: u.role == "guide")
def update_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if project.guide != request.user:
        return HttpResponseForbidden("You are not allowed to update this project.")

    if request.method == "POST":
        project.title = request.POST.get("title")
        project.description = request.POST.get("description")
        project.due_date = request.POST.get("due_date")
        project.save()
        messages.success(request, "Project updated successfully ✅")
        return redirect("guide-projects")

    return render(request, "manage/update_project.html", {"project": project})

@never_cache
@login_required
@user_passes_test(lambda u: u.role == "guide")
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if project.guide != request.user:
        return HttpResponseForbidden("You are not allowed to delete this project.")
    
    project.delete()
    messages.success(request, "Project deleted successfully ✅")
    return redirect("guide-projects")



# 🔹 Text Summarizer Page
def text_summarizer(request):
    return render(request, "manage/text_summarizer.html")

# 🔹 Video Summarizer Backend

def summarize_video(request):
    if request.method == "POST" and request.FILES.get("video"):
        video = request.FILES["video"]

        # --- Save uploaded video ---
        tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        for chunk in video.chunks():
            tmp_video.write(chunk)
        tmp_video.close()
        tmp_video_path = tmp_video.name
        print("✅ Saved video to:", tmp_video_path, os.path.exists(tmp_video_path))

        try:
            # --- STEP 1: Extract audio ---
            video_clip = VideoFileClip(tmp_video_path)
            tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_audio_path = tmp_audio.name
            tmp_audio.close()  # Close before ffmpeg writes to it
            print("🎧 Temp audio path:", tmp_audio_path)

            video_clip.audio.write_audiofile(tmp_audio_path, codec="pcm_s16le")
            video_clip.close()

            print("✅ Audio extraction complete:", os.path.exists(tmp_audio_path))

            # --- STEP 2: Transcribe using Whisper ---
            device = "cuda" if torch.cuda.is_available() else "cpu"
            whisper_model = whisper.load_model("small", device=device)
            result = whisper_model.transcribe(tmp_audio_path)
            transcript = result["text"]

            # --- STEP 3: Summarize using T5 ---
            tokenizer = T5Tokenizer.from_pretrained("t5-small")
            t5_model = T5ForConditionalGeneration.from_pretrained("t5-small").to(device)

            def chunk_text(text, max_chars=1000):
                sentences = text.split(". ")
                chunks, current = [], ""
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(current) + len(s) + 2 <= max_chars:
                        current += s + ". "
                    else:
                        chunks.append(current.strip())
                        current = s + ". "
                if current.strip():
                    chunks.append(current.strip())
                return chunks

            def summarize_with_t5(text, max_input_len=512, max_output_len=150):
                inputs = tokenizer(
                    "summarize: " + text,
                    return_tensors="pt",
                    max_length=max_input_len,
                    truncation=True,
                ).to(device)
                summary_ids = t5_model.generate(
                    inputs["input_ids"],
                    max_length=max_output_len,
                    min_length=40,
                    num_beams=4,
                    early_stopping=True,
                )
                return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

            chunks = chunk_text(transcript)
            sections = []
            for i, ch in enumerate(chunks, 1):
                summary = summarize_with_t5(ch)
                sections.append(f"Section {i}:\n• " + "\n• ".join(summary.split(". ")))
            final_summary = "\n\n".join(sections)

            # --- STEP 4: Save to .txt file ---
            output_path = os.path.join(tempfile.gettempdir(), "video_summary.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("=== TRANSCRIPT ===\n")
                f.write(transcript + "\n\n=== SUMMARY ===\n")
                f.write(final_summary)

            print("📄 Summary saved:", output_path)

            return FileResponse(open(output_path, "rb"), as_attachment=True, filename="video_summary.txt")

        finally:
            # --- Cleanup temp files ---
            if os.path.exists(tmp_video_path):
                os.remove(tmp_video_path)
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)

    return render(request, "manage/text_summarizer.html", {"error": "No video uploaded."})