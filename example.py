__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

class Example:
    def __init__(self, input=None, parse=None, semantics=None, denotation=None):
        self.input = input
        self.parse = parse
        self.semantics = semantics
        self.denotation = denotation

    def __str__(self):
        fields = []
        self.input != None and fields.append('input=\'%s\'' % self.input.replace("'", "\'"))
        self.parse != None and fields.append('parse=%s' % self.parse)
        self.semantics != None and fields.append('semantics=%s' % str(self.semantics))
        self.denotation != None and fields.append('denotation=%s' % str(self.denotation))
        return 'Example(%s)' % (', '.join(fields))


if __name__ == '__main__':
    examples = [
        Example(),
        Example(input='one plus one', semantics='(+ 1 1)', denotation=2),
        Example(input='two plus three', denotation=5),
        Example(input='utah', semantics='/state/utah', denotation=set(['/state/utah'])),
    ]
    for example in examples:
        print(example)
