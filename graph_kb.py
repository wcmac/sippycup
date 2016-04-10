"""
This file defines two classes:

  - GraphKB is a generic graph-structured knowledge base, or equivalently,
    a set of relational pairs and triples, with indexing for fast lookups.

  - GraphKBExecutor executes queries against a GraphKB.  It defines a simple
    query language, and responds to queries with (possibly empty) sets of
    values from the GraphKB.

The primary use case for these classes within SippyCup is to provide an executor
backed by Geobase for use with the GeoQuery domain.  However, these classes are
generic enough that they could be used for other applications.  For example,
Freebase is also a graph-structured knowledge base.

See further documentation on the individual classes, in particular for a
detailed description of the query language defined by GraphKBExecutor.

See the demo() method at the bottom of this file for a concrete example.
"""

__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

from collections import defaultdict, Iterable
from types import FunctionType

class GraphKB:
    """
    Represents a knowledge base as set of tuples, each either:

    - a pair, consisting of a unary relation and an element which belongs to it,
      or
    - a triple consisting of a binary relation and a pair of elements which
      belong to it.

    There are no restrictions on the types of the tuple elements, except that
    they be indexable (hashable).

    For example, a GraphKB could be constructed from this set of tuples:

        ('male', 'homer')
        ('female', 'marge')
        ('male', 'bart')
        ('female', 'lisa')
        ('female', 'maggie')
        ('adult', 'homer')
        ('adult', 'marge')
        ('child', 'bart')
        ('child', 'lisa')
        ('child', 'maggie')
        ('has_age', 'homer', 36)
        ('has_age', 'marge', 34)
        ('has_age', 'bart', 10)
        ('has_age', 'lisa', 8)
        ('has_age', 'maggie', 1)
        ('has_brother', 'lisa', 'bart')
        ('has_brother', 'maggie', 'bart')
        ('has_sister', 'bart', 'maggie')
        ('has_sister', 'bart', 'lisa')
        ('has_father', 'bart', 'homer')
        ('has_father', 'lisa', 'homer')
        ('has_father', 'maggie', 'homer')
        ('has_mother', 'bart', 'marge')
        ('has_mother', 'lisa', 'marge')
        ('has_mother', 'maggie', 'marge'),
    """
    def __init__(self, tuples):
        self.nodes = set()
        self.unaries = defaultdict(set)
        self.binaries_fwd = defaultdict(lambda : defaultdict(set))  # rel => src => {dst}
        self.binaries_rev = defaultdict(lambda : defaultdict(set))  # rel => dst => {src}
        for tuple in tuples:
            if len(tuple) == 2:
                self.add_unary(tuple)
            elif len(tuple) == 3:
                self.add_binary(tuple)
            else:
                assert False, 'Invalid tuple'

    def add_unary(self, tuple):
        self.nodes.add(tuple[1])
        self.unaries[tuple[0]].add(tuple[1])

    def add_binary(self, tuple):
        self.nodes.add(tuple[1])
        self.nodes.add(tuple[2])
        self.binaries_fwd[tuple[0]][tuple[1]].add(tuple[2])
        self.binaries_rev[tuple[0]][tuple[2]].add(tuple[1])

    def list(self):
        for rel in sorted(list(self.unaries.keys())):
            for node in sorted(list(self.unaries[rel])):
                print("(%s %s)" % (rel, node))
        for rel in sorted(list(self.binaries_fwd.keys())):
            for src in sorted(list(self.binaries_fwd[rel])):
                for dst in sorted(list(self.binaries_fwd[rel][src])):
                    print("(%s %s %s)" % (rel, src, dst))

    def executor(self):
        return GraphKBExecutor(self)


class GraphKBExecutor:
    """
    Executes formal queries against a GraphKB and returns their denotations.
    Queries are represented by Python tuples, and can be nested.
    Denotations are also represented by Python tuples, but are conceptually sets.

    The query language is perhaps most easily explained by example:

        query                                           denotation
        ----------------------------------------        ------------------------
        'bart'                                          ('bart',)
        'male'                                          ('bart', 'homer')
        ('has_sister', 'lisa')                          ('bart', 'maggie')
        ('lisa', 'has_sister')                          ('maggie',)
        ('lisa', 'has_brother')                         ('bart',)
        ('.and', 'male', 'child')                       ('bart',)
        ('.or', 'male', 'adult')                        ('bart', 'homer', 'marge')
        ('.count', ('bart', 'has_sister'))              (2,)
        ('has_age', ('.gt', 21))                        ('homer', 'marge')
        ('has_age', ('.lt', 2))                         ('maggie',)
        ('has_age', ('.eq', 10))                        ('bart',)
        ('.argmax', 'has_age', 'female')                ('marge',)
        ('.argmin', 'has_age', ('bart', 'has_sister'))  ('maggie',)

    A bit more formally: if

        v is a value
        U is a unary relation
        B is a binary relation
        Q is a relation having numeric values
        X and Y are queries
        [[X]] is the denotation of query X

    then we can define the denotations of queries as follows:

        query               denotation

        v                   the singleton set containing the value v
        U                   the set of values belonging unary relation U
        (B, X)              the set of values which have relation B to any value in [[X]]
        (X, B)              the set of values to which any value in [[X]] has relation B
        ('.and', X, Y)      the intersection of [[X]] and [[Y]]
        ('.or', X, Y)       the union of [[X]] and [[Y]]
        ('.count', X)       the cardinality of [[X]]
        ('.gt', X)          the set of numbers greater than any number in [[X]]
        ('.lt', X)          the set of numbers less than any number in [[X]]
        ('.eq', X)          the set of numbers equal to the single number in [[X]]
        ('.argmax', Q, X)   the subset of [[X]] having maximal values under relation Q
        ('.argmin', Q, X)   the subset of [[X]] having minimal values under relation Q

    """
    def __init__(self, graph_kb):
        self.graph_kb = graph_kb

    def execute(self, sem):
        if isinstance(sem, tuple):
            return self.execute_tuple(sem)
        elif isinstance(sem, str) and sem.startswith('.'):
            return self.execute_special((sem,))
        elif sem in self.graph_kb.unaries:
            return self.execute_unary(sem)
        elif sem in self.graph_kb.binaries_fwd:
            # It's a relation name, so return it as is.
            return sem
        else:
            # It's some other value (string, integer, ...), so return it as a tuple.
            return (sem,)

    def execute_tuple(self, sem):
        if len(sem) == 1 and sem[0] in self.graph_kb.unaries:
            return self.execute_unary(sem[0])
        elif len(sem) == 2 and sem[0] in self.graph_kb.binaries_fwd:
            return self.execute_binary(sem[0], sem[1], rev=True)
        elif len(sem) == 2 and sem[1] in self.graph_kb.binaries_fwd:
            return self.execute_binary(sem[1], sem[0], rev=False)
        elif sem[0].startswith('.'):
            return self.execute_special(sem)

    def execute_unary(self, rel):
        return sorted_tuple(self.graph_kb.unaries[rel])

    def execute_binary(self, rel, arg, rev=False):
        arg = self.execute(arg)
        index = self.graph_kb.binaries_rev if rev else self.graph_kb.binaries_fwd
        if isinstance(arg, Iterable):
            # arg is a tuple, e.g., the result of executing '5044'.
            vals = [src for dst in arg for src in index[rel][dst]]
        elif isinstance(arg, FunctionType):
            # arg is a predicate, e.g., the result of executing ('.gt', 5044).
            vals = [src for dst, srcs in list(index[rel].items()) if arg(dst) for src in srcs]
        else:
            raise Exception('Unsupported argument to join: %s' % str(arg))
        return sorted_tuple(set(vals))

    def execute_special(self, sem):
        args = tuple([self.execute(elt) for elt in sem[1:]])
        if sem[0] == '.and':
            return self.execute_and(args)
        elif sem[0] == '.or':
            return self.execute_or(args)
        elif sem[0] == '.not':
            return self.execute_not(args)
        elif sem[0] == '.any':
            return self.execute_any(args)
        elif sem[0] == '.count':
            return self.execute_count(args)
        elif sem[0] == '.gt':
            return self.execute_gt(args)
        elif sem[0] == '.lt':
            return self.execute_lt(args)
        elif sem[0] == '.eq':
            return self.execute_eq(args)
        elif sem[0] == '.max':
            return self.execute_max(args, rev=False, arg=False)
        elif sem[0] == '.min':
            return self.execute_max(args, rev=True, arg=False)
        elif sem[0] == '.argmax':
            return self.execute_max(args, rev=False, arg=True)
        elif sem[0] == '.argmin':
            return self.execute_max(args, rev=True, arg=True)
        else:
            raise Exception('Unsupported operator: %s' % str(sem[0]))

    def execute_and(self, args):
        assert len(args) == 2
        # Check to see if either element of args is a predicate,
        # e.g., the result of executing ('.gt', 5044).
        if isinstance(args[0], FunctionType):
            args = (args[1], args[0])
        if isinstance(args[1], FunctionType):
            return sorted_tuple([elt for elt in args[0] if args[1](elt)])
        else:
            return sorted_tuple(set(args[0]).intersection(set(args[1])))

    # TODO: Properly handle the case where one or both arguments are
    # functions, like execute_and() does.
    def execute_or(self, args):
        assert len(args) == 2
        return sorted_tuple(set(args[0]).union(set(args[1])))

    def execute_not(self, args):
        assert len(args) == 1
        complement = [node for node in self.graph_kb.nodes if node not in args[0]]
        return sorted_tuple(complement)

    def execute_any(self, args):
        assert len(args) == 0
        return self.execute_not(((),))

    def execute_count(self, args):
        assert len(args) == 1
        return (len(args[0]),)

    def execute_gt(self, args):
        assert len(args) == 1
        assert isinstance(args[0], tuple), 'Not a tuple: %s' % str(args[0])
        max_val = max(args[0]) if args[0] else float('-inf')
        return lambda x: x > max_val

    # TODO: consider ways of combining with execute_gt().
    def execute_lt(self, args):
        assert len(args) == 1
        assert isinstance(args[0], tuple), 'Not a tuple: %s' % str(args[0])
        min_val = min(args[0]) if args[0] else float('inf')
        return lambda x: x < min_val

    def execute_eq(self, args):
        assert len(args) == 1
        assert isinstance(args[0], tuple), 'Not a tuple: %s' % str(args[0])
        assert len(args[0]) == 1
        return lambda x: x == args[0][0]

    def execute_max(self, args, rev=False, arg=False):
        assert len(args) == 2
        # TODO: Drop the assumption that the first argument is a relation from some entity
        # to a number.  What if it's the other way around?
        index = self.graph_kb.binaries_fwd
        assert args[0] in index, 'Not a relation name: %s' % str(args[0])
        pairs = [(src, dst) for src in args[1] for dst in index[args[0]][src]]
        vals = [val for e, val in pairs]
        if rev:
            ext_val = min(vals) if pairs else float('inf')
        else:
            ext_val = max(vals) if pairs else float('-inf')
        if arg:
            return sorted_tuple(set([e for e, val in pairs if val == ext_val]))
        else:
            return (ext_val,)

def sorted_tuple(elements):
    return tuple(sorted(list(elements), key=str))


# demo =========================================================================

def demo():
    from example import Example
    tuples = [
        ('male', 'homer'),
        ('female', 'marge'),
        ('male', 'bart'),
        ('female', 'lisa'),
        ('female', 'maggie'),
        ('adult', 'homer'),
        ('adult', 'marge'),
        ('child', 'bart'),
        ('child', 'lisa'),
        ('child', 'maggie'),
        ('has_age', 'homer', 36),
        ('has_age', 'marge', 34),
        ('has_age', 'bart', 10),
        ('has_age', 'lisa', 8),
        ('has_age', 'maggie', 1),
        ('has_brother', 'lisa', 'bart'),
        ('has_brother', 'maggie', 'bart'),
        ('has_sister', 'bart', 'maggie'),
        ('has_sister', 'bart', 'lisa'),
        ('has_father', 'bart', 'homer'),
        ('has_father', 'lisa', 'homer'),
        ('has_father', 'maggie', 'homer'),
        ('has_mother', 'bart', 'marge'),
        ('has_mother', 'lisa', 'marge'),
        ('has_mother', 'maggie', 'marge'),
    ]
    graph_kb = GraphKB(tuples)
    graph_kb.list()
    executor = graph_kb.executor()
    examples = [
        Example(input='bart',
                semantics='bart',
                denotation=('bart',)),
        Example(input='males',
                semantics='male',
                denotation=('bart', 'homer')),
        Example(input='things that have bart as brother',
                semantics=('has_brother', 'bart'),
                denotation=('lisa', 'maggie')),
        Example(input='brothers of bart',
                semantics=('bart', 'has_brother'),
                denotation=()),
        Example(input='sisters of bart',
                semantics=('bart', 'has_sister'),
                denotation=('lisa', 'maggie')),
        Example(input='male children',
                semantics=('.and', 'male', 'child'),
                denotation=('bart',)),
        Example(input='males or adults',
                semantics=('.or', 'male', 'adult'),
                denotation=('bart', 'homer', 'marge')),
        Example(input='not a child',
                semantics=('.not', 'child'),
                denotation=(1, 10, 34, 36, 8, 'homer', 'marge')),
        Example(input='anything',
                semantics=('.any',),
                denotation=(1, 10, 34, 36, 8, 'bart', 'homer', 'lisa', 'maggie', 'marge')),
        Example(input='sisters',
                semantics=('.any', 'has_sister'),
                denotation=('lisa', 'maggie')),
        Example(input='children who are not sisters',
                semantics=('.and', 'child', ('.not', ('.any', 'has_sister'))),
                denotation=('bart',)),
        Example(input='number of sisters of bart',
                semantics=('.count', ('bart', 'has_sister')),
                denotation=(2,)),
        Example(input='things that have age greater than 21',
                semantics=('has_age', ('.gt', 21)),
                denotation=('homer', 'marge')),
        Example(input='things that have age less than 2',
                semantics=('has_age', ('.lt', 2)),
                denotation=('maggie',)),
        Example(input='things that have age equal to 10',
                semantics=('has_age', ('.eq', 10)),
                denotation=('bart',)),
        Example(input='age of oldest female',
                semantics=('.max', 'has_age', 'female'),
                denotation=(34,)),
        Example(input='age of youngest sister of bart',
                semantics=('.min', 'has_age', ('bart', 'has_sister')),
                denotation=(1,)),
        Example(input='age of oldest thing',
                semantics=('.max', 'has_age', '.any'),
                denotation=(36,)),
        Example(input='oldest female',
                semantics=('.argmax', 'has_age', 'female'),
                denotation=('marge',)),
        Example(input='youngest sister of bart',
                semantics=('.argmin', 'has_age', ('bart', 'has_sister')),
                denotation=('maggie',)),
        Example(input='oldest thing',
                semantics=('.argmax', 'has_age', '.any'),
                denotation=('homer',)),
    ]
    for example in examples:
        deno = executor.execute(example.semantics)
        assert deno == example.denotation, example.input + ': ' + str(deno)
        print()
        print('%-16s %s' % ('input', example.input))
        print('%-16s %s' % ('semantics', example.semantics))
        print('%-16s %s' % ('denotation', deno))

if __name__ == '__main__':
    demo()
