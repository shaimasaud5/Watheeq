from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SignupForm, LoginForm


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('frontend:home')
    else:
        form = SignupForm()
    return render(request, 'frontend/auth/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('frontend:home')
    else:
        form = LoginForm()
    return render(request, 'frontend/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('frontend:login')


@login_required(login_url='/login/')
def home(request):
    from project.models import Project
    try:
        recent_projects = Project.objects.filter(owner=request.user).order_by('-created_at')[:3]
    except Exception:
        recent_projects = []
    return render(request, 'frontend/pages/home.html', {
        'recent_projects': recent_projects
    })


@login_required(login_url='/login/')
def projects(request):
    from project.models import Project
    all_projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'frontend/pages/projects.html', {
        'projects': all_projects
    })


@login_required(login_url='/login/')
def profile(request):
    if request.method == 'POST':
        old_password    = request.POST.get('old_password')
        new_password    = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'كلمة المرور الحالية غير صحيحة.')
        elif new_password != confirm_password:
            messages.error(request, 'كلمة المرور الجديدة وتأكيدها غير متطابقتين.')
        elif len(new_password) < 6:
            messages.error(request, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'تم تغيير كلمة المرور بنجاح.')
        return redirect('frontend:profile')

    return render(request, 'frontend/pages/profile.html')


@login_required(login_url='/login/')
def create_project(request):
    from project.models import Project, Meeting, Document
    error = None

    if request.method == 'POST':
        name         = request.POST.get('name', '').strip()
        client       = request.POST.get('client', '').strip()
        manager      = request.POST.get('manager', '').strip()
        domain       = request.POST.get('domain', '').strip()
        project_type = request.POST.get('project_type', '').strip()
        target_user  = request.POST.get('target_user', '').strip()
        doc_type     = request.POST.get('doc_type', 'BRD')
        meeting_title = request.POST.get('meeting_title', '').strip()
        platform      = request.POST.get('platform', '').strip()
        meeting_link  = request.POST.get('meeting_link', '').strip()

        if not all([name, client, manager, meeting_title, platform, meeting_link]):
            error = 'يرجى تعبئة جميع الحقول المطلوبة.'
        else:
            try:
                project = Project.objects.create(
                    owner=request.user,
                    name=name,
                    client=client,
                    manager=manager,
                    domain=domain,
                    project_type=project_type,
                    target_user=target_user,
                )
                Meeting.objects.create(
                    project=project,
                    title=meeting_title,
                    platform=platform,
                    meeting_link=meeting_link,
                )
                doc = Document.objects.create(
                    project=project,
                    doc_type=doc_type,
                )
                messages.success(request, 'تم إنشاء المشروع بنجاح!')
                return redirect('frontend:processing', document_id=doc.id)
            except Exception as e:
                error = f'حدث خطأ أثناء إنشاء المشروع: {str(e)}'

    return render(request, 'frontend/pages/create_project.html', {'error': error})


def landing(request):
    return render(request, 'frontend/pages/landing.html')


@login_required(login_url='/login/')
def search(request):
    from project.models import Project, Document
    query = request.GET.get('q', '').strip()
    project_results  = []
    document_results = []
    if query:
        project_results = Project.objects.filter(
            owner=request.user,
            name__icontains=query
        ).order_by('-created_at')
        document_results = Document.objects.filter(
            project__owner=request.user,
            project__name__icontains=query
        ).order_by('-created_at')

    return render(request, 'frontend/pages/search.html', {
        'query': query,
        'project_results': project_results,
        'document_results': document_results,
    })


@login_required(login_url='/login/')
def overview(request, project_id):
    from project.models import Project
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    return render(request, 'frontend/pages/overview.html', {'project': project})


@login_required(login_url='/login/')
def documents(request, project_id):
    from project.models import Project, Document
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    docs = Document.objects.filter(project=project).order_by('-created_at')
    return render(request, 'frontend/pages/documents.html', {
        'project': project,
        'documents': docs,
    })


@login_required(login_url='/login/')
def generated_document(request, doc_id):
    from project.models import Document
    doc = get_object_or_404(Document, id=doc_id, project__owner=request.user)
    regenerate_count = 0
    if doc.meta and isinstance(doc.meta, dict):
        regenerate_count = int(doc.meta.get('regenerate_count', 0))
    regen_remaining = max(0, 3 - regenerate_count)
    return render(request, 'frontend/pages/generated_document.html', {
        'doc': doc,
        'regen_remaining': regen_remaining,
    })


@login_required(login_url='/login/')
def processing(request, document_id):
    from project.models import Document
    doc = get_object_or_404(Document, id=document_id, project__owner=request.user)
    return render(request, 'frontend/pages/processing.html', {
        'document_id': document_id,
        'project': doc.project,
        'doc': doc,
    })