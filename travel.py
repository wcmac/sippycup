"""
The TravelDomain focuses on queries about getting from here to there, such as:

    driving directions to williamsburg virginia
    how long a bus ride from atlantic city to new york city
    cheapest airfare from newark nj to charleston sc

Queries in this domain always contain at least one location, which may be either
the destination or the origin, and they may contain both.  They may also specify
a transportation mode (such as car, bus, or air), and they may specify a
request type (such as directions, schedule, distance, or travel time).

The TravelDomain contains 100 example queriess which were collected from the AOL
search query dataset.  Details below.

The semantic representation is a map of key-value pairs. The possible keys and
values are:

    'domain'      : 'travel' if query is in-domain, else 'other'
    'type'        : 'distance', 'directions', 'schedule', 'cost', ...
    'mode'        : 'air', 'car', 'transit', 'boat', 'bus', 'train', 'bike', 'taxi'
    'origin'      : the origin location
    'destination' : the destination location

Only the 'domain' field is required; the rest are optional.

The location representation for the 'origin' and 'destination' fields is itself
a map of key-value pairs, using information derived from GeoNames.org:

    'id'          : the location id in the GeoNames database
    'name'        : a string representation of the full name of the location

For examples of the semantic representation, see the examples() method.

The TravelDomain does not define or use an executor or denotations, only
semantic representations.

Note that the semantic parsing model given here is far from optimal for the
travel domain.  This is intentional.  The principle goals of SippyCup are
pedagogical.  The limitations of the current model represent opportunities for
learning.  See the exercises in the accompanying IPython Notebook.
"""

__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

from annotator import TokenAnnotator
from domain import Domain
from example import Example
from experiment import evaluate_for_domain, train_test_for_domain, interact, sample_wins_and_losses, evaluate_dev_examples_for_domain
from geonames import GeoNamesAnnotator
from graph_kb import GraphKB
from metrics import semantics_match_metrics, SemanticsOracleAccuracyMetric, HasParseMetric
from parsing import Grammar, Rule, parse_input
from scoring import rule_features
from travel_examples import travel_train_examples, travel_test_examples
from travel_examples_dev import travel_dev_examples


# semantics helper functions ===================================================

def sems_0(sems):
    return sems[0]

def sems_1(sems):
    return sems[1]

def merge_dicts(d1, d2):
    if not d2:
        return d1
    result = d1.copy()
    result.update(d2)
    return result


# TravelDomain =================================================================

class TravelDomain(Domain):
    def __init__(self):
        self.geonames_annotator = GeoNamesAnnotator()

    def train_examples(self):
        return travel_train_examples

    def dev_examples(self):
        return travel_dev_examples

    def test_examples(self):
        return travel_test_examples

    # Define the basic structure of a $TravelQuery.
    # A $TravelQuery is a sequence of one or more $TravelQueryElements.
    # A $TravelQueryElement is either a $TravelLocation or a $TravelArgument.
    # EXERCISE: This approach permits any number of $FromLocations and $ToLocations.
    # Find a way to require that (a) there is at least one location,
    # (b) there are not multiple $FromLocations or $ToLocations.
    rules_travel = [
        Rule('$ROOT', '$TravelQuery', sems_0),
        Rule('$TravelQuery', '$TravelQueryElements',
             lambda sems: merge_dicts({'domain': 'travel'}, sems[0])),
        Rule('$TravelQueryElements', '$TravelQueryElement ?$TravelQueryElements',
             lambda sems: merge_dicts(sems[0], sems[1])),
        Rule('$TravelQueryElement', '$TravelLocation', sems_0),
        Rule('$TravelQueryElement', '$TravelArgument', sems_0),
    ]

    # Define query elements which specify the origin or destination.
    rules_travel_locations = [
        Rule('$TravelLocation', '$ToLocation', sems_0),
        Rule('$TravelLocation', '$FromLocation', sems_0),
        Rule('$ToLocation', '$To $Location', lambda sems: {'destination': sems[1]}),
        Rule('$FromLocation', '$From $Location', lambda sems: {'origin': sems[1]}),
        Rule('$To', 'to'),
        Rule('$From', 'from'),
    ]

    # Allow travel arguments which specify the mode of travel.
    # Raises oracle accuracy to ~20%.
    # All lexical items are either obvious or attested in training data.
    rules_travel_modes = [
        Rule('$TravelArgument', '$TravelMode', sems_0),

        Rule('$TravelMode', '$AirMode', {'mode': 'air'}),
        Rule('$TravelMode', '$BikeMode', {'mode': 'bike'}),
        Rule('$TravelMode', '$BoatMode', {'mode': 'boat'}),
        Rule('$TravelMode', '$BusMode', {'mode': 'bus'}),
        Rule('$TravelMode', '$CarMode', {'mode': 'car'}),
        Rule('$TravelMode', '$TaxiMode', {'mode': 'taxi'}),
        Rule('$TravelMode', '$TrainMode', {'mode': 'train'}),
        Rule('$TravelMode', '$TransitMode', {'mode': 'transit'}),

        Rule('$AirMode', 'air fare'),
        Rule('$AirMode', 'air fares'),
        Rule('$AirMode', 'airbus'),
        Rule('$AirMode', 'airfare'),
        Rule('$AirMode', 'airfares'),
        Rule('$AirMode', 'airline'),
        Rule('$AirMode', 'airlines'),
        Rule('$AirMode', '?by air'),
        Rule('$AirMode', 'flight'),
        Rule('$AirMode', 'flights'),
        Rule('$AirMode', 'fly'),

        Rule('$BikeMode', '?by bike'),
        Rule('$BikeMode', 'bike riding'),

        Rule('$BoatMode', '?by boat'),
        Rule('$BoatMode', 'cruise'),
        Rule('$BoatMode', 'cruises'),
        Rule('$BoatMode', 'norwegian cruise lines'),

        Rule('$BusMode', '?by bus'),
        Rule('$BusMode', 'bus tours'),
        Rule('$BusMode', 'buses'),
        Rule('$BusMode', 'shutle'),
        Rule('$BusMode', 'shuttle'),

        Rule('$CarMode', '?by car'),
        Rule('$CarMode', 'drive'),
        Rule('$CarMode', 'driving'),
        Rule('$CarMode', 'gas'),

        Rule('$TaxiMode', 'cab'),
        Rule('$TaxiMode', 'car service'),
        Rule('$TaxiMode', 'taxi'),

        Rule('$TrainMode', '?by train'),
        Rule('$TrainMode', 'trains'),
        Rule('$TrainMode', 'amtrak'),

        Rule('$TransitMode', '?by public transportation'),
        Rule('$TransitMode', '?by ?public transit'),
    ]

    # Allow arguments which indicate travel without specifying a mode.
    # Adds roughly 4% in oracle accuracy.
    rules_travel_triggers = [
        Rule('$TravelArgument', '$TravelTrigger', {}),
        # All of the following lexical rules are obvious or are based on
        # inspection of training data -- not inspection of test data!
        Rule('$TravelTrigger', 'tickets'),
        Rule('$TravelTrigger', 'transportation'),
        Rule('$TravelTrigger', 'travel'),
        Rule('$TravelTrigger', 'travel packages'),
        Rule('$TravelTrigger', 'trip'),
    ]

    # Allow travel arguments which specify the type of information requested.
    rules_request_types = [
        Rule('$TravelArgument', '$RequestType', sems_0),

        Rule('$RequestType', '$DirectionsRequest', {'type': 'directions'}),
        Rule('$RequestType', '$DistanceRequest', {'type': 'distance'}),
        Rule('$RequestType', '$ScheduleRequest', {'type': 'schedule'}),
        Rule('$RequestType', '$CostRequest', {'type': 'cost'}),

        Rule('$DirectionsRequest', 'directions'),
        Rule('$DirectionsRequest', 'how do i get'),
        Rule('$DistanceRequest', 'distance'),
        Rule('$ScheduleRequest', 'schedule'),
        Rule('$CostRequest', 'cost'),
    ]

    # Allow optional words around travel query elements.
    rules_optionals = [
        # EXERCISE: These rules introduce some spurious ambiguity.  Figure out
        # why, and propose a way to avoid or minimize the spurious ambiguity.
        Rule('$TravelQueryElement', '$TravelQueryElement $Optionals', sems_0),
        Rule('$TravelQueryElement', '$Optionals $TravelQueryElement', sems_1),

        Rule('$Optionals', '$Optional ?$Optionals'),

        Rule('$Optional', '$Show'),
        Rule('$Optional', '$Modifier'),
        Rule('$Optional', '$Carrier'),
        Rule('$Optional', '$Stopword'),
        Rule('$Optional', '$Determiner'),

        Rule('$Show', 'book'),
        Rule('$Show', 'give ?me'),
        Rule('$Show', 'show ?me'),

        Rule('$Modifier', 'cheap'),
        Rule('$Modifier', 'cheapest'),
        Rule('$Modifier', 'discount'),
        Rule('$Modifier', 'honeymoon'),
        Rule('$Modifier', 'one way'),
        Rule('$Modifier', 'direct'),
        Rule('$Modifier', 'scenic'),
        Rule('$Modifier', 'transatlantic'),
        Rule('$Modifier', 'one day'),
        Rule('$Modifier', 'last minute'),

        Rule('$Carrier', 'delta'),
        Rule('$Carrier', 'jet blue'),
        Rule('$Carrier', 'spirit airlines'),
        Rule('$Carrier', 'amtrak'),

        Rule('$Stopword', 'all'),
        Rule('$Stopword', 'of'),
        Rule('$Stopword', 'what'),
        Rule('$Stopword', 'will'),
        Rule('$Stopword', 'it'),
        Rule('$Stopword', 'to'),

        Rule('$Determiner', 'a'),
        Rule('$Determiner', 'an'),
        Rule('$Determiner', 'the'),
    ]

    # Allow any query to be parsed as a non-travel query.
    rules_not_travel = [
        Rule('$ROOT', '$NotTravelQuery', sems_0),
        Rule('$NotTravelQuery', '$Text', {'domain': 'other'}),
        Rule('$Text', '$Token ?$Text'),
    ]

    def rules(self):
        return (                                  # semantics oracle accuracy
            self.rules_travel +                   # 0% train, 0% test
            self.rules_travel_locations +         # 0% train, 0% test
            self.rules_travel_modes +             # 13% train, 4% test
            self.rules_travel_triggers +          # 17% train, 12% test
            self.rules_request_types +            # 20% train, 16% test
            self.rules_optionals +                # 40% train, 20% test
            self.rules_not_travel +               # 57% train, 48% test
            []
        )

    def annotators(self):
        return [TokenAnnotator(), self.geonames_annotator]

    def grammar(self):
        return Grammar(rules=self.rules(), annotators=self.annotators())

    def features(self, parse):
        return rule_features(parse)

    def metrics(self):
        return semantics_match_metrics() + [HasTravelParseMetric()]


# HasTravelParseMetric ---------------------------------------------------------

def is_travel_parse(parse):
    return parse.semantics.get('domain') == 'travel'

class HasTravelParseMetric(HasParseMetric):
    def __init__(self):
        HasParseMetric.__init__(self,
                                name='has travel parse',
                                parse_filter_fn=is_travel_parse)


# trigger grammar --------------------------------------------------------------

class ContainsLocationDomain(Domain):
    def __init__(self):
        self.geonames_annotator = GeoNamesAnnotator()

    def examples(self):
        return [
            Example(input='xuxux', semantics='{}'),
            Example(input='xuxux miami', semantics='{}'),
            Example(input='miami xuxux', semantics='{}'),
            Example(input='xuxux miami xuxux', semantics='{}'),
        ]

    def rules(self):
        return [
            Rule('$ROOT', '?$Optionals $Location ?$Optionals', sems_1),
            Rule('$Optionals', '$Optional ?$Optionals'),
            Rule('$Optional', '$Token'),
        ]

    def annotators(self):
        return [TokenAnnotator(), self.geonames_annotator]

    def grammar(self):
        return Grammar(rules=self.rules(), annotators=self.annotators())

    def metrics(self):
        return semantics_match_metrics() + [HasTravelParseMetric()]

def filter_queries_containing_locations(start=0, size=10):
    import re
    line_pattern = re.compile(r'^ *[0-9]+ (.*)$')
    queries = []
    query_file = '/Users/wcmac/Desktop/aol-data/AOL-user-ct-collection/20150220/possible-travel-queries.txt'
    f = open(query_file, 'rU')
    for line in f.readlines():
        match = line_pattern.match(line)
        if not match:
            raise Exception('unexpected line: %s' % line)
        query = match.group(1)
        queries.append(query)
    f.close()
    print('Read %d queries' % len(queries))
    selected_queries = queries[start:(start+size)]
    print('Selected %d queries' % len(selected_queries))

    domain = ContainsLocationDomain()
    grammar = domain.grammar()
    for query in selected_queries:
        print()
        print('Trying to parse', query)
        parses = parse_input(grammar, query)
        # parses = filter(lambda parse: domain.is_travel_parse(parse), parses)
        if len(parses) > 0:
            print('got %d parses' % len(parses))
            for parse in parses:
                print(parse.semantics)
        else:
            print('no parse')


# experiments ------------------------------------------------------------------

def overtriggering_experiment():
    domain = TravelDomain()
    grammar = domain.grammar()
    import re
    line_pattern = re.compile(r'^ *[0-9]+ (.*)$')
    queries = []
    query_file = '/Users/wcmac/Desktop/aol-data/AOL-user-ct-collection/all-queries-counted.txt'
    f = open(query_file, 'rU')
    for line in f.readlines():
        match = line_pattern.match(line)
        if not match:
            raise Exception('unexpected line: %s' % line)
        query = match.group(1)
        parses = parse_input(grammar, query)
        parses = [parse for parse in parses if domain.is_travel_parse(parse)]
        if len(parses) > 0:
            print()
            print(query)
            for parse in parses:
                print(parse.semantics)
        queries.append(' '.join(query))
        if len(queries) % 1000 == 0:
            print()
            print('-' * 80)
            print('Processed %d queries' % len(queries))
    f.close()


if __name__ == '__main__':
    domain = TravelDomain()
    evaluate_for_domain(domain, print_examples=False)
    # evaluate_dev_examples_for_domain(domain)
    # train_test_for_domain(domain, seed=1)
    # overtriggering_experiment()
    # interact(domain, 'directions from boston to austin by bike')
    # evaluate_for_domain(ContainsLocationDomain())
    # filter_queries_containing_locations()
    # sample_wins_and_losses(domain=domain, metric=SemanticsOracleAccuracyMetric())
    # learn_lexical_semantics(domain, seed=1)
