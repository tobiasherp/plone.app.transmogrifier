import logging

from zope.interface import classProvides, implements
from zope.component import queryUtility

from plone.app.redirector.interfaces import IRedirectionStorage

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultMatcher, Matcher, Expression


class RedirectorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.logger = logging.getLogger(name)

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.oldpathskey = Expression(
            options.get(
                'old-paths-key',
                'python:"remoteUrl" not in item '
                'and "_is_defaultpage" not in item and "_old_paths"'),
            transmogrifier, name, options)

        self.updatepathkeys = Matcher(
            *options.get('update-path-keys',
                         "['remoteUrl', 'relatedItems']").splitlines())

    def __iter__(self):
        storage = queryUtility(IRedirectionStorage)
        for item in self.previous:
            if storage is None:
                self.logger.warn(
                    'Could not find plone.app.redirector storage utility')
                yield item
                continue

            old_paths = set()
            oldpathskey = self.oldpathskey(item)
            if oldpathskey and oldpathskey in item:
                old_paths.update(old_path.strip() for old_path in
                                 item[oldpathskey] if old_path.strip())

            keys = item.keys()
            pathkey = self.pathkey(*keys)[0]
            if pathkey:
                path = item[pathkey]
                for old_path in old_paths:
                    if old_path != path:
                        storage.add(old_path, path)

            for key in keys:
                if not self.updatepathkeys(key)[1]:
                    continue

                multiple = True
                paths = item[key]
                if isinstance(paths, basestring):
                    multiple = False
                    paths = [paths]

                for idx, path in enumerate(paths):
                    new_path = storage.get(path)
                    if new_path is not None:
                        paths[idx] = new_path

                if not multiple:
                    paths = paths[0]
                item[key] = paths

            yield item
