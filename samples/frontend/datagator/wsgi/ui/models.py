# -*- coding: utf-8 -*-
"""
    datagator.wsgi.ui.models
    ~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.
"""

import json
import collections


__all__ = ['RepoRef', 'DataSetRef', 'MatrixRef', 'RecipeRef', ]


class EntityRef(collections.OrderedDict):

    def __hash__(self):
        return json.dumps(self).__hash__()

    pass


class RepoRef(EntityRef):

    def __init__(self, repo):
        super(RepoRef, self).__init__([
            ('kind', "datagator#Repo"),
            ('name', repo),
        ])
        pass

    pass


class DataSetRef(EntityRef):

    def __init__(self, repo, dataset, rev=None):
        super(DataSetRef, self).__init__([
            ('kind', "datagator#DataSet"),
            ('repo', RepoRef(repo)),
            ('name', dataset),
        ])
        if rev is not None:
            self['rev'] = rev
        pass

    pass


class DataItemKey(collections.OrderedDict):

    def __init__(self, kind, key):
        super(EntityRef, self).__init__([
            ('kind', "datagator#{0}".format(kind)),
            ('name', key)
        ])
        pass

    pass


class MatrixRef(EntityRef):

    def __init__(self, repo, dataset, rev, key):
        super(DataItemRef, self).__init__()
        self.update(DataSetRef(repo, dataset, rev))
        self['items'] = (DataItemKey("Matrix", key), )
        self['itemsCount'] = 1
        pass

    pass


class RecipeRef(EntityRef):

    def __init__(self, repo, dataset, rev, key):
        super(DataItemRef, self).__init__()
        self.update(DataSetRef(repo, dataset, rev))
        self['items'] = (DataItemKey("Recipe", key), )
        self['itemsCount'] = 1
        pass

    pass
