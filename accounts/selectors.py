from accounts.models import User
from accounts.services import require_actor, require_admin


def accounts_for(actor):
    require_admin(require_actor(actor))
    return User.objects.all()
