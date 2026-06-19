import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from .models import Timetable
from .forms import TimetableForm, ResultForm
from .models import Attendance, Session, Subject, StudentResult, Student
from .models import News
from .EmailBackend import EmailBackend
from .models import Attendance, Session, Subject 
from django.db.models import Sum
import json
from .models import Notice
from .forms import NoticeForm
from django.utils.timezone import now
from datetime import timedelta
from .models import (
    Student, Staff, Course,
    Notice, Event, Birthday,
    Fee, Assignment, ExamForm,
    Syllabus, Settings,
    DailyFeeCollection, FacultyLeave
)
from datetime import datetime, date
from .forms import NewsForm, EventForm, BirthdayForm, FeeForm, LeaveForm

# Create your views here.


def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    return render(request, 'main_app/login.html')


def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        # Google recaptcha
        captcha_token = request.POST.get('g-recaptcha-response')
        captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        captcha_key = "6LfTGD4qAAAAALtlli02bIM2MGi_V0cUYrmzGEGd"

        data = {
            'secret': captcha_key,
            'response': captcha_token
        }

        try:
            captcha_server = requests.post(url=captcha_url, data=data)
            response = json.loads(captcha_server.text)

            if response['success'] == False:
                messages.error(request, 'Invalid Captcha. Try Again')
                return redirect('/')
        except:
            messages.error(request, 'Captcha could not be verified. Try Again')
            return redirect('/')

        # Authenticate
        user = EmailBackend.authenticate(
            request,
            username=request.POST.get('email'),
            password=request.POST.get('password')
        )

        if user is not None:
            login(request, user)

            # Remember me
            remember_me = request.POST.get('remember')
            if remember_me:
                request.session.set_expiry(30 * 24 * 60 * 60)
            else:
                request.session.set_expiry(0)

            # ✅ ROLE BASED REDIRECT (FIXED)
            if user.user_type == '1':
                return redirect('dashboard')
            elif user.user_type == '2':
                return redirect('staff_home')
            else:
                return redirect('student_home')

        else:
            messages.error(request, "Invalid details")
            return redirect("/")


def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')

def view_timetable(request):
    timetable = Timetable.objects.all()

    selected_course = request.GET.get('course')
    if selected_course:
        timetable = timetable.filter(course=selected_course)

    courses = Timetable.objects.values_list('course', flat=True).distinct()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    time_slots = []
    for t in timetable:
        slot = (t.start_time, t.end_time)
        if slot not in time_slots:
            time_slots.append(slot)

    context = {
        'timetable': timetable,
        'days': days,
        'time_slots': sorted(time_slots),
        'courses': courses,
        'selected_course': selected_course,
    }

    return render(request, 'hod_template/timetable.html', context)


def add_timetable(request):
    form = TimetableForm()

    if request.method == "POST":
        form = TimetableForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_timetable')

    return render(request, 'hod_template/add_timetable.html', {'form': form})


def edit_timetable(request, id):
    obj = get_object_or_404(Timetable, id=id)
    form = TimetableForm(instance=obj)

    if request.method == "POST":
        form = TimetableForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('view_timetable')

    return render(request, 'hod_template/edit_timetable.html', {'form': form})


def delete_timetable(request, id):
    obj = get_object_or_404(Timetable, id=id)
    obj.delete()
    return redirect('view_timetable')


def print_timetable(request):
    timetable = Timetable.objects.all()
    return render(request, 'hod_template/print_timetable.html', {'timetable': timetable})

def add_result(request):
    form = ResultForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('view_results')
    return render(request, 'hod_template/add_result.html', {'form': form})

def view_results(request):
    results = StudentResult.objects.all()
    students = Student.objects.all()

    # 🔍 FILTER
    student_id = request.GET.get('student')
    if student_id:
        results = results.filter(student_id=student_id)

    # 🏆 TOPPERS
    toppers = StudentResult.objects.values(
        'student__admin__first_name',
        'student__admin__last_name'
    ).annotate(
        total=Sum('marks_obtained')
    ).order_by('-total')[:5]

    # 📊 CHART DATA
    chart_data = StudentResult.objects.values(
        'student__admin__first_name'
    ).annotate(
        total=Sum('marks_obtained')
    )

    labels = [x['student__admin__first_name'] for x in chart_data]
    data = [x['total'] for x in chart_data]

    return render(request, 'hod_template/view_results.html', {
        'results': results,
        'students': students,
        'toppers': toppers,
        'labels': json.dumps(labels),
        'data': json.dumps(data),
    })

def student_result(request):
    student = request.user.student
    results = StudentResult.objects.filter(student=student)

    return render(request, 'student_template/student_result.html', {
        'results': results
    })

def add_notice(request):
    form = NoticeForm()

    if request.method == "POST":
        form = NoticeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('view_notices')

    return render(request, 'hod_template/add_notice.html', {'form': form})

def view_notices(request):
    user = request.user

    if user.user_type == '3':  # student
        notices = Notice.objects.filter(
            course=user.student.course
        ) | Notice.objects.filter(is_global=True)
    else:
        notices = Notice.objects.all()

    notices = notices.order_by('-created_at')

    # NEW badge
    for n in notices:
        n.is_new = (now() - n.created_at) < timedelta(days=2)

    return render(request, 'hod_template/view_notices.html', {
        'notices': notices
    })

def notice_count(request):
    user = request.user

    # ✅ HANDLE LOGGED OUT USER
    if not user.is_authenticated:
        return {'notice_count': 0}

    if user.user_type == '3':
        count = Notice.objects.filter(
            course=user.student.course
        ).count()
    else:
        count = Notice.objects.count()

    return {'notice_count': count}


def fee_management(request):
    return render(request, 'main_app/fee_management.html')

def assignments(request):
    return render(request, 'main_app/assignments.html')

def exam_form(request):
    return render(request, 'main_app/exam_form.html')

def syllabus(request):
    return render(request, 'main_app/syllabus.html')

def calendar_view(request):
    return render(request, 'main_app/calendar.html')

def dashboard(request):
    today = date.today()

    # ===== RIGHT PANEL =====
    news_list = News.objects.all().order_by('-created_at')

    new_news = News.objects.filter(
        created_at__gte=now() - timedelta(days=1)
    )

    birthdays = Birthday.objects.all()
    today_fees = DailyFeeCollection.objects.filter(date=today)
    events = Event.objects.all()
    leaves = FacultyLeave.objects.filter(date=today)

    # ===== COUNTS =====
    total_students = Student.objects.count()
    total_staff = Staff.objects.count()
    total_course = Course.objects.count()
    total_subject = Subject.objects.count()

    # ===== ATTENDANCE PER SUBJECT =====
    subjects = Subject.objects.all()
    subject_list = []
    attendance_list = []

    for subject in subjects:
        count = Attendance.objects.filter(subject_id=subject.id).count()
        subject_list.append(subject.name)
        attendance_list.append(count)

    # ===== STUDENTS PER COURSE =====
    courses = Course.objects.all()
    course_name_list = []
    student_count_list_in_course = []

    for course in courses:
        count = Student.objects.filter(course_id=course.id).count()
        course_name_list.append(course.name)
        student_count_list_in_course.append(count)

    # ===== STUDENTS PER SUBJECT =====
    student_count_list_in_subject = []

    for subject in subjects:
        count = Student.objects.filter(course_id=subject.course.id).count()
        student_count_list_in_subject.append(count)

    return render(request, 'main_app/dashboard.html', {
        'news_list': news_list,
        'new_news': new_news,
        'birthdays': birthdays,
        'today_fees': today_fees,
        'events': events,
        'leaves': leaves,

        'total_students': total_students,
        'total_staff': total_staff,
        'total_course': total_course,
        'total_subject': total_subject,

    'subject_list': json.dumps(subject_list),
    'attendance_list': json.dumps(attendance_list),

    'course_name_list': json.dumps(course_name_list),
    'student_count_list_in_course': json.dumps(student_count_list_in_course),
    'student_count_list_in_subject': json.dumps(student_count_list_in_subject),
    })


def add_news(request):
    form = NewsForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'hod_template/add_news.html', {'form': form})


def add_event(request):
    form = EventForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'hod_template/add_event.html', {'form': form})


def add_birthday(request):
    form = BirthdayForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'hod_template/add_birthday.html', {'form': form})


def add_fee(request):
    form = FeeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'hod_template/add_fee.html', {'form': form})


def add_leave(request):
    form = LeaveForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'hod_template/add_leave.html', {'form': form})

def staff_home(request):
    return dashboard(request)   # reuse admin dashboard

def student_home(request):
    student = request.user.student

    # 📢 News
    news_list = News.objects.all().order_by('-created_at')

    # 🎂 Birthdays
    birthdays = Birthday.objects.all()

    # 💰 Fees (for this student)
    fees = Fee.objects.filter(student=student)

    # 🏖️ Leaves (if needed)
    leaves = FacultyLeave.objects.all()  # or filter if you want

    context = {
        'news_list': news_list,
        'birthdays': birthdays,
        'fees': fees,
        'leaves': leaves,
    }

    return render(request, 'student_template/home_content.html', context)