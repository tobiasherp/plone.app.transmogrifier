import posixpath
import urlparse
import logging

from xml.etree.ElementTree import Element
try:
    from lxml.etree import ElementBase
except ImportError:
    ElementBase  # pyflakes
    ElementBase = Element

from zope.interface import classProvides, implements
from zope.component import queryUtility

from plone.app.redirector.interfaces import IRedirectionStorage

from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import defaultKeys, defaultMatcher


class RedirectorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context_path = '/'.join(
            transmogrifier.context.getPhysicalPath()) + '/'
        self.context_url = transmogrifier.context.absolute_url()
        self.logger = logging.getLogger(name)

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.oldpathskey = defaultMatcher(
            options, 'old-paths-key', name, 'old_paths')

        self.updatepathkeys = defaultMatcher(
            options, 'update-path-keys', name, 'update_path',
            extra=(('_content_element', 'remoteUrl', 'relatedItems') +
                   defaultKeys(options['blueprint'], name, 'path')))

        self.elementattribs = options.get('element-attributes',
                                          ('href', 'src'))

    def __iter__(self):
        storage = queryUtility(IRedirectionStorage)
        for item in self.previous:
            if storage is None:
                self.logger.warn(
                    'Could not find plone.app.redirector storage utility')
                yield item
                continue

            keys = item.keys()

            # Update paths first

            # If a redirect already exists for _path, it should be
            # updated first so that any new redirects for _old_paths
            # point to the correct _path and it's unlikely that any
            # keys in this item will contain any _old_paths for the
            # same item

            for key in keys:
                if not self.updatepathkeys(key)[1]:
                    continue

                multiple = True
                paths = old_paths = item[key]
                if not isinstance(paths, (tuple, list)):
                    multiple = False
                    paths = [paths]

                for idx, obj in enumerate(paths):
                    path = obj
                    is_element = isinstance(obj, (Element, ElementBase))
                    if is_element:
                        for attrib in self.elementattribs:
                            if attrib in obj.attrib:
                                path = obj.attrib[attrib]
                                break
                        else:
                            # No attribute in this element
                            continue

                    if self._is_external(path):
                        continue

                    path = str(path)
                    stripped = path.lstrip('/')
                    leading = path[:-len(stripped)]
                    new_path = storage.get(
                        posixpath.join(self.context_path, stripped))
                    if new_path is None:
                        continue
                    if not urlparse.urlsplit(new_path).netloc:
                        new_path = leading + new_path[len(self.context_path):]

                    if is_element:
                        obj.attrib[attrib] = new_path
                        new_path = obj
                    paths[idx] = new_path

                if not multiple:
                    paths = paths[0]
                if item[key] != paths:
                    self.logger.debug('Updating %r path(s): %r => %r',
                                      key, old_paths, paths)
                    item[key] = paths

            # Collect old paths
            old_paths = set()
            oldpathskey = self.oldpathskey(*keys)[0]
            if oldpathskey and oldpathskey in item:
                paths = item[oldpathskey]
                if isinstance(paths, (str, unicode)):
                    paths = [paths]
                old_paths.update(paths)

            pathkey = self.pathkey(*keys)[0]
            if pathkey:
                path = item[pathkey]
                new_path = ((self._is_external(path) and path)
                            or posixpath.join(self.context_path,
                                              str(path).lstrip('/')))
                # Add any new redirects
                for old_path in old_paths:
                    old_path = posixpath.join(
                        self.context_path, str(old_path).lstrip('/'))
                    if old_path and old_path != new_path:
                        self.logger.debug('Adding %r redirect: %r => %r',
                                          pathkey, old_path, new_path)
                        storage.add(old_path, new_path)

            yield item

    def _is_external(self, path):
        return urlparse.urlsplit(path).netloc and not path.startswith(
            self.context_url)
