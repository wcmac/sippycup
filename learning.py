__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

import random
from collections import defaultdict

from metrics import SemanticsAccuracyMetric, DenotationAccuracyMetric
from scoring import Model

def latent_sgd(model=None, examples=[], training_metric=None, T=10, eta=0.1, seed=None):
    # Used for sorting scored parses.
    def scored_parse_key_fn(scored_parse):
        return (scored_parse[0], str(scored_parse[1]))
    if T <= 0:
        return model
    print('=' * 80)
    print('Running SGD learning on %d examples with training metric: %s\n' % (
        len(examples), training_metric.name()))
    if seed:
        print('random.seed(%d)' % seed)
        random.seed(seed)
    model = clone_model(model)
    for t in range(T):
        random.shuffle(examples)
        num_correct = 0
        for example in examples:
            # Reparse with current weights.
            parses = model.parse_input(example.input)
            # Get the highest-scoring "good" parse among the candidate parses.
            good_parses = [p for p in parses if training_metric.evaluate(example, [p])]
            if good_parses:
                target_parse = good_parses[0]
                # Get all (score, parse) pairs.
                scores = [(p.score + cost(target_parse, p), p) for p in parses]
                # Get the maximal score.
                max_score = sorted(scores, key=scored_parse_key_fn)[-1][0]
                # Get all the candidates with the max score and choose one randomly.
                predicted_parse = random.choice([p for s, p in scores if s == max_score])
                if training_metric.evaluate(example, [predicted_parse]):
                    num_correct += 1
                update_weights(model, target_parse, predicted_parse, eta)
        print('SGD iteration %d: train accuracy: %.3f' % (t, 1.0 * num_correct / len(examples)))
    print_weights(model.weights)
    return model

def cost(parse_1, parse_2):
    return 0.0 if parse_1 == parse_2 else 1.0

def clone_model(model):
    return Model(grammar=model.grammar,
                 feature_fn=model.feature_fn,
                 weights=defaultdict(float),  # Zero the weights.
                 executor=model.executor)

def update_weights(model, target_parse, predicted_parse, eta):
    target_features = model.feature_fn(target_parse)
    predicted_features = model.feature_fn(predicted_parse)
    for f in set(list(target_features.keys()) + list(predicted_features.keys())):
        update = target_features[f] - predicted_features[f]
        if update != 0.0:
            # print 'update %g + %g * %g = %g\t%s' % (
            #     model.weights[f], eta, update, model.weights[f] + eta * update, f)
            model.weights[f] += eta * update

def print_weights(weights, n=20):
    pairs = [(value, str(key)) for key, value in list(weights.items()) if value != 0]
    pairs = sorted(pairs, reverse=True)
    print()
    if len(pairs) < n * 2:
        print('Feature weights:')
        for value, key in pairs:
            print('%8.1f\t%s' % (value, key))
    else:
        print('Top %d and bottom %d feature weights:' % (n, n))
        for value, key in pairs[:n]:
            print('%8.1f\t%s' % (value, key))
        print('%8s\t%s' % ('...', '...'))
        for value, key in pairs[-n:]:
            print('%8.1f\t%s' % (value, key))
    print()


# demo =========================================================================

def demo_learning_from_semantics(domain):
    from example import Example
    print('\nDemo of learning from semantics')
    # Strip denotations, just to prove that we're learning from semantics.
    def strip_denotation(example):
        return Example(input=example.input, semantics=example.semantics)
    examples = [strip_denotation(example) for example in domain.train_examples()]
    model = domain.model()
    model = latent_sgd(model=model, examples=examples, training_metric=SemanticsAccuracyMetric())

def demo_learning_from_denotations(domain):
    from example import Example
    print('\nDemo of learning from denotations')
    # Strip semantics, just to prove that we're learning from denotations.
    def strip_semantics(example):
        return Example(input=example.input, denotation=example.denotation)
    examples = [strip_semantics(example) for example in domain.train_examples()]
    model = domain.model()
    model = latent_sgd(model=model, examples=examples, training_metric=DenotationAccuracyMetric())

def arithmetic_demo():
    from arithmetic import ArithmeticDomain
    demo_learning_from_semantics(ArithmeticDomain())
    demo_learning_from_denotations(ArithmeticDomain())

def travel_demo():
    from travel import TravelDomain
    demo_learning_from_semantics(TravelDomain())

def geoquery_demo():
    from geoquery import GeoQueryDomain
    demo_learning_from_denotations(GeoQueryDomain())


if __name__ == '__main__':
    # arithmetic_demo()
    # travel_demo()
    geoquery_demo()
