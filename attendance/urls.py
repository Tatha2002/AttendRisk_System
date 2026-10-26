from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.attendance_upload, name="attendance-upload"),
    path("records/", views.attendance_list, name="attendance-list"),
    path(
        "correction/request/",
        views.correction_request,
        name="correction-request",
    ),
    path(
        "corrections/review/",
        views.manager_correction_review,
        name="manager-correction-review",
    ),

    path(
        "corrections/finalize/",
        views.hr_correction_finalize,
        name="hr-correction-finalize",
    ),

    path(
        "corrections/review/",
        views.manager_correction_review,
        name="manager-correction-review",
    ),
    path(
        "corrections/review/<int:correction_id>/",
        views.manager_review_correction_action,
        name="manager-review-correction-action",
    ),
]