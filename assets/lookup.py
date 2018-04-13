"""
Module providing lookup API-related functionality.

"""
from urllib.parse import urljoin
import logging
from django.conf import settings
from django.core.cache import cache

from .models import UserLookup
from .oauth2client import AuthenticatedSession


LOG = logging.getLogger(__name__)


#: An authenticated session which can access the lookup API
LOOKUP_SESSION = AuthenticatedSession(scopes=settings.ASSETS_OAUTH2_LOOKUP_SCOPES)


class LookupError(RuntimeError):
    """
    Error raised if :py:func:`~.get_person_for_user` encounters a problem.
    """
    pass


def get_person_for_user(user):
    """
    Return the resource from Lookup associated with the specified user. A requests package
    :py:class:`HTTPError` is raised if the request fails.

    The result of this function call is cached based on the username so it is safe to call this
    multiple times.

    If user is the anonymous user (user.is_anonymous is True), :py:class:`~.UserIsAnonymousError`
    is raised.

    """
    # check that the user is not anonymous
    if user.is_anonymous:
        raise LookupError('User is anonymous')

    # return a cached response if we have it
    cached_resource = cache.get("{user.username}:lookup".format(user=user))
    if cached_resource is not None:
        return cached_resource

    # check the user has an associated lookup identity
    if not UserLookup.objects.filter(user=user).exists():
        raise LookupError('User has no lookup identity')

    # Extract the scheme and identifier for the token
    scheme = user.lookup.scheme
    identifier = user.lookup.identifier

    # Ask lookup about this person
    lookup_response = LOOKUP_SESSION.request(
        method='GET', url=urljoin(
            settings.LOOKUP_ROOT,
            'people/{scheme}/{identifier}?fetch=all_insts,all_groups'.format(
                scheme=scheme, identifier=identifier
            )
        )
    )

    # Raise if there was an error
    lookup_response.raise_for_status()

    # save cached value
    cache.set("{user.username}:lookup".format(user=user), lookup_response.json(),
              settings.LOOKUP_PEOPLE_CACHE_LIFETIME)

    # recurse, which should now retrieve the value from the cache
    return get_person_for_user(user)
