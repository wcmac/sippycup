__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

from collections import defaultdict
from numbers import Number

from domain import Domain
from example import Example
from experiment import evaluate_for_domain, evaluate_dev_examples_for_domain, train_test, train_test_for_domain, interact, learn_lexical_semantics, generate
from metrics import DenotationAccuracyMetric
from parsing import Grammar, Rule
from scoring import rule_features

# ArithmeticDomain =============================================================

# TODO: comment.
class ArithmeticDomain(Domain):

    def train_examples(self):
        return [
            Example(input="one plus one", semantics=('+', 1, 1), denotation=2),
            Example(input="one plus two", semantics=('+', 1, 2), denotation=3),
            Example(input="one plus three", semantics=('+', 1, 3), denotation=4),
            Example(input="two plus two", semantics=('+', 2, 2), denotation=4),
            Example(input="two plus three", semantics=('+', 2, 3), denotation=5),
            Example(input="three plus one", semantics=('+', 3, 1), denotation=4),
            Example(input="three plus minus two", semantics=('+', 3, ('~', 2)), denotation=1),
            Example(input="two plus two", semantics=('+', 2, 2), denotation=4),
            Example(input="three minus two", semantics=('-', 3, 2), denotation=1),
            Example(input="minus three minus two", semantics=('-', ('~', 3), 2), denotation=-5),
            Example(input="two times two", semantics=('*', 2, 2), denotation=4),
            Example(input="two times three", semantics=('*', 2, 3), denotation=6),
            Example(input="three plus three minus two", semantics=('-', ('+', 3, 3), 2), denotation=4),
        ]

    def test_examples(self):
        return [
            Example(input="minus three", semantics=('~', 3), denotation=-3),
            Example(input="three plus two", semantics=('+', 3, 2), denotation=5),
            Example(input="two times two plus three", semantics=('+', ('*', 2, 2), 3), denotation=7),
            Example(input="minus four", semantics=('~', 4), denotation=-4),
        ]

    def dev_examples(self):
        return arithmetic_dev_examples

    numeral_rules = [
        Rule('$E', 'one', 1),
        Rule('$E', 'two', 2),
        Rule('$E', 'three', 3),
        Rule('$E', 'four', 4),
    ]

    operator_rules = [
        Rule('$UnOp', 'minus', '~'),
        Rule('$BinOp', 'plus', '+'),
        Rule('$BinOp', 'minus', '-'),
        Rule('$BinOp', 'times', '*'),
    ]

    compositional_rules = [
        Rule('$E', '$UnOp $E', lambda sems: (sems[0], sems[1])),
        Rule('$EBO', '$E $BinOp', lambda sems: (sems[1], sems[0])),
        Rule('$E', '$EBO $E', lambda sems: (sems[0][0], sems[0][1], sems[1])),
    ]

    def rules(self):
        return self.numeral_rules + self.operator_rules + self.compositional_rules

    def operator_precedence_features(self, parse):
        """
        Traverses the arithmetic expression tree which forms the semantics of
        the given parse and adds a feature (op1, op2) whenever op1 appears
        lower in the tree than (i.e. with higher precedence than) than op2.
        """
        def collect_features(semantics, features):
            if isinstance(semantics, tuple):
                for child in semantics[1:]:
                    collect_features(child, features)
                    if isinstance(child, tuple) and child[0] != semantics[0]:
                        features[(child[0], semantics[0])] += 1.0
        features = defaultdict(float)
        collect_features(parse.semantics, features)
        return features

    def features(self, parse):
        features = rule_features(parse)
        features.update(self.operator_precedence_features(parse))
        return features

    def weights(self):
        weights = defaultdict(float)
        weights[('*', '+')] = 1.0
        weights[('*', '-')] = 1.0
        weights[('~', '+')] = 1.0
        weights[('~', '-')] = 1.0
        weights[('+', '*')] = -1.0
        weights[('-', '*')] = -1.0
        weights[('+', '~')] = -1.0
        weights[('-', '~')] = -1.0
        return weights

    def grammar(self):
        return Grammar(rules=self.rules(), start_symbol='$E')

    ops = {
        '~': lambda x: -x,
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
    }

    def execute(self, semantics):
        if isinstance(semantics, tuple):
            op = self.ops[semantics[0]]
            args = [self.execute(arg) for arg in semantics[1:]]
            return op(*args)
        else:
            return semantics

    def training_metric(self):
        return DenotationAccuracyMetric()


# EagerArithmeticDomain ========================================================
# TODO: add comment.

class EagerArithmeticDomain(Domain):

    def train_examples(self):
        return [convert_example(ex) for ex in ArithmeticDomain().train_examples()]

    def test_examples(self):
        return [convert_example(ex) for ex in ArithmeticDomain().test_examples()]

    def dev_examples(self):
        return [convert_example(ex) for ex in ArithmeticDomain().dev_examples()]

    numeral_rules = ArithmeticDomain.numeral_rules

    operator_rules = [
        Rule('$BinOp', 'plus', lambda x: (lambda y: x + y)),
        Rule('$BinOp', 'minus', lambda x: (lambda y: x - y)),
        Rule('$BinOp', 'times', lambda x: (lambda y: x * y)),
        Rule('$UnOp', 'minus', lambda x: -1 * x),
    ]

    compositional_rules = [
        Rule('$E', '$EBO $E', lambda sems: sems[0](sems[1])),
        Rule('$EBO', '$E $BinOp', lambda sems: sems[1](sems[0])),
        Rule('$E', '$UnOp $E', lambda sems: sems[0](sems[1])),
    ]

    def rules(self):
        return self.numeral_rules + self.operator_rules + self.compositional_rules

    def grammar(self):
        return Grammar(rules=self.rules(), start_symbol='$E')

    def execute(self, semantics):
        return semantics

    def training_metric(self):
        return DenotationAccuracyMetric()

def convert_example(example):
    return Example(input=example.input,
                   semantics=example.denotation,
                   denotation=example.denotation)

# ==============================================================================

arithmetic_dev_examples = [
    Example(input='three plus four', denotation=7),
    Example(input='one times one', denotation=1),
    Example(input='four plus one plus four', denotation=9),
    Example(input='minus three plus two', denotation=-1),
    Example(input='minus three plus three', denotation=0),
    Example(input='minus four minus minus three', denotation=-1),
    Example(input='four minus minus three', denotation=7),
    Example(input='two plus one', denotation=3),
    Example(input='minus one minus four minus four', denotation=-9),
    Example(input='one plus minus one plus minus one', denotation=-1),
    Example(input='two times minus two plus three', denotation=-1),
    Example(input='two times minus three', denotation=-6),
    Example(input='four times two', denotation=8),
    Example(input='one plus four', denotation=5),
    Example(input='four minus one', denotation=3),
    Example(input='minus one times one times one', denotation=-1),
    Example(input='minus minus two', denotation=2),
    Example(input='one minus three times minus two times three', denotation=19),
    Example(input='minus two minus four', denotation=-6),
    Example(input='one minus two', denotation=-1),
    Example(input='three minus one', denotation=2),
    Example(input='minus three minus minus minus four', denotation=-7),
    Example(input='minus three plus four', denotation=1),
    Example(input='minus four minus four times minus one', denotation=0),
    Example(input='minus minus three plus two', denotation=5),
    Example(input='four plus three', denotation=7),
    Example(input='minus three plus one', denotation=-2),
    Example(input='minus two times one minus minus two', denotation=0),
    Example(input='one plus minus two', denotation=-1),
    Example(input='four plus four', denotation=8),
    Example(input='two minus one', denotation=1),
    Example(input='one plus minus three times four plus four times four', denotation=5),
    Example(input='minus one times three plus two', denotation=-1),
    Example(input='minus three times one minus minus three', denotation=0),
    Example(input='four plus four minus four minus one', denotation=3),
    Example(input='four minus one times three minus one', denotation=0),
    Example(input='two minus minus one', denotation=3),
    Example(input='minus minus three minus two', denotation=1),
    Example(input='one times minus four minus four plus one plus one', denotation=-6),
    Example(input='two plus four times two', denotation=10),
    Example(input='one plus two times one', denotation=3),
    Example(input='three minus four', denotation=-1),
    Example(input='two times two', denotation=4),
    Example(input='three minus minus three plus two minus minus three', denotation=11),
    Example(input='three minus minus three times two', denotation=9),
    Example(input='minus three times four times two', denotation=-24),
    Example(input='minus four minus four', denotation=-8),
    Example(input='three minus minus minus one', denotation=2),
    Example(input='two minus four', denotation=-2),
    Example(input='four times four minus one times three', denotation=13),
    Example(input='four minus three times three', denotation=-5),
    Example(input='minus three plus minus one', denotation=-4),
    Example(input='one minus three', denotation=-2),
    Example(input='minus one minus two', denotation=-3),
    Example(input='one times four times three', denotation=12),
    Example(input='minus three times one', denotation=-3),
    Example(input='three minus minus three', denotation=6),
    Example(input='three times minus minus minus four', denotation=-12),
    Example(input='minus one minus three', denotation=-4),
    Example(input='minus four plus one times three times four minus four', denotation=4),
    Example(input='minus minus four plus four plus minus three', denotation=5),
    Example(input='two minus minus three', denotation=5),
    Example(input='four plus one minus one times four', denotation=1),
    Example(input='three times two', denotation=6),
    Example(input='four plus three times minus two plus minus one', denotation=-3),
    Example(input='minus three minus one', denotation=-4),
    Example(input='minus minus two times four', denotation=8),
    Example(input='one plus three minus minus two minus minus minus four', denotation=2),
    Example(input='minus one minus one plus four plus three', denotation=5),
    Example(input='three times three minus one', denotation=8),
    Example(input='two minus four minus minus three', denotation=1),
    Example(input='minus minus three minus minus one minus three', denotation=1),
    Example(input='three plus two', denotation=5),
    Example(input='minus minus three', denotation=3),
    Example(input='minus minus three times one', denotation=3),
    Example(input='minus two plus four', denotation=2),
    Example(input='two minus minus two', denotation=4),
    Example(input='one plus three', denotation=4),
    Example(input='one times four', denotation=4),
    Example(input='minus three minus minus minus four plus four plus one', denotation=-2),
    Example(input='three times four minus two minus two minus three', denotation=5),
    Example(input='minus three minus three times minus minus minus minus two', denotation=-9),
    Example(input='minus four times minus two', denotation=8),
    Example(input='minus three plus two times three minus minus minus four', denotation=-1),
    Example(input='four times three', denotation=12),
    Example(input='minus minus three plus minus four', denotation=-1),
    Example(input='minus four times four', denotation=-16),
    Example(input='two plus minus one', denotation=1),
    Example(input='minus minus minus three plus minus one', denotation=-4),
    Example(input='three plus one minus minus two', denotation=6),
    Example(input='minus four times minus four', denotation=16),
    Example(input='four plus minus two', denotation=2),
    Example(input='two times four', denotation=8),
    Example(input='minus minus minus four minus one times three plus two', denotation=-5),
    Example(input='one minus one', denotation=0),
    Example(input='minus minus one', denotation=1),
    Example(input='minus minus minus four', denotation=-4),
    Example(input='four plus two', denotation=6),
    Example(input='two minus three', denotation=-1),
    Example(input='minus four plus two', denotation=-2),
]

def train_on_dev_experiment():
    from metrics import denotation_match_metrics
    domain = ArithmeticDomain()
    train_test(model=domain.model(),
               train_examples=arithmetic_dev_examples,
               test_examples=domain.test_examples(),
               metrics=denotation_match_metrics(),
               training_metric=DenotationAccuracyMetric(),
               seed=1,
               print_examples=False)


# ==============================================================================

if __name__ == '__main__':
    evaluate_for_domain(ArithmeticDomain())
    # train_test_for_domain(ArithmeticDomain(), seed=1, print_examples=False)
    # train_on_dev_experiment()
    # evaluate_for_domain(EagerArithmeticDomain())
    # evaluate_dev_examples_for_domain(ArithmeticDomain())
    # interact(ArithmeticDomain(), "two times two plus three")
    # learn_lexical_semantics(ArithmeticDomain(), seed=1)
    # generate(ArithmeticDomain().rules(), '$E')
