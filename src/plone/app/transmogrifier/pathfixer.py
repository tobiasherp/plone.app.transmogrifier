from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
from zope.interface import classProvides
from zope.interface import implements


class PathFixer(object):
    """Changes the start of the path.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        """
        :param options['path-key']: The key, under the path can be found in
                                    the item.
        :param options['stripstring']: A string to strip from the beginning of
                                       the path.
        :param options['prependstring']: A string to prepend on the beginning
                                         of the path.
        """
        self.previous = previous
        self.context = transmogrifier.context
        self.count = transmogrifier.create_itemcounter(name)

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

        self.stripstring = None
        if 'stripstring' in options and options['stripstring']:
            self.stripstring = options['stripstring'].splitlines()[0]

        self.prependstring = None
        if 'prependstring' in options and options['prependstring']:
            self.prependstring = options['prependstring'].splitlines()[0]

    def __iter__(self):

        count = self.count
        for item in self.previous:
            count('got')

            pathkey = self.pathkey(*item.keys())[0]
            stripstring = self.stripstring
            prependstring = self.prependstring

            if not pathkey or not (stripstring or prependstring):
                # not enough info or nothing to do
                count('unchanged')
                yield item
                continue

            path = item[pathkey]

            if stripstring and path.startswith(stripstring):
                path = path[len(stripstring):]
                count('stripped')
            if prependstring:
                path = '%s%s' % (prependstring, path)
                count('prefixed')

            item[pathkey] = path

            count('forwarded')
            yield item
