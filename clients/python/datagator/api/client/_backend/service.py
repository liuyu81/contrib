# -*- coding: utf-8 -*-
"""
    datagator.api.client._backend.service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/28
"""

from __future__ import unicode_literals, with_statement

import datetime as dt
import json
import logging
import os
import requests
import ssl
import time

from .. import environ
from .._compat import to_bytes, to_native

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.status_codes import codes
from requests.exceptions import Timeout


__all__ = ['DataGatorService', ]
__all__ = [to_native(n) for n in __all__]


_log = logging.getLogger(__package__)


class ThrottleAdapter(HTTPAdapter):
    """
    Limit send frequencies to conform backend rate limiting
    """

    max_attempts = 3
    min_wait = dt.timedelta(microseconds=100000)  # 0.1 sec
    scheduled = None

    def send(self, request, stream=False, timeout=None, verify=True, cert=None,
             proxies=None):

        if isinstance(timeout, tuple):
            timeout = timeout[0]

        attempted = 0
        max_wait = None if timeout is None else dt.timedelta(seconds=timeout)
        response = None

        while attempted < ThrottleAdapter.max_attempts:

            scheduled = ThrottleAdapter.scheduled
            timestamp = dt.datetime.utcnow()
            wait_for = dt.timedelta(0)

            if scheduled is not None and scheduled >= timestamp:
                wait_for = scheduled - timestamp

            if max_wait is not None and wait_for > max_wait:
                raise Timeout(
                    "request cannot be send within user-specified timeout")

            if wait_for > dt.timedelta(0):
                _log.debug("entering sleep for rate control")
                # python 2.6 and before do not have `timedelta.total_seconds()`
                wait_seconds = float(wait_for.microseconds) / 1000000 + \
                    wait_for.seconds + wait_for.days * 86400
                _log.debug("  - {0} seconds".format(wait_seconds))
                time.sleep(wait_seconds)

            response = super(ThrottleAdapter, self).send(
                request, stream=stream, timeout=timeout, verify=verify,
                cert=cert, proxies=proxies)

            attempted += 1

            if response.status_code != codes.too_many_requests:
                # apply minimum wait time when no over rate
                ThrottleAdapter.scheduled = \
                    timestamp + ThrottleAdapter.min_wait
                break

            # when there is an `X-RateLimit-Reset` header, we know when the
            # rate-limiting quota resets, so we schedule next send() to that
            # exact timestamp;
            if "X-RateLimit-Reset" in response.headers:
                ThrottleAdapter.scheduled = dt.datetime.utcfromtimestamp(
                    int(response['X-RateLimit-Reset']))
                continue

            # otherwise, we apply exponential backoff time to the next send()
            # according to the # of previous attempts, i.e. 30, 60, 120 sec
            ThrottleAdapter.scheduled = \
                timestamp + dt.timedelta(seconds=15 * (2 ** attempted))

        return response

    pass


class TLSv1Adapter(HTTPAdapter):
    """
    Enforce TLS v1 protocol for HTTPS sessions
    """

    def init_poolmanager(self, connections, maxsize, block):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1)
        pass

    pass


def safe_url(path):

    request_uri = path

    # converting absolute url to relative path (ignore HTTP scheme)
    if "://" in request_uri:
        _, _, request_uri = request_uri.partition("://")
        _, _, expected_prefix = environ.DATAGATOR_API_URL.partition("://")
        if request_uri.startswith(expected_prefix):
            request_uri = request_uri[len(expected_prefix):]
        else:
            raise AssertionError("unexpected address: '{0}'".format(path))

    # unify relative path
    if request_uri.startswith("/"):
        request_uri = request_uri[1:]

    # finalize url
    return "{0}/{1}".format(environ.DATAGATOR_API_URL, request_uri)


def make_payload(data):
    if hasattr(data, "read"):
        return data
    return to_bytes(json.dumps(data, ensure_ascii=False))


class DataGatorService(object):
    """
    HTTP client for DataGator's backend services.
    """

    __slots__ = ['http', ]

    def __init__(self, auth=None, verify=not environ.DEBUG):
        """
        Optional arguments:

        :param auth: 2-``tuple`` of ``<username>`` and ``<secret>`` for use
            in HTTP basic authentication, defaults to ``None``.
        :param verify: perform SSL verification, defaults to ``False`` in
            debugging mode and ``True`` otherwise.
        """

        self.http = requests.Session()

        # force TLSv1, this resolves SSL error (EOF occurred in violation of
        # protocol), see http://stackoverflow.com/questions/14102416/
        self.http.mount('https://', TLSv1Adapter())

        # apply rate limitation
        throttle = ThrottleAdapter()
        self.http.mount('http://', throttle)
        self.http.mount('https://', throttle)

        self.auth = auth

        # turn off SSL verification in DEBUG mode, i.e. the testbed web server
        # may not have a domain name matching the official SSL certificate
        if verify:
            self.http.verify = verify
        else:
            _log.warning("disabled SSL verification")
            self.http.verify = False

        self.http.allow_redirects = environ.DATAGATOR_API_FOLLOW_REDIRECT
        self.http.timeout = environ.DATAGATOR_API_TIMEOUT

        # common http headers shared by all requests
        self.http.headers.update({
            "User-Agent": environ.DATAGATOR_API_USER_AGENT,
            "Accept": "application/json, */*",
            "Accept-Encoding": environ.DATAGATOR_API_ACCEPT_ENCODING})

        super(DataGatorService, self).__init__()
        pass

    @property
    def auth(self):
        return self.http.auth

    @auth.setter
    def auth(self, auth):
        if auth:
            _log.info("enabled HTTP authentication")
            self.http.auth = auth
        else:
            self.http.auth = None
        pass

    def delete(self, path, headers={}):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param headers: extra HTTP headers to be sent with request.
        :returns: HTTP response object.
        """
        r = self.http.request(
            method="DELETE",
            url=safe_url(path),
            headers=headers)
        return r

    def get(self, path, headers={}, stream=False,
            timeout=environ.DATAGATOR_API_TIMEOUT):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param headers: extra HTTP headers to be sent with request.
        :param stream: enable streamed access to response body.
        :param timeout: connection timeout in seconds.
        :returns: HTTP response object.
        """
        r = self.http.request(
            method="GET",
            url=safe_url(path),
            headers=headers,
            stream=stream,
            timeout=timeout)
        return r

    def head(self, path, headers={}):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param headers: extra HTTP headers to be sent with request.
        :returns: HTTP response object.
        """
        r = self.http.request(
            method="HEAD",
            url=safe_url(path),
            headers=headers)
        return r

    def patch(self, path, data, headers={}):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param data: JSON-serializable data object.
        :param headers: extra HTTP headers to be sent with request.
        :returns: HTTP response object.
        """
        headers.setdefault('Content-Type', "application/json")
        r = self.http.request(
            method="PATCH",
            url=safe_url(path),
            data=make_payload(data),
            headers=headers)
        return r

    def post(self, path, data, files={}, headers={}):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param data: JSON-serializable data object.
        :param file: dictionary of files ``{<key>: (<filename>, <file>)}``.
        :param headers: extra HTTP headers to be sent with request.
        :returns: HTTP response object.
        """

        if files:
            headers.setdefault('Content-Type', "multipart/form-data")
        else:
            data = make_payload(data)
            headers.setdefault('Content-Type', "application/json")

        r = self.http.request(
            method="POST",
            url=safe_url(path),
            data=data,
            files=files,
            headers=headers)
        return r

    def put(self, path, data, headers={}):
        """
        :param path: relative url w.r.t. ``DATAGATOR_API_URL``.
        :param data: JSON-serializable data object.
        :param headers: extra HTTP headers to be sent with request.
        :returns: HTTP response object.
        """
        headers.setdefault('Content-Type', "application/json")
        r = self.http.request(
            method="PUT",
            url=safe_url(path),
            data=make_payload(data),
            headers=headers)
        return r

    @property
    def status(self):
        """
        general status of the backend service
        """
        return self.get("/").json()

    @property
    def schema(self):
        """
        JSON schema being used by the backend service
        """
        return self.get("/schema").json()

    def __del__(self):
        # close the underlying HTTP session upon garbage collection
        try:
            self.http.close()
        except Exception as e:
            _log.debug(e)
        pass

    pass
