__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

import math
import random
from collections import defaultdict, Counter

from metrics import SemanticsAccuracyMetric, DenotationAccuracyMetric
from scoring import Model, score


def latent_sgd(
        model,
        examples,
        training_metric,
        T=10,
        eta=0.1,
        seed=None,
        loss='hinge',
        l2_penalty=0.0,
        epsilon=1e-7):
    """
    Parameters
    ----------
    model : `scoring.Model`
    examples : iterable of `example.Example`
    training_metric : `metric.Metric`
    T : int
        Maximum number of training instances. This can be cut short
        if the error or AdaGrad magnitude drop below `epsilon`.
    eta : float
        Learning rate
    seed : int or None
        Use to fix the randomization in how examples are shuffled and
        ties are decided.
    loss : str
        Either 'hinge' or 'log'.
    l2_penalty : float
        L2 penalty constant to apply to each weight. If 0.0, then
        no penalty is imposed. Larger weights correspond to a stronger
        penalty.
    epsilon : float
        Tolerance for stopping learning. If either the total error
        or the adagrad magnitude drops below this, then learning
        is terminated.

    Returns
    -------
    Trained `scoring.Model` instance.
    """
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
    adagrad = defaultdict(float)
    # No margin cost for log-loss objective:
    costfunc = cost if loss == 'hinge' else (lambda x, y : 0.0)
    for t in range(T):
        random.shuffle(examples)
        num_correct = 0
        ada_update_mag = 0.0
        error = 0.0
        for example in examples:
            # Reparse with current weights.
            parses = model.parse_input(example.input)
            # Get the highest-scoring "good" parse among the candidate parses.
            good_parses = [p for p in parses if training_metric.evaluate(example, [p])]
            if good_parses:
                target_parse = good_parses[0]
                # Get all (score, parse) pairs.
                scores = [(p.score + costfunc(target_parse, p), p) for p in parses]
                # Get the maximal score.
                max_score = sorted(scores, key=scored_parse_key_fn)[-1][0]
                # Error:
                error += max_score - target_parse.score
                # Get all the candidates with the max score and choose one randomly.
                predicted_parse = random.choice([p for s, p in scores if s == max_score])
                if training_metric.evaluate(example, [predicted_parse]):
                    num_correct += 1
                ada_update_mag, adagrad = update_weights(
                    model,
                    target_parse,
                    predicted_parse,
                    eta,
                    l2_penalty,
                    loss, adagrad,
                    ada_update_mag)
        acc = 1.0 * num_correct / len(examples)
        print(
            'iter. {0:}; '
            'err. {1:0.07f}; '
            'AdaGrad mag. {2:0.07f}; '
            'train acc. {3:0.04f}'.format(t+1, error, ada_update_mag, acc))
        if error < epsilon or ada_update_mag < epsilon:
            break
    print_weights(model.weights)
    return model

def cost(parse_1, parse_2):
    return 0.0 if parse_1 == parse_2 else 1.0

def clone_model(model):
    return Model(grammar=model.grammar,
                 feature_fn=model.feature_fn,
                 weights=defaultdict(float),  # Zero the weights.
                 executor=model.executor)

def update_weights(model, target_parse, predicted_parse, eta, l2_penalty, loss, adagrad, ada_update_mag):
    target_features = model.feature_fn(target_parse)
    predicted_features = model.feature_fn(predicted_parse)
    all_f = set(target_features.keys()) | set(predicted_features.keys())
    # Gradient:
    grad = defaultdict(float)
    if loss == 'hinge':
        for f in all_f:
            grad[f] = target_features[f] - predicted_features[f]
    else: # This is the log-loss:
        grad = Counter(target_features)
        grad.subtract(predicted_features)
    # L2 penalty:
    for f, w in model.weights.items():
        grad[f] -= l2_penalty * w
    # Adaptive gradient update:
    for f, w in grad.items():
        adagrad[f] += grad[f]**2
        ada_decay = math.sqrt(adagrad[f])
        if ada_decay != 0.0:
            dw = eta * (grad[f] / ada_decay)
            model.weights[f] += dw
            ada_update_mag += dw**2
    return (ada_update_mag, adagrad)


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
