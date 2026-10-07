"""Translate service/model errors without exposing database details."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.deletion import ProtectedError
from django.http import Http404
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "Dependent work or history prevents deletion."},
            status=400,
        )
    if isinstance(exc, ValidationError):
        errors = (
            exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        )
        return Response(errors, status=400)
    if isinstance(exc, (ObjectDoesNotExist, Http404)):
        exc = NotFound("Resource unavailable.")
    return exception_handler(exc, context)
