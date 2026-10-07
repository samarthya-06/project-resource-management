from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from accounts import selectors, services
from accounts.serializers import AccountInput, AccountOutput
from projects.serializers import InputSerializer, parsed


class AccountViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AccountOutput
    parser_classes = [JSONParser]

    def get_queryset(self):
        return selectors.accounts_for(self.request.user).order_by("pk")

    def create(self, request):
        user = services.create_account(request.user, **parsed(AccountInput, request))
        return Response(AccountOutput(user).data, status=201)

    def update(self, request, pk=None):
        self.get_object()
        user = services.update_account(
            request.user, pk, **parsed(AccountInput, request, partial=True)
        )
        return Response(AccountOutput(user).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        self.get_object()
        parsed(InputSerializer, request)
        user = services.deactivate_account(request.user, pk)
        return Response(AccountOutput(user).data)
