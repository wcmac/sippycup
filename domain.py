"""
Defines the Domain class, which represents a specific application or use case
for a semantic parsing system.  Each domain can define a number of attributes
specific to and appropriate for its intended use case:

    - a list of examples
    - a list of grammar rules
    - a list of annotators
    - a default method of constructing a grammar
    - a set of feature functions
    - a set of feature weights
    - an executor
    - a collection of evaluation metrics
    - a training metric

The SippyCup codebase defines three domains as subclasses of Domain:

    - ArithmeticDomain, defined in arithmetic.py
    - TravelDomain, defined in travel.py
    - GeoQueryDomain, defined in geoquery.py
"""

__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

from collections import defaultdict

from metrics import standard_metrics, SemanticsAccuracyMetric
from scoring import Model

class Domain:
    def train_examples(self):
        """Returns a list of training Examples suitable for the domain."""
        return []

    def dev_examples(self):
        """Returns a list of development Examples suitable for the domain."""
        return []

    def test_examples(self):
        """Returns a list of test Examples suitable for the domain."""
        return []

    def rules(self):
        """Returns a list of Rules suitable for the domain."""
        return []

    def annotators(self):
        """Returns a list of Annotators suitable for the domain."""
        return []

    def grammar(self):
        raise Exception('grammar() method not implemented')

    def features(self, parse):
        """
        Takes a parse and returns a map from feature names to float values.
        """
        return defaultdict(float)

    def weights(self):
        return defaultdict(float)

    def execute(self, semantics):
        """
        Executes a semantic representation and returns a denotation.  Both
        semantic representations and the denotations can be pretty much any
        Python values: numbers, strings, tuples, lists, sets, trees, and so on.
        Each domain will define its own spaces of semantic representations and
        denotations.
        """
        return None

    def model(self):
        return Model(grammar=self.grammar(),
                     feature_fn=self.features,
                     weights=self.weights(),
                     executor=self.execute)

    def metrics(self):
        """Returns a list of Metrics which are appropriate for the domain."""
        return standard_metrics()

    def training_metric(self):
        """
        Returns the evaluation metric which should be used to supervise training
        for this domain.
        """
        return SemanticsAccuracyMetric()
