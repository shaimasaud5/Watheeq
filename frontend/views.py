from django.shortcuts import render, redirect
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
    from django.contrib.auth.forms import AuthenticationForm
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
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
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
        # بيانات المشروع
        name         = request.POST.get('name', '').strip()
        client       = request.POST.get('client', '').strip()
        manager      = request.POST.get('manager', '').strip()
        domain       = request.POST.get('domain', '').strip()
        project_type = request.POST.get('project_type', '').strip()
        target_user  = request.POST.get('target_user', '').strip()
        doc_type     = request.POST.get('doc_type', 'BRD')

        # بيانات الاجتماع
        meeting_title = request.POST.get('meeting_title', '').strip()
        platform      = request.POST.get('platform', '').strip()
        meeting_link  = request.POST.get('meeting_link', '').strip()

        # ملف القالب
        template_file = request.FILES.get('template_file')

        # التحقق من الحقول المطلوبة
        if not all([name, client, manager, meeting_title, platform, meeting_link]):
            error = 'يرجى تعبئة جميع الحقول المطلوبة.'
        else:
            try:
                # إنشاء المشروع
                project = Project.objects.create(
                    owner=request.user,
                    name=name,
                    client=client,
                    manager=manager,
                    domain=domain,
                    project_type=project_type,
                    target_user=target_user,
                )

                # إنشاء الاجتماع
                meeting = Meeting.objects.create(
                    project=project,
                    title=meeting_title,
                    platform=platform,
                    meeting_link=meeting_link,
                )

                # إنشاء المستند مع القالب
                document = Document.objects.create(
                    project=project,
                    doc_type=doc_type,
                    template_file=template_file,
                )
                from project.services import request_recall_bot
                request_recall_bot(meeting_id=meeting.id)

                messages.success(request, 'تم إنشاء المشروع بنجاح!')
                return redirect('frontend:processing', project_id=project.id)  # ← غيّري هذا
            
            except Exception as e:
                error = f'حدث خطأ أثناء إنشاء المشروع: {str(e)}'

    return render(request, 'frontend/pages/create_project.html', {'error': error})


def landing(request):
    return render(request, 'frontend/pages/landing.html')


@login_required(login_url='/login/')
def search(request):
    from project.models import Project, Document
    query = request.GET.get('q', '').strip()
    project_results = []
    document_results = []
    if query:
        project_results = Project.objects.filter(
            owner=request.user,
            name__icontains=query
        ).order_by('-created_at')

        document_results = Document.objects.filter(
            project__owner=request.user
        ).filter(
            project__name__icontains=query
        ).order_by('-created_at')

    return render(request, 'frontend/pages/search.html', {
        'query': query,
        'project_results': project_results,
        'document_results': document_results,
    })

@login_required(login_url='/login/')
def overview(request, project_id):
    from project.models import Project, Document

    project = Project.objects.get(id=project_id, owner=request.user)
    documents = Document.objects.filter(project=project)

    has_brd = documents.filter(doc_type="BRD").exists()
    has_mom = documents.filter(doc_type="MOM").exists()

    return render(request, 'frontend/pages/overview.html', {
        'project': project,
        'documents': documents,
        'has_brd': has_brd,
        'has_mom': has_mom,
    })


@login_required(login_url='/login/')
def documents(request, project_id):
    from project.models import Project, Document
    from generation.models import GeneratedDocument

    project = Project.objects.get(id=project_id, owner=request.user)
    documents = Document.objects.filter(project=project)

    docs_with_generated = []

    for doc in documents:
        generated = getattr(doc, "generated", None)

        docs_with_generated.append({
            "doc": doc,
            "generated": generated,
        })

    return render(request, 'frontend/pages/documents.html', {
        'project': project,
        'documents': documents,  # لا نحذفها (نخلي القديم شغال)
        'docs_with_generated': docs_with_generated,  # الجديد
    })

# Updated processing view to pass meeting_id and document_id to the template
# This is required for frontend polling:
# - meeting_id → used for BAR 1 (meeting lifecycle progress)
# - document_id → used for BAR 2 (AI pipeline progress)
@login_required(login_url='/login/')
def processing(request, project_id):
    from project.models import Project, Document

    project = Project.objects.get(id=project_id, owner=request.user)
    meeting = project.meeting
    document = Document.objects.filter(project=project).order_by("-id").first()

    return render(request, 'frontend/pages/processing.html', {
        'project': project,
        'meeting': meeting,
        'meeting_id': meeting.id,
        'document': document,
        'document_id': document.id if document else None,
    })



@login_required(login_url='/login/')
def generated_document(request, doc_id):
    from project.models import Document
    from generation.models import GeneratedDocument

    base_doc = Document.objects.get(id=doc_id, project__owner=request.user)
    project = base_doc.project

    try:
        gen_doc = GeneratedDocument.objects.get(document=base_doc)
    except GeneratedDocument.DoesNotExist:
        gen_doc = GeneratedDocument(
            document=base_doc,
            status="DRAFT",
            content="",
            meta={},
        )

    regen_count = int((gen_doc.meta or {}).get("regenerate_count", 0))
    regen_remaining = max(0, 3 - regen_count)

    return render(request, 'frontend/pages/generated_document.html', {
        'base_doc': base_doc,
        'doc': gen_doc,
        'gen_doc': gen_doc,
        'project': project,
        'project_id': project.id,
        'regen_remaining': regen_remaining,
    })

@login_required(login_url='/login/')
def generate_new_document(request, project_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from project.models import Project
    import requests

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method != "POST":
        return redirect("frontend:overview", project_id=project.id)

    document_type = request.POST.get("document_type")

    if document_type not in ["BRD", "MOM"]:
        messages.error(request, "يرجى اختيار نوع الوثيقة.")
        return redirect("frontend:overview", project_id=project.id)

    if project.documents.filter(doc_type=document_type).exists():
        messages.error(request, "هذا النوع من الوثائق موجود مسبقًا.")
        return redirect("frontend:overview", project_id=project.id)

    api_url = request.build_absolute_uri(
        f"/api/generation/projects/{project.id}/generate-new-document/"
    )

    response = requests.post(
        api_url,
        json={"document_type": document_type},
        timeout=None,
    )

    if response.status_code not in [200, 201]:
        print("Generate new document error:", response.text)
        return redirect("frontend:processing", project_id=project.id)

    
    data = response.json()
    document_id = data.get("document_id")

    if not document_id:
        from project.models import Document

        new_doc = Document.objects.filter(
            project=project,
            doc_type=document_type
        ).order_by("-id").first()

        if new_doc:
            document_id = new_doc.id

    if not document_id:
        return redirect("frontend:documents", project_id=project.id)

    return redirect("frontend:generated_document", doc_id=document_id)
    