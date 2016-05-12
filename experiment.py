__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

from collections import defaultdict
import random

from metrics import SemanticsAccuracyMetric, NumParsesMetric, standard_metrics
from example import Example
from learning import latent_sgd
from parsing import is_cat, parse_to_pretty_string, print_grammar
from scoring import Model, rule_features

# TODO: comment
def print_sample_outcomes(model=None,
                          examples=[],
                          name=None,
                          metric=None,
                          metric_test=None,
                          k=10):
    candidates = []
    for example in examples:
        parses = model.parse_input(example.input)
        metric_value = metric.evaluate(example, parses)
        if metric_test(metric_value):
            candidates.append(example)
    k = min(k, len(candidates))
    samples = random.sample(candidates, k)
    print('%d of %d %s on %s:\n' % (k, len(candidates), name, metric.name()))
    inputs = [example.input for example in samples]
    for input in sorted(inputs):
        print(' ', input)
    print()
    return samples

# TODO: comment
def sample_wins_and_losses(domain=None,
                           model=None,
                           metric=None,
                           seed=None):
    if seed:
        random.seed(seed)
    metric = metric or domain.training_metric()
    model = model or domain.model()
    train_examples=domain.train_examples()
    evaluate_model(model=model,
                   examples=train_examples,
                   metrics=domain.metrics(),
                   print_examples=False)
    def my_print_sample_outcomes(name=None, metric_test=None, k=10):
        examples = print_sample_outcomes(model=model,
                                         examples=train_examples,
                                         name=name,
                                         metric=metric,
                                         metric_test=metric_test,
                                         k=k)
    my_print_sample_outcomes(name='wins', metric_test=(lambda n: n > 0), k=5)
    my_print_sample_outcomes(name='losses', metric_test=(lambda n: n == 0), k=10)

# TODO: comment
def print_parses(example,
                 parses,
                 metrics=[NumParsesMetric()],
                 max_parses=10000,
                 show_syntax=False):
        print('%-34s %s' % ('input', example.input))
        if example.semantics != None:
            print('%-34s %s' % ('target semantics', str(example.semantics)))
        if example.denotation != None:
            print('%-34s %s' % ('target denotation', str(example.denotation)))
        print()
        for metric in metrics:
            metric_value = metric.evaluate(example, parses)
            print('%-34s %.3g' % (metric.name(), metric_value))
        print()
        for idx, parse in enumerate(parses[:max_parses]):
            def outcome_marker(target, prediction):
                return ('+' if prediction == target else '-') if target != None else ' '
            parse_outcome = outcome_marker(example.parse, parse)
            semantics_outcome = outcome_marker(example.semantics, parse.semantics)
            if example.denotation != None:
                denotation_outcome = outcome_marker(example.denotation, parse.denotation)
            else:
                denotation_outcome = ' '
            lines = []
            if show_syntax:
                lines.append('%-15s %s   \n%s' % ('parse', parse_outcome, parse_to_pretty_string(parse)))
            lines.append('%-15s %s   %s' % ('semantics', semantics_outcome, parse.semantics))
            if example.denotation != None or parse.denotation != None:
                lines.append('%-15s %s   %s' % ('denotation', denotation_outcome, parse.denotation))
            for l, line in enumerate(lines):
                if l == 0:
                    print('%-3s %8.3f   %s' % (idx, parse.score, line))
                else:
                    print('%-3s %8s   %s' % ('', '', line))
        if len(parses) > max_parses:
            print('(additional parses truncated)')
        print('\n' + '-' * 80)

# TODO: comment
def evaluate_model(model=None,
                   examples=[],
                   examples_label=None,
                   metrics=standard_metrics(),
                   print_examples=True):
    print('=' * 80)
    print('Evaluating on %d %sexamples\n' % (
        len(examples), examples_label + ' ' if examples_label else ''))
    print('-' * 80)
    metric_values = defaultdict(int)
    for example in examples:
        parses = model.parse_input(example.input)
        for metric in metrics:
            metric_value = metric.evaluate(example, parses)
            metric_values[metric.name()] += metric_value
        if print_examples:
            print_parses(example, parses, metrics=metrics)
    print('Over %d examples:' % len(examples))
    print()
    for metric in metrics:
        print('%-34s %.3f' % (metric.name(), 1.0 * metric_values[metric.name()] / len(examples)))
    print()

# TODO: comment
def evaluate_grammar(grammar=None,
                     executor=None,
                     examples=[],
                     examples_label=None,
                     metrics=standard_metrics(),
                     print_examples=True):
    evaluate_model(model=Model(grammar=grammar, executor=executor),
                   examples=examples,
                   metrics=metrics,
                   print_examples=print_examples)

def test_executor(domain):
    print('=' * 80)
    print('Test Executor\n')
    for example in domain.examples():
        print('%-24s %s' % ('semantics', example.semantics))
        print('%-24s %s' % ('target denotation', example.denotation))
        actual_denotation = domain.execute(example.semantics)
        match = (actual_denotation == example.denotation)
        print('%-24s %s' % ('actual denotation', '[match]' if match else actual_denotation))
        print()

def evaluate_for_domain(domain, print_examples=True):
    print('#' * 80)
    print('Standard evaluation for domain: %s\n' % domain.__class__.__name__)
    # grammar = domain.grammar()
    # print_grammar(grammar)
    # print
    model = domain.model()
    evaluate_model(model=model,
                   examples=domain.train_examples(),
                   examples_label='train',
                   metrics=domain.metrics(),
                   print_examples=print_examples)
    evaluate_model(model=model,
                   examples=domain.test_examples(),
                   examples_label='test',
                   metrics=domain.metrics(),
                   print_examples=print_examples)

def evaluate_dev_examples_for_domain(domain):
    evaluate_model(model=domain.model(),
                   examples=domain.dev_examples(),
                   examples_label='dev',
                   metrics=domain.metrics(),
                   print_examples=True)

def train_test(model=None,
               train_examples=[],
               test_examples=[],
               metrics=standard_metrics(),
               training_metric=SemanticsAccuracyMetric(),
               seed=None,
               print_examples=False):
    # print_grammar(model.grammar)
    # print
    print('%d training examples, %d test examples' % (len(train_examples), len(test_examples)))

    # 'Before' test
    model.weights = defaultdict(float)  # no weights
    evaluate_model(model=model,
                   examples=train_examples,
                   examples_label='train',
                   metrics=metrics,
                   print_examples=print_examples)
    evaluate_model(model=model,
                   examples=test_examples,
                   examples_label='test',
                   metrics=metrics,
                   print_examples=print_examples)

    # Train
    model = latent_sgd(model, train_examples, training_metric=training_metric, seed=seed)

    # 'After' test
    evaluate_model(model=model,
                   examples=train_examples,
                   examples_label='train',
                   metrics=metrics,
                   print_examples=print_examples)
    evaluate_model(model=model,
                   examples=test_examples,
                   examples_label='test',
                   metrics=metrics,
                   print_examples=print_examples)

def train_test_for_domain(domain, seed=None, print_examples=False):
    print('#' * 80)
    print('Train/test experiment for domain: %s\n' % domain.__class__.__name__)
    train_test(model=domain.model(),
               train_examples=domain.train_examples(),
               test_examples=domain.test_examples(),
               metrics=domain.metrics(),
               training_metric=domain.training_metric(),
               seed=seed,
               print_examples=print_examples)

def cartesian_product_of_lexical_rules(rules, restrict_by_lhs=True):
    """
    Expands the given collection of rules by iterating through all possible
    pairs of existing lexical rules and adding a new rule which combines the RHS
    of the first rule with the semantics of the second.  If restrict_by_lhs is
    true, we only consider pairs which have the same LHS, which helps to avoid
    constructing malformed semantics.
    """
    from itertools import product
    from parsing import Rule, is_lexical
    lexical_rules = [rule for rule in rules if is_lexical(rule)]
    expanded_rules = [rule for rule in rules if not is_lexical(rule)]
    # Partition rules by lhs.
    lexical_rules_by_lhs = defaultdict(list)
    for rule in lexical_rules:
        lhs = rule.lhs if restrict_by_lhs else 'dummy'
        lexical_rules_by_lhs[lhs].append(rule)
    # In each partition, iterate through Cartesian product of lexical rules.
    for lhs, rules in list(lexical_rules_by_lhs.items()):
        sems = set([rule.sem for rule in rules])
        for rule, sem in product(rules, sems):
            expanded_rules.append(Rule(rule.lhs, rule.rhs, sem))
    return expanded_rules

def learn_lexical_semantics(domain, seed=None):
    from parsing import Grammar
    print('#' * 80)
    print('Learn lexical semantics experiment for domain: %s\n' % domain.__class__.__name__)
    original_grammar = domain.grammar()
    expanded_rules = cartesian_product_of_lexical_rules(domain.rules())
    grammar = Grammar(rules=expanded_rules,
                      annotators=original_grammar.annotators,
                      start_symbol=original_grammar.start_symbol)
    model = Model(grammar=grammar,
                  feature_fn=domain.features,
                  weights=domain.weights,
                  executor=domain.execute)
    train_test(model=model,
               train_examples=domain.train_examples(),
               test_examples=domain.test_examples(),
               metrics=domain.metrics(),
               training_metric=domain.training_metric(),
               seed=seed,
               print_examples=False)

def interact(domain, example_input=None, T=10):
    import readline
    model = domain.model()
    model = latent_sgd(model=model,
                       examples=domain.train_examples(),
                       training_metric=domain.training_metric(),
                       T=T)

    print('\nHello! Enter a query%s:' % (', such as "%s"' % example_input if example_input else ''))
    while True:
        try:
            query = input('>>> ')
        except EOFError:
            print('\nBye!')
            return
        example = Example(input=query)
        parses = model.parse_input(query)
        if parses:
            print_parses(example, parses)
        else:
            print('No parse!')

def generate(rules, start_symbol='$ROOT', n=100, min_tokens=3, max_tokens=10):
    rules_by_lhs = defaultdict(list)
    for rule in rules:
        rules_by_lhs[rule.lhs].append(rule)
    def sample_phrase(label):
        if label.startswith('?'):
            label = label[1:]
        if not is_cat(label):
            return label
        if label not in rules_by_lhs:
            return label
        rule = random.choice(rules_by_lhs[label])
        phrases = [sample_phrase(label) for label in rule.rhs]
        return ' '.join(phrases)
    inputs = set()
    while len(inputs) < n:
        input = sample_phrase(start_symbol)
        print(input)
        num_tokens = len(input.split())
        if num_tokens >= min_tokens and num_tokens <= max_tokens:
            inputs.add(input)
    print('-' * 80)
    for input in inputs:
        print(input)

def find_best_rules(domain):
    model = domain.model()
    examples = domain.train_examples()
    metric = domain.training_metric()
    rule_counts = defaultdict(int)
    for example in examples:
        parses = model.parse_input(example.input)
        good_parses = [p for p in parses if metric.evaluate(example, [p])]
        if good_parses:
            best_parse = good_parses[0]
            features = rule_features(best_parse)
            for rule, count in list(features.items()):
                rule_counts[rule] = rule_counts[rule] + count
    counts = [(count, rule) for rule, count in list(rule_counts.items())]
    counts = sorted(counts, reverse=True)
    for count, rule in counts:
        print('%d\t%s' % (count, rule))
