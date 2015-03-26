# -*- coding: utf-8 -*-
"""
    datagator.api.client._entity
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/03/24
"""

from __future__ import unicode_literals, with_statement

import abc
import atexit
import importlib
import json
import jsonschema
import os
import shutil

from . import environ
from ._backend import DataGatorService
from ._cache import CacheManager
from ._compat import with_metaclass, to_bytes, to_native, to_unicode


__all__ = ['Entity', 'validated', ]
__all__ = [to_native(n) for n in __all__]


class validated(object):
    """
    Context manager and proxy to validated response from backend service
    """

    __slots__ = ['__response', '__expected', '__body', ]

    def __init__(self, response, expected=(200, )):
        """
        :param response: response object from the backend service
        :param exptected: `list` or `tuple` of expected status codes
        """
        self.__response = response
        self.__expected = expected
        self.__body = None
        pass

    @property
    def status_code(self):
        return self.__response.status_code

    @property
    def headers(self):
        return self.__response.headers

    @property
    def body(self):
        if self.__body is None:
            self.__body = self.__response.json()
        return self.__body

    def __enter__(self):
        # validate content-type and body data
        try:
            # response body should be a valid JSON object
            assert(self.headers['Content-Type'] == "application/json")
            data = self.body
            Entity.__schema__.validate(data)
        except (jsonschema.ValidationError, AssertionError, ):
            # re-raise as runtime error
            raise RuntimeError("invalid response from backend service")
        else:
            # validate status code
            if self.status_code not in self.__expected:
                # error responses always come with code and message
                msg = "unexpected response from backend service"
                if data.get("kind") == "datagator#Error":
                    msg = "{0} ({1}): {2}".format(
                        msg, data.get("code", "N/A"), data.get("message", ""))
                # re-raise as runtime error
                raise RuntimeError(msg)
            pass
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        return False  # re-raise exception

    pass


class EntityType(type):
    """
    Meta class for initializing class members of the Entity class
    """

    def __new__(cls, name, parent, prop):

        # initialize backend service shared by all entities
        try:
            service = DataGatorService()
            prop['__service__'] = service
            prop['__schema__'] = jsonschema.Draft4Validator(service.schema)
        except:
            raise RuntimeError("failed to initialize backend service")

        # initialize cache manager shared by all entities
        try:
            mod, sep, cm_cls = environ.DATAGATOR_CACHE_BACKEND.rpartition(".")
            CacheManagerBackend = getattr(importlib.import_module(mod), cm_cls)
            assert(issubclass(CacheManagerBackend, CacheManager))
        except (ImportError, AssertionError):
            raise AssertionError("invalid cache backend '{0}'".format(
                environ.DATAGATOR_CACHE_BACKEND))
        else:
            prop['__cache__'] = CacheManagerBackend()

        return type(to_native(name), parent, prop)

    pass


class Entity(with_metaclass(EntityType, object)):
    """
    Abstract base class of all client-side entities
    """

    @classmethod
    def cleanup(cls):
        # decref triggers garbage collection of the cache manager backend
        setattr(cls, "__cache__", None)
        pass

    __slots__ = ['__kind', ]

    def __init__(self, kind):
        super(Entity, self).__init__()
        kind = to_unicode(kind)
        if kind.startswith("datagator#"):
            kind = kind[len("datagator#"):]
        self.__kind = kind
        pass

    @property
    def cache(self):
        data = Entity.__cache__.get(self.uri, None)
        if data is None:
            with validated(Entity.__service__.get(self.uri)) as response:
                data = response.body
                kind = data.get("kind")
                # valid response should bare a matching entity kind
                assert(kind == "datagator#{0}".format(self.kind)), \
                    "unexpected entity kind '{0}'".format(kind)
                # cache data for reuse
                Entity.__cache__.put(self.uri, data)
        return data

    @cache.setter
    def cache(self, data):
        if data is not None:
            Entity.__cache__.put(self.uri, data)
        else:
            Entity.__cache__.delete(self.uri)
        pass

    @property
    def kind(self):
        return self.__kind

    @property
    @abc.abstractmethod
    def uri(self):
        return None

    @property
    @abc.abstractmethod
    def id(self):
        return None

    def __json__(self):
        return self.cache

    def __repr__(self):
        return "<{0} '{1}' at 0x{2:x}>".format(
            self.__class__.__name__, self.uri, id(self))

    pass


atexit.register(Entity.cleanup)
