from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from project.models import Project, Meeting, Document
from preprocessing.models import Transcript
from processing.models import ProcessingResult

User = get_user_model()


# ==============================================================================
#  Helper: ينشئ Project + Meeting جاهزين لكل test
# ==============================================================================
def create_project_and_meeting(user):
    project = Project.objects.create(
        owner=user,
        name="Watheeq Test Project",
        client="Test Client",
        manager="Test Manager",
    )
    meeting = Meeting.objects.create(
        project=project,
        title="Test Meeting",
        platform=Meeting.PLATFORM_ZOOM,
        meeting_link="https://zoom.us/test",
    )
    return project, meeting


# ==============================================================================
#  BAR 1 — Meeting Status API
#  Endpoint: GET /api/meetings/{id}/status/
# ==============================================================================
class MeetingStatusAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.project, self.meeting = create_project_and_meeting(self.user)

    # --------------------------------------------------------------------------
    # MS_001 — الحالة الافتراضية عند إنشاء الاجتماع
    # --------------------------------------------------------------------------
    def test_MS001_default_status_is_created(self):
        """
        Black Box | MS_001
        Input : GET /api/meetings/{id}/status/  (اجتماع جديد)
        Expect: 200 + {"status": "created"}
        """
        res = self.client.get(f"/api/meetings/{self.meeting.id}/status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Meeting.STATUS_CREATED)

    # --------------------------------------------------------------------------
    # MS_002 — البوت في طريقه للاجتماع
    # --------------------------------------------------------------------------
    def test_MS002_status_joining(self):
        """
        Black Box | MS_002
        Input : meeting.status = 'joining'
        Expect: 200 + {"status": "joining"}
        """
        self.meeting.status = Meeting.STATUS_JOINING
        self.meeting.save()

        res = self.client.get(f"/api/meetings/{self.meeting.id}/status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Meeting.STATUS_JOINING)

    # --------------------------------------------------------------------------
    # MS_003 — البوت داخل الاجتماع
    # --------------------------------------------------------------------------
    def test_MS003_status_in_meeting(self):
        """
        Black Box | MS_003
        Input : meeting.status = 'in_meeting'
        Expect: 200 + {"status": "in_meeting"}
        """
        self.meeting.status = Meeting.STATUS_IN_MEETING
        self.meeting.save()

        res = self.client.get(f"/api/meetings/{self.meeting.id}/status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Meeting.STATUS_IN_MEETING)

    # --------------------------------------------------------------------------
    # MS_004 — اكتمل الترانسكريبت → Bar 2 تبدأ
    # --------------------------------------------------------------------------
    def test_MS004_status_transcribed(self):
        """
        Black Box | MS_004
        Input : meeting.status = 'transcribed'
        Expect: 200 + {"status": "transcribed"}
        """
        self.meeting.status = Meeting.STATUS_TRANSCRIBED
        self.meeting.save()

        res = self.client.get(f"/api/meetings/{self.meeting.id}/status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Meeting.STATUS_TRANSCRIBED)

    # --------------------------------------------------------------------------
    # MS_005 — Meeting ID غير موجود
    # --------------------------------------------------------------------------
    def test_MS005_invalid_meeting_id_returns_404(self):
        """
        Black Box | MS_005
        Input : meeting_id = 99999 (غير موجود)
        Expect: 404
        """
        res = self.client.get("/api/meetings/99999/status/")
        self.assertEqual(res.status_code, 404)


# ==============================================================================
#  BAR 2 — Pipeline Status API
#  Endpoint: GET /api/meetings/{id}/pipeline-status/
# ==============================================================================
class PipelineStatusAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser2", password="testpass")
        self.project, self.meeting = create_project_and_meeting(self.user)
        self.document = Document.objects.create(
            project=self.project,
            doc_type="BRD",
        )

    # --------------------------------------------------------------------------
    # PS_001 — ما فيه ترانسكريبت بعد → كل المراحل pending
    # --------------------------------------------------------------------------
    def test_PS001_no_transcript_all_pending(self):
        """
        Black Box | PS_001
        Input : لا يوجد Transcript
        Expect: 200 + كل المراحل = pending / DRAFT
        """
        res = self.client.get(f"/api/meetings/{self.meeting.id}/pipeline-status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["preprocessing"], "pending")
        self.assertEqual(res.data["processing"],    "pending")
        self.assertEqual(res.data["extraction"],    "pending")
        self.assertEqual(res.data["generation"],    "DRAFT")

    # --------------------------------------------------------------------------
    # PS_002 — Preprocessing شغّال
    # --------------------------------------------------------------------------
    def test_PS002_preprocessing_in_progress(self):
        """
        Black Box | PS_002
        Input : Transcript.status = 'in_progress'
        Expect: 200 + preprocessing = 'in_progress'
        """
        Transcript.objects.create(
            meeting=self.meeting,
            status=Transcript.STATUS_IN_PROGRESS,
        )

        res = self.client.get(f"/api/meetings/{self.meeting.id}/pipeline-status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["preprocessing"], Transcript.STATUS_IN_PROGRESS)

    # --------------------------------------------------------------------------
    # PS_003 — Preprocessing اكتمل، Processing لسا ما بدأ
    # --------------------------------------------------------------------------
    def test_PS003_preprocessing_completed_processing_pending(self):
        """
        Black Box | PS_003
        Input : Transcript.status = 'completed'  بدون ProcessingResult
        Expect: preprocessing='completed' + processing='pending'
        """
        Transcript.objects.create(
            meeting=self.meeting,
            status=Transcript.STATUS_COMPLETED,
        )

        res = self.client.get(f"/api/meetings/{self.meeting.id}/pipeline-status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["preprocessing"], Transcript.STATUS_COMPLETED)
        self.assertEqual(res.data["processing"],    "pending")

    # --------------------------------------------------------------------------
    # PS_004 — Preprocessing + Processing اكتملوا
    # --------------------------------------------------------------------------
    def test_PS004_preprocessing_and_processing_completed(self):
        """
        Black Box | PS_004
        Input : Transcript completed + ProcessingResult completed
        Expect: preprocessing='completed' + processing='completed'
        """
        transcript = Transcript.objects.create(
            meeting=self.meeting,
            status=Transcript.STATUS_COMPLETED,
        )
        ProcessingResult.objects.create(
            transcript=transcript,
            status=ProcessingResult.STATUS_COMPLETED,
        )

        res = self.client.get(f"/api/meetings/{self.meeting.id}/pipeline-status/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["preprocessing"], Transcript.STATUS_COMPLETED)
        self.assertEqual(res.data["processing"],    ProcessingResult.STATUS_COMPLETED)

    # --------------------------------------------------------------------------
    # PS_005 — Meeting ID غير موجود
    # --------------------------------------------------------------------------
    def test_PS005_invalid_meeting_id_returns_404(self):
        """
        Black Box | PS_005
        Input : meeting_id = 99999 (غير موجود)
        Expect: 404
        """
        res = self.client.get("/api/meetings/99999/pipeline-status/")
        self.assertEqual(res.status_code, 404)