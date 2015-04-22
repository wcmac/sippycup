__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

class Annotator:
    """A base class for annotators."""
    def annotate(self, tokens):
        """Returns a list of pairs, each a category and a semantic representation."""
        return []

class TokenAnnotator(Annotator):
    def annotate(self, tokens):
        if len(tokens) == 1:
            return [('$Token', tokens[0])]
        else:
            return []

class NumberAnnotator(Annotator):
    def annotate(self, tokens):
        if len(tokens) == 1:
            try:
                value = float(tokens[0])
                if int(value) == value:
                    value = int(value)
                return [('$Number', value)]
            except ValueError:
                pass
        return []

if __name__ == '__main__':
    annotators = [TokenAnnotator(), NumberAnnotator()]
    tokens = 'four score and 30 years ago'.split()
    for j in range(1, len(tokens) + 1):
        for i in range(j - 1, -1, -1):
            annotations = [a for anno in annotators for a in anno.annotate(tokens[i:j])]
            print '(%d, %d): %s => %s' % (i, j, ' '.join(tokens[i:j]), annotations)
