"""Small HTML adapter helpers, with no alternative business-rule path."""

import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.http import Http404

from accounts.models import User
from accounts.services import require_actor

logger = logging.getLogger(__name__)


def page_actor(request):
    return require_actor(request.user)


def manageable_project(actor, project_id):
    from projects.selectors import project_for

    project = available(project_for, actor, project_id)
    if actor.role == User.Role.EMPLOYEE:
        raise PermissionDenied
    return project


def available(selector, *args, **kwargs):
    try:
        return selector(*args, **kwargs)
    except ObjectDoesNotExist as exc:
        raise Http404("This item is unavailable.") from exc


def form_errors(form, exc):
    errors = exc.message_dict if hasattr(exc, "message_dict") else {"__all__": exc.messages}
    for field, messages in errors.items():
        if field == "assignee" and "assignee_id" in form.fields:
            field = "assignee_id"
        for message in messages:
            form.add_error(field if field in form.fields else None, message)


def save_form(form, operation, *args, **data):
    try:
        operation(*args, **data)
        return True
    except ValidationError as exc:
        form_errors(form, exc)
    except ObjectDoesNotExist as exc:
        raise Http404("This item is unavailable.") from exc
    except ProtectedError:
        form.add_error(None, "Recorded work depends on this item. Its history must be preserved.")
    except DatabaseError:
        logger.exception("Workspace save failed")
        form.add_error(None, "Your changes could not be saved. Try again.")
    return False
