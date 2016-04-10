"""
Implementation of core parsing functionality, including the Rule, Parse, and
Grammar classes.

Note that the code architecture does not always adhere to the principles of
object-oriented design.  In many cases, functionality which might naturally be
implemented as instance methods of classes instead appears in standalone static
functions.  This is done to facilitate an incremental presentation in the
accompanying IPython Notebook.
"""

__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

import math
from collections import defaultdict, Iterable
from itertools import product
from io import StringIO
from types import FunctionType

MAX_CELL_CAPACITY = 1000  # upper bound on number of parses in one chart cell


# Rule =========================================================================

class Rule:
    """Represents a CFG rule with a semantic attachment."""

    def __init__(self, lhs, rhs, sem=None):
        self.lhs = lhs
        self.rhs = tuple(rhs.split()) if isinstance(rhs, str) else rhs
        self.sem = sem
        validate_rule(self)

    def __str__(self):
        """Returns a string representation of this Rule."""
        return 'Rule' + str((self.lhs, ' '.join(self.rhs), self.sem))

def is_cat(label):
    """
    Returns true iff the given label is a category (non-terminal), i.e., is
    marked with an initial '$'.
    """
    return label.startswith('$')

def is_lexical(rule):
    """
    Returns true iff the given Rule is a lexical rule, i.e., contains only
    words (terminals) on the RHS.
    """
    return all([not is_cat(rhsi) for rhsi in rule.rhs])

def is_unary(rule):
    """
    Returns true iff the given Rule is a unary compositional rule, i.e.,
    contains only a single category (non-terminal) on the RHS.
    """
    return len(rule.rhs) == 1 and is_cat(rule.rhs[0])

def is_binary(rule):
    """
    Returns true iff the given Rule is a binary compositional rule, i.e.,
    contains exactly two categories (non-terminals) on the RHS.
    """
    return len(rule.rhs) == 2 and is_cat(rule.rhs[0]) and is_cat(rule.rhs[1])

def validate_rule(rule):
    """Returns true iff the given Rule is well-formed."""
    assert is_cat(rule.lhs), 'Not a category: %s' % rule.lhs
    assert isinstance(rule.rhs, tuple), 'Not a tuple: %s' % rule.rhs
    for rhs_i in rule.rhs:
        assert isinstance(rhs_i, str), 'Not a string: %s' % rhs_i

def is_optional(label):
    """
    Returns true iff the given RHS item is optional, i.e., is marked with an
    initial '?'.
    """
    return label.startswith('?') and len(label) > 1

def contains_optionals(rule):
    """Returns true iff the given Rule contains any optional items on the RHS."""
    return any([is_optional(rhsi) for rhsi in rule.rhs])


# Parse ========================================================================

class Parse:
    def __init__(self, rule, children):
        self.rule = rule
        self.children = tuple(children[:])
        self.semantics = compute_semantics(self)
        self.score = float('NaN')
        self.denotation = None
        validate_parse(self)

    def __str__(self):
        child_strings = [str(child) for child in self.children]
        return '(%s %s)' % (self.rule.lhs, ' '.join(child_strings))

def validate_parse(parse):
    assert isinstance(parse.rule, Rule), 'Not a Rule: %s' % parse.rule
    assert isinstance(parse.children, Iterable)
    assert len(parse.children) == len(parse.rule.rhs)
    for i in range(len(parse.rule.rhs)):
        if is_cat(parse.rule.rhs[i]):
            assert parse.rule.rhs[i] == parse.children[i].rule.lhs
        else:
            assert parse.rule.rhs[i] == parse.children[i]

def apply_semantics(rule, sems):
    # Note that this function would not be needed if we required that semantics
    # always be functions, never bare values.  That is, if instead of
    # Rule('$E', 'one', 1) we required Rule('$E', 'one', lambda sems: 1).
    # But that would be cumbersome.
    if isinstance(rule.sem, FunctionType):
        return rule.sem(sems)
    else:
        return rule.sem

def compute_semantics(parse):
    if is_lexical(parse.rule):
        return parse.rule.sem
    else:
        child_semantics = [child.semantics for child in parse.children]
        return apply_semantics(parse.rule, child_semantics)

def parse_to_pretty_string(parse, indent=0, show_sem=False):
    def indent_string(level):
        return '  ' * level
    def label(parse):
        if show_sem:
            return '(%s %s)' % (parse.rule.lhs, parse.semantics)
        else:
            return parse.rule.lhs
    def to_oneline_string(parse):
        if isinstance(parse, Parse):
          child_strings = [to_oneline_string(child) for child in parse.children]
          return '[%s %s]' % (label(parse), ' '.join(child_strings))
        else:
            return str(parse)
    def helper(parse, level, output):
        line = indent_string(level) + to_oneline_string(parse)
        if len(line) <= 100:
            print(line, file=output)
        elif isinstance(parse, Parse):
            print(indent_string(level) + '[' + label(parse), file=output)
            for child in parse.children:
                helper(child, level + 1, output)
            # TODO: Put closing parens to end of previous line, not dangling alone.
            print(indent_string(level) + ']', file=output)
        else:
            print(indent_string(level) + parse, file=output)
    output = StringIO()
    helper(parse, indent, output)
    return output.getvalue()[:-1]  # trim final newline


# Grammar ======================================================================

class Grammar:
    def __init__(self, rules=[], annotators=[], start_symbol='$ROOT'):
        self.categories = set()
        self.lexical_rules = defaultdict(list)
        self.unary_rules = defaultdict(list)
        self.binary_rules = defaultdict(list)
        self.annotators = annotators
        self.start_symbol = start_symbol
        for rule in rules:
            add_rule(self, rule)
        print('Created grammar with %d rules' % len(rules))

    def parse_input(self, input):
        """
        Returns the list of parses for the given input which can be derived
        using this grammar.
        """
        return parse_input(self, input)

def add_rule(grammar, rule):
    if contains_optionals(rule):
        add_rule_containing_optional(grammar, rule)
    elif is_lexical(rule):
        grammar.lexical_rules[rule.rhs].append(rule)
    elif is_unary(rule):
        grammar.unary_rules[rule.rhs].append(rule)
    elif is_binary(rule):
        grammar.binary_rules[rule.rhs].append(rule)
    elif all([is_cat(rhsi) for rhsi in rule.rhs]):
        add_n_ary_rule(grammar, rule)
    else:
        # EXERCISE: handle this case.
        raise Exception('RHS mixes terminals and non-terminals: %s' % rule)

def add_rule_containing_optional(grammar, rule):
    """
    Handles adding a rule which contains an optional element on the RHS.
    We find the leftmost optional element on the RHS, and then generate
    two variants of the rule: one in which that element is required, and
    one in which it is removed.  We add these variants in place of the
    original rule.  (If there are more optional elements further to the
    right, we'll wind up recursing.)

    For example, if the original rule is:

        Rule('$Z', '$A ?$B ?$C $D')

    then we add these rules instead:

        Rule('$Z', '$A $B ?$C $D')
        Rule('$Z', '$A ?$C $D')
    """
    # Find index of the first optional element on the RHS.
    first = next((idx for idx, elt in enumerate(rule.rhs) if is_optional(elt)), -1)
    assert first >= 0
    assert len(rule.rhs) > 1, 'Entire RHS is optional: %s' % rule
    prefix = rule.rhs[:first]
    suffix = rule.rhs[(first + 1):]
    # First variant: the first optional element gets deoptionalized.
    deoptionalized = (rule.rhs[first][1:],)
    add_rule(grammar, Rule(rule.lhs, prefix + deoptionalized + suffix, rule.sem))
    # Second variant: the first optional element gets removed.
    # If the semantics is a value, just keep it as is.
    sem = rule.sem
    # But if it's a function, we need to supply a dummy argument for the removed element.
    if isinstance(rule.sem, FunctionType):
        sem = lambda sems: rule.sem(sems[:first] + [None] + sems[first:])
    add_rule(grammar, Rule(rule.lhs, prefix + suffix, sem))

def add_n_ary_rule(grammar, rule):
    """
    Handles adding a rule with three or more non-terminals on the RHS.
    We introduce a new category which covers all elements on the RHS except
    the first, and then generate two variants of the rule: one which
    consumes those elements to produce the new category, and another which
    combines the new category which the first element to produce the
    original LHS category.  We add these variants in place of the
    original rule.  (If the new rules still contain more than two elements
    on the RHS, we'll wind up recursing.)

    For example, if the original rule is:

        Rule('$Z', '$A $B $C $D')

    then we create a new category '$Z_$A' (roughly, "$Z missing $A to the left"),
    and add these rules instead:

        Rule('$Z_$A', '$B $C $D')
        Rule('$Z', '$A $Z_$A')
    """
    def add_category(base_name):
        assert is_cat(base_name)
        name = base_name
        while name in grammar.categories:
            name = name + '_'
        grammar.categories.add(name)
        return name
    category = add_category('%s_%s' % (rule.lhs, rule.rhs[0]))
    add_rule(grammar, Rule(category, rule.rhs[1:], lambda sems: sems))
    add_rule(grammar, Rule(rule.lhs, (rule.rhs[0], category),
                           lambda sems: apply_semantics(rule, [sems[0]] + sems[1])))

def parse_input(grammar, input):
    """
    Returns the list of parses for the given input which can be derived using
    the given grammar.
    """
    tokens = input.split()
    # TODO: populate chart with tokens?  that way everything is in the chart
    chart = defaultdict(list)
    for j in range(1, len(tokens) + 1):
        for i in range(j - 1, -1, -1):
            apply_annotators(grammar, chart, tokens, i, j)
            apply_lexical_rules(grammar, chart, tokens, i, j)
            apply_binary_rules(grammar, chart, i, j)
            apply_unary_rules(grammar, chart, i, j)
    # print_chart(chart)
    parses = chart[(0, len(tokens))]
    if grammar.start_symbol:
        parses = [parse for parse in parses if parse.rule.lhs == grammar.start_symbol]
    return parses

def apply_annotators(grammar, chart, tokens, i, j):
    """Add parses to chart cell (i, j) by applying annotators."""
    if hasattr(grammar, 'annotators'):
        for annotator in grammar.annotators:
            for category, semantics in annotator.annotate(tokens[i:j]):
                if not check_capacity(chart, i, j):
                    return
                rule = Rule(category, tuple(tokens[i:j]), semantics)
                chart[(i, j)].append(Parse(rule, tokens[i:j]))

def apply_lexical_rules(grammar, chart, tokens, i, j):
    """Add parses to chart cell (i, j) by applying lexical rules."""
    for rule in grammar.lexical_rules[tuple(tokens[i:j])]:
        if not check_capacity(chart, i, j):
            return
        chart[(i, j)].append(Parse(rule, tokens[i:j]))

def apply_binary_rules(grammar, chart, i, j):
    """Add parses to chart cell (i, j) by applying binary rules."""
    for k in range(i + 1, j):
        for parse_1, parse_2 in product(chart[(i, k)], chart[(k, j)]):
            for rule in grammar.binary_rules[(parse_1.rule.lhs, parse_2.rule.lhs)]:
                if not check_capacity(chart, i, j):
                    return
                chart[(i, j)].append(Parse(rule, [parse_1, parse_2]))

def apply_unary_rules(grammar, chart, i, j):
    """Add parses to chart cell (i, j) by applying unary rules."""
    # Note that the last line of this method can add new parses to chart[(i,
    # j)], the list over which we are iterating.  Because of this, we
    # essentially get unary closure "for free".  (However, if the grammar
    # contains unary cycles, we'll get stuck in a loop, which is one reason for
    # check_capacity().)
    for parse in chart[(i, j)]:
        for rule in grammar.unary_rules[(parse.rule.lhs,)]:
            if not check_capacity(chart, i, j):
                return
            chart[(i, j)].append(Parse(rule, [parse]))

# Important for catching e.g. unary cycles.
max_cell_capacity_hits = 0
def check_capacity(chart, i, j):
    global max_cell_capacity_hits
    if len(chart[(i, j)]) >= MAX_CELL_CAPACITY:
        # print 'Cell (%d, %d) has reached capacity %d' % (
        #     i, j, MAX_CELL_CAPACITY)
        max_cell_capacity_hits += 1
        lg_max_cell_capacity_hits = math.log(max_cell_capacity_hits, 2)
        if int(lg_max_cell_capacity_hits) == lg_max_cell_capacity_hits:
            print('Max cell capacity %d has been hit %d times' % (
                MAX_CELL_CAPACITY, max_cell_capacity_hits))
        return False
    return True

def print_grammar(grammar):
    def all_rules(rule_index):
        return [rule for rules in list(rule_index.values()) for rule in rules]
    def print_rules_sorted(rules):
        for s in sorted([str(rule) for rule in rules]):
            print('  ' + s)
    print('Lexical rules:')
    print_rules_sorted(all_rules(grammar.lexical_rules))
    print('Unary rules:')
    print_rules_sorted(all_rules(grammar.unary_rules))
    print('Binary rules:')
    print_rules_sorted(all_rules(grammar.binary_rules))

def print_chart(chart):
    """Print the chart.  Useful for debugging."""
    spans = sorted(list(chart.keys()), key=(lambda span: span[0]))
    spans = sorted(spans, key=(lambda span: span[1] - span[0]))
    for span in spans:
        if len(chart[span]) > 0:
            print('%-12s' % str(span), end=' ')
            print(chart[span][0])
            for entry in chart[span][1:]:
                print('%-12s' % ' ', entry)
