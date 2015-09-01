# -*- coding: utf-8 -*-
"""
    datagator.wsgi.decorators
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.
"""

import functools

from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse, HttpResponseForbidden

from datagator.rest.decorators import _basic_auth

from .http import HttpResponseUnauthorized


__all__ = ['with_basic_auth', ]


def with_basic_auth(_method=None, **options):

    if _method is not None:
        return with_basic_auth()(_method)

    allow_unauthorized = options.get("allow_unauthorized", False)

    def decorator(view):

        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):

            try:
                request = _basic_auth(request)
            except SuspiciousOperation:
                return HttpResponseForbidden("Failed authentication.")

            if not allow_unauthorized and not request.user.is_authenticated():
                return HttpResponseUnauthorized("Unauthorized access.")

            return view(request, *args, **kwargs)

        return wrapper

    return decorator
