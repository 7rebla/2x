"""API endpoints of the answers app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.answers.api import AnswerStatusView, AnswerView

urlpatterns: list[URLPattern | URLResolver] = [
    path("answers/", AnswerView.as_view(), name="answers"),
    path("answers/status/", AnswerStatusView.as_view(), name="answers-status"),
]
