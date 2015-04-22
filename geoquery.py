"""
TODO: comment.

Note that the semantic parsing model given here is far from optimal for the
GeoQuery domain.  This is intentional.  The principle goals of SippyCup are
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

import re
import sys
from collections import defaultdict

from annotator import Annotator, TokenAnnotator
from domain import Domain
from example import Example
from experiment import evaluate_for_domain, test_executor, evaluate_model, sample_wins_and_losses, interact, train_test_for_domain, learn_lexical_semantics, evaluate_dev_examples_for_domain, find_best_rules
from metrics import denotation_match_metrics, DenotationAccuracyMetric, DenotationOracleAccuracyMetric
from geo880 import geo880_train_examples, geo880_test_examples
from geobase import GeobaseReader
from graph_kb import GraphKB, GraphKBExecutor
from parsing import Grammar, Rule
from scoring import rule_features


# semantics helper functions ===================================================

def sems_0(sems):
    return sems[0]

def sems_1(sems):
    return sems[1]

def reverse(relation_sem):
    """TODO"""
    # relation_sem is a lambda function which takes an arg and forms a pair,
    # either (rel, arg) or (arg, rel).  We want to swap the order of the pair.
    def apply_and_swap(arg):
        pair = relation_sem(arg)
        return (pair[1], pair[0])
    return apply_and_swap


# GeoQueryDomain ===============================================================

class GeoQueryDomain(Domain):
    def __init__(self):
        self.geobase = GraphKB(GeobaseReader().tuples)
        self.geobase_executor = GraphKBExecutor(self.geobase)

    def train_examples(self):
        return geo880_train_examples

    def test_examples(self):
        return geo880_test_examples

    def dev_examples(self):
        return [

            # Entities .........................................................

            Example(input='utah',
                    semantics='/state/utah',
                    denotation=('/state/utah',)),

            Example(input='austin texas',
                    semantics=('.and', '/city/austin_tx', ('/state/texas', 'contains')),
                    denotation=('/city/austin_tx',)),

            # Types ............................................................

            Example(input='rivers',
                    semantics='river',
                    denotation=('/river/allegheny', '/river/arkansas', '/river/bighorn', '/river/canadian', '/river/chattahoochee', '/river/cheyenne', '/river/cimarron', '/river/clark_fork', '/river/colorado', '/river/columbia', '/river/connecticut', '/river/cumberland', '/river/dakota', '/river/delaware', '/river/gila', '/river/green', '/river/hudson', '/river/little_missouri', '/river/mississippi', '/river/missouri', '/river/neosho', '/river/niobrara', '/river/north_platte', '/river/ohio', '/river/ouachita', '/river/pearl', '/river/pecos', '/river/potomac', '/river/powder', '/river/red', '/river/republican', '/river/rio_grande', '/river/roanoke', '/river/rock', '/river/san_juan', '/river/smoky_hill', '/river/snake', '/river/south_platte', '/river/st._francis', '/river/tennessee', '/river/tombigbee', '/river/wabash', '/river/washita', '/river/wateree_catawba', '/river/white', '/river/yellowstone')),

            # Joins ............................................................

            Example(input='traverses utah',
                    semantics=('traverses', '/state/utah'),
                    denotation=('/lake/great_salt_lake', '/river/colorado', '/river/green', '/river/san_juan', '/road/15', '/road/70', '/road/80', '/road/84')),

            Example(input='capital of new york',
                    semantics=('/state/new_york', 'capital'),
                    denotation=('/city/albany_ny',)),

            Example(input='bordering new york',
                    semantics=('borders', '/state/new_york'),
                    denotation=('/state/connecticut', '/state/massachusetts', '/state/new_jersey', '/state/pennsylvania', '/state/vermont')),

            Example(input='capitals of states',
                    semantics=('state', 'capital'),
                    denotation=('/city/albany_ny', '/city/annapolis_md', '/city/atlanta_ga', '/city/augusta_me', '/city/austin_tx', '/city/baton_rouge_la', '/city/bismarck_nd', '/city/boise_id', '/city/boston_ma', '/city/carson_city_nv', '/city/charleston_wv', '/city/cheyenne_wy', '/city/columbia_sc', '/city/columbus_oh', '/city/concord_nh', '/city/denver_co', '/city/des_moines_ia', '/city/dover_de', '/city/frankfort_ky', '/city/harrisburg_pa', '/city/hartford_ct', '/city/helena_mt', '/city/honolulu_hi', '/city/indianapolis_in', '/city/jackson_ms', '/city/jefferson_city_mo', '/city/juneau_ak', '/city/lansing_mi', '/city/lincoln_ne', '/city/little_rock_ar', '/city/madison_wi', '/city/montgomery_al', '/city/montpelier_vt', '/city/nashville_tn', '/city/oklahoma_city_ok', '/city/olympia_wa', '/city/phoenix_az', '/city/pierre_sd', '/city/providence_ri', '/city/raleigh_nc', '/city/richmond_va', '/city/sacramento_ca', '/city/salem_or', '/city/salt_lake_city_ut', '/city/santa_fe_nm', '/city/springfield_il', '/city/st._paul_mn', '/city/tallahassee_fl', '/city/topeka_ks', '/city/trenton_nj', '/city/washington_dc')),

            # Intersection (conjunction) .......................................

            Example(input='rivers that traverse utah',
                    semantics=('.and', 'river', ('traverses', '/state/utah')),
                    denotation=('/river/colorado', '/river/green', '/river/san_juan')),

            Example(input='traversed by rivers that traverse utah',
                    semantics=(('.and', 'river', ('traverses', '/state/utah')), 'traverses'),
                    denotation=('/state/arizona', '/state/california', '/state/colorado', '/state/nevada', '/state/new_mexico', '/state/utah', '/state/wyoming')),

            Example(input='states traversed by rivers that traverse utah',
                    semantics=('.and', 'state', (('.and', 'river', ('traverses', '/state/utah')), 'traverses')),
                    denotation=('/state/arizona', '/state/california', '/state/colorado', '/state/nevada', '/state/new_mexico', '/state/utah', '/state/wyoming')),

            Example(input='states bordering new york',
                    semantics=('.and', 'state', ('borders', '/state/new_york')),
                    denotation=('/state/connecticut', '/state/massachusetts', '/state/new_jersey', '/state/pennsylvania', '/state/vermont')),

            Example(input='capitals of states bordering new york',
                    semantics=(('.and', 'state', ('borders', '/state/new_york')), 'capital'),
                    denotation=('/city/boston_ma', '/city/harrisburg_pa', '/city/hartford_ct', '/city/montpelier_vt', '/city/trenton_nj')),

            Example(input='cities named springfield',
                    semantics=('.and', 'city', ('name', 'springfield')),
                    denotation=('/city/springfield_il', '/city/springfield_ma', '/city/springfield_mo', '/city/springfield_oh')),

            Example(input='states have cities named springfield',
                    semantics=('.and', 'state', ('contains', ('.and', 'city', ('name', 'springfield')))),
                    denotation=('/state/illinois', '/state/massachusetts', '/state/missouri', '/state/ohio')),

            # Counting .........................................................

            Example(input='how many states',
                    semantics=('.count', 'state'),
                    denotation=(51,)),

            Example(input='how many states are traversed by rivers that traverse utah',
                    semantics=('.count', ('.and', 'state', (('.and', 'river', ('traverses', '/state/utah')), 'traverses'))),
                    denotation=(7,)),

            Example(input='how many states border new york',
                    semantics=('.count', ('.and', 'state', ('borders', '/state/new_york'))),
                    denotation=(5,)),

            Example(input='how many states have cities named springfield',
                    semantics=('.count', ('.and', 'state', ('contains', ('.and', 'city', ('name', 'springfield'))))),
                    denotation=(4,)),

            # Comparisons ......................................................

            Example(input='height of bona',
                    semantics=('/mountain/bona', 'height'),
                    denotation=(5044,)),

            Example(input='mountains with height 5044',
                    semantics=('.and', 'mountain', ('height', 5044)),
                    denotation=('/mountain/bona',)),

            Example(input='mountains with height greater than 5044',
                    semantics=('.and', 'mountain', ('height', ('.gt', 5044))),
                    denotation=('/mountain/foraker', '/mountain/mckinley', '/mountain/st._elias')),

            Example(input='mountains with height greater than height of bona',
                    semantics=('.and', 'mountain', ('height', ('.gt', ('/mountain/bona', 'height')))),
                    denotation=('/mountain/foraker', '/mountain/mckinley', '/mountain/st._elias')),

            # same semantics as previous, but uses ellipsis -- tough!
            Example(input='mountains with height greater than bona',
                    semantics=('.and', 'mountain', ('height', ('.gt', ('/mountain/bona', 'height')))),
                    denotation=('/mountain/foraker', '/mountain/mckinley', '/mountain/st._elias')),

            # Disjunctions (unions) ............................................

            Example(input='texas or maine',
                    semantics=('.or', '/state/texas', '/state/maine'),
                    denotation=('/state/maine', '/state/texas')),

            Example(input='cities or towns named springfield',
                    semantics=('.and', ('.or', 'city', 'city'), ('name', 'springfield')),
                    denotation=('/city/springfield_il', '/city/springfield_ma', '/city/springfield_mo', '/city/springfield_oh')),

            Example(input='states bordering texas or maine',
                    semantics=('.and', 'state', ('borders', ('.or', '/state/texas', '/state/maine'))),
                    denotation=('/state/arkansas', '/state/louisiana', '/state/maine', '/state/new_mexico', '/state/oklahoma')),

        ]

    # This list of lexical rules was generated by counting all 248 tokens
    # in geo880_train_examples and then excluding those which plainly refer
    # to entities, types, or relations.
    optional_words = [
        'the', 'what', 'is', 'in', 'of', 'how', 'many', 'are', 'which', 'that',
        'with', 'has', 'major', 'does', 'have', 'where', 'me', 'there', 'give',
        'name', 'all', 'a', 'by', 'you', 'to', 'tell', 'other', 'it', 'do',
        'whose', 'show', 'one', 'on', 'for', 'can', 'whats', 'urban', 'them',
        'list', 'exist', 'each', 'could', 'about', '.', '?'
    ]
    
    rules_optionals = [
        Rule('$ROOT', '?$Optionals $Query ?$Optionals', sems_1),
        Rule('$Optionals', '$Optional ?$Optionals'),
    ] + [Rule('$Optional', word) for word in optional_words]
        
        #                              # occurrences in geo880_train_examples
        # Rule('$Optional', 'the'),    # 618   huge gain!
        # Rule('$Optional', 'what'),   # 386   huge gain!
        # Rule('$Optional', 'is'),     # 283   huge gain!
        # Rule('$Optional', 'in'),     # 247   no impact
        # Rule('$Optional', 'of'),     # 150   no impact
        # Rule('$Optional', 'how'),    # 111   no impact
        # Rule('$Optional', 'many'),   # 90    no impact
        # Rule('$Optional', 'are'),    # 90    some gain
        # Rule('$Optional', 'which'),  # 75    small gain
        # Rule('$Optional', 'that'),   # 48    tiny gain
        # Rule('$Optional', 'with'),   # 48    no impact
        # Rule('$Optional', 'has'),    # 43    no impact
        # Rule('$Optional', 'major'),  # 42    small gain
        # Rule('$Optional', 'does'),   # 27    no impact
        # Rule('$Optional', 'have'),   # 23    no impact
        # Rule('$Optional', 'where'),  # 17    small gain
        # Rule('$Optional', 'me'),     # 13    small gain
        # Rule('$Optional', 'there'),  # 12    no impact
        # Rule('$Optional', 'give'),   # 9     small gain
        # Rule('$Optional', 'name'),   # 9     small gain
        # Rule('$Optional', 'all'),    # 8     small gain
        # Rule('$Optional', 'a'),      # 8     no impact
        # Rule('$Optional', 'by'),     # 5     no impact
        # Rule('$Optional', 'you'),    # 3     no impact
        # Rule('$Optional', 'to'),     # 3     no impact
        # Rule('$Optional', 'tell'),   # 3     no impact
        # Rule('$Optional', 'other'),  # 3     no impact
        # Rule('$Optional', 'it'),     # 3     no impact
        # Rule('$Optional', 'do'),     # 3     no impact
        # Rule('$Optional', 'whose'),  # 2     no impact
        # Rule('$Optional', 'show'),   # 2     no impact
        # Rule('$Optional', 'one'),    # 2     no impact
        # Rule('$Optional', 'on'),     # 2     no impact
        # Rule('$Optional', 'for'),    # 2     tiny gain
        # Rule('$Optional', 'can'),    # 2     tiny gain
        # Rule('$Optional', 'whats'),  # 1     tiny gain
        # Rule('$Optional', 'urban'),  # 1     no impact
        # Rule('$Optional', 'them'),   # 1     tiny gain
        # Rule('$Optional', 'list'),   # 1     tiny gain
        # Rule('$Optional', 'exist'),  # 1     no impact
        # Rule('$Optional', 'each'),   # 1     no impact
        # Rule('$Optional', 'could'),  # 1     tiny gain
        # Rule('$Optional', 'about'),  # 1     tiny gain
        # Rule('$Optional', '.'),
        # Rule('$Optional', '?'),
        
    rules_collection_entity = [
        Rule('$Query', '$Collection', sems_0),
        Rule('$Collection', '$Entity', sems_0),
    ]

    rules_types = [
        Rule('$Collection', '$Type', sems_0),

        Rule('$Type', 'state', 'state'),
        Rule('$Type', 'states', 'state'),
        Rule('$Type', 'city', 'city'),
        Rule('$Type', 'cities', 'city'),
        Rule('$Type', 'big cities', 'city'),
        Rule('$Type', 'towns', 'city'),
        Rule('$Type', 'river', 'river'),
        Rule('$Type', 'rivers', 'river'),
        Rule('$Type', 'mountain', 'mountain'),
        Rule('$Type', 'mountains', 'mountain'),
        Rule('$Type', 'mount', 'mountain'),
        Rule('$Type', 'peak', 'mountain'),
        Rule('$Type', 'road', 'road'),
        Rule('$Type', 'roads', 'road'),
        Rule('$Type', 'lake', 'lake'),
        Rule('$Type', 'lakes', 'lake'),
        Rule('$Type', 'country', 'country'),
        Rule('$Type', 'countries', 'country'),
    ]

    rules_relations = [
        Rule('$Collection', '$Relation ?$Optionals $Collection',
             lambda sems: sems[0](sems[2])),

        Rule('$Relation', '$FwdRelation', lambda sems: (lambda arg: (sems[0], arg))),
        Rule('$Relation', '$RevRelation', lambda sems: (lambda arg: (arg, sems[0]))),

        Rule('$FwdRelation', '$FwdBordersRelation', 'borders'),
        Rule('$FwdBordersRelation', 'border'),
        Rule('$FwdBordersRelation', 'bordering'),
        Rule('$FwdBordersRelation', 'borders'),
        Rule('$FwdBordersRelation', 'neighbor'),
        Rule('$FwdBordersRelation', 'neighboring'),
        Rule('$FwdBordersRelation', 'surrounding'),
        Rule('$FwdBordersRelation', 'next to'),

        Rule('$FwdRelation', '$FwdTraversesRelation', 'traverses'),
        Rule('$FwdTraversesRelation', 'cross ?over'),
        Rule('$FwdTraversesRelation', 'flow through'),
        Rule('$FwdTraversesRelation', 'flowing through'),
        Rule('$FwdTraversesRelation', 'flows through'),
        Rule('$FwdTraversesRelation', 'go through'),
        Rule('$FwdTraversesRelation', 'goes through'),
        Rule('$FwdTraversesRelation', 'in'),
        Rule('$FwdTraversesRelation', 'pass through'),
        Rule('$FwdTraversesRelation', 'passes through'),
        Rule('$FwdTraversesRelation', 'run through'),
        Rule('$FwdTraversesRelation', 'running through'),
        Rule('$FwdTraversesRelation', 'runs through'),
        Rule('$FwdTraversesRelation', 'traverse'),
        Rule('$FwdTraversesRelation', 'traverses'),

        Rule('$RevRelation', '$RevTraversesRelation', 'traverses'),
        Rule('$RevTraversesRelation', 'has'),
        Rule('$RevTraversesRelation', 'have'),  # 'how many states have major rivers'
        Rule('$RevTraversesRelation', 'lie on'),
        Rule('$RevTraversesRelation', 'next to'),
        Rule('$RevTraversesRelation', 'traversed by'),
        Rule('$RevTraversesRelation', 'washed by'),

        Rule('$FwdRelation', '$FwdContainsRelation', 'contains'),
        # 'how many states have a city named springfield'
        Rule('$FwdContainsRelation', 'has'),
        Rule('$FwdContainsRelation', 'have'),

        Rule('$RevRelation', '$RevContainsRelation', 'contains'),
        Rule('$RevContainsRelation', 'contained by'),
        Rule('$RevContainsRelation', 'in'),
        Rule('$RevContainsRelation', 'found in'),
        Rule('$RevContainsRelation', 'located in'),
        Rule('$RevContainsRelation', 'of'),

        Rule('$RevRelation', '$RevCapitalRelation', 'capital'),
        Rule('$RevCapitalRelation', 'capital'),
        Rule('$RevCapitalRelation', 'capitals'),

        Rule('$RevRelation', '$RevHighestPointRelation', 'highest_point'),
        Rule('$RevHighestPointRelation', 'high point'),
        Rule('$RevHighestPointRelation', 'high points'),
        Rule('$RevHighestPointRelation', 'highest point'),
        Rule('$RevHighestPointRelation', 'highest points'),

        Rule('$RevRelation', '$RevLowestPointRelation', 'lowest_point'),
        Rule('$RevLowestPointRelation', 'low point'),
        Rule('$RevLowestPointRelation', 'low points'),
        Rule('$RevLowestPointRelation', 'lowest point'),
        Rule('$RevLowestPointRelation', 'lowest points'),
        Rule('$RevLowestPointRelation', 'lowest spot'),

        Rule('$RevRelation', '$RevHighestElevationRelation', 'highest_elevation'),
        Rule('$RevHighestElevationRelation', '?highest elevation'),

        Rule('$RevRelation', '$RevHeightRelation', 'height'),
        Rule('$RevHeightRelation', 'elevation'),
        Rule('$RevHeightRelation', 'height'),
        Rule('$RevHeightRelation', 'high'),
        Rule('$RevHeightRelation', 'tall'),

        Rule('$RevRelation', '$RevAreaRelation', 'area'),
        Rule('$RevAreaRelation', 'area'),
        Rule('$RevAreaRelation', 'big'),
        Rule('$RevAreaRelation', 'large'),
        Rule('$RevAreaRelation', 'size'),

        Rule('$RevRelation', '$RevPopulationRelation', 'population'),
        Rule('$RevPopulationRelation', 'big'),
        Rule('$RevPopulationRelation', 'large'),
        Rule('$RevPopulationRelation', 'populated'),
        Rule('$RevPopulationRelation', 'population'),
        Rule('$RevPopulationRelation', 'populations'),
        Rule('$RevPopulationRelation', 'populous'),
        Rule('$RevPopulationRelation', 'size'),

        Rule('$RevRelation', '$RevLengthRelation', 'length'),
        Rule('$RevLengthRelation', 'length'),
        Rule('$RevLengthRelation', 'long'),
    ]

    rules_intersection = [
        # (+22% oracle accuracy)
        Rule('$Collection', '$Collection $Collection',
             lambda sems: ('.and', sems[0], sems[1])),
        # (+6% oracle accuracy)
        # 'how many states are traversed by ...'
        Rule('$Collection', '$Collection $Optional $Collection',
             lambda sems: ('.and', sems[0], sems[2])),
        # (+3.7% oracle accuracy)
        Rule('$Collection', '$Collection $Optional $Optional $Collection',
             lambda sems: ('.and', sems[0], sems[3])),
    ]

    rules_superlatives = [
        Rule('$Collection', '$Superlative ?$Optionals $Collection', lambda sems: sems[0] + (sems[2],)),
        Rule('$Collection', '$Collection ?$Optionals $Superlative', lambda sems: sems[2] + (sems[0],)),

        Rule('$Superlative', 'largest', ('.argmax', 'area')),
        Rule('$Superlative', 'largest', ('.argmax', 'population')),
        Rule('$Superlative', 'biggest', ('.argmax', 'area')),
        Rule('$Superlative', 'biggest', ('.argmax', 'population')),
        Rule('$Superlative', 'smallest', ('.argmin', 'area')),
        Rule('$Superlative', 'smallest', ('.argmin', 'population')),
        Rule('$Superlative', 'longest', ('.argmax', 'length')),
        Rule('$Superlative', 'shortest', ('.argmin', 'length')),
        Rule('$Superlative', 'tallest', ('.argmax', 'height')),
        Rule('$Superlative', 'highest', ('.argmax', 'height')),

        Rule('$Superlative', '$MostLeast $RevRelation', lambda sems: (sems[0], sems[1])),
        Rule('$MostLeast', 'most', '.argmax'),
        Rule('$MostLeast', 'least', '.argmin'),
        Rule('$MostLeast', 'lowest', '.argmin'),
        Rule('$MostLeast', 'greatest', '.argmax'),
        Rule('$MostLeast', 'highest', '.argmax'),
    ]

    # (+4.5% oracle accuracy, +70% number of parses)
    # 'which state is the city denver located in'
    # 'which states does the mississippi river run through'
    rules_reverse_joins = [
        Rule('$Collection', '$Collection ?$Optionals $Relation',
             lambda sems: reverse(sems[2])(sems[0])),
    ]

    def rules(self):
        return (
                                                  # denotation oracle accuracy
                                                  # train   diff    test

            self.rules_optionals +                # 0.000           0.000
            self.rules_collection_entity +        # 0.000   0.000   0.000
            self.rules_types +                    # 0.003   0.003   0.000
            self.rules_relations +                # 0.125   0.122   0.139
            self.rules_intersection +             # 0.277   0.152   0.275
            self.rules_superlatives +             # 0.422   0.145   0.371
            self.rules_reverse_joins +            # 0.468   0.046   0.418

            # self.rules_counting +                 # 0.510   0.042   0.461
            # self.rules_how_many_people +          # 0.547   0.037   0.489
            # self.rules_entities +                 # 0.568   0.021   0.507
            # self.rules_where_is +                 # 0.588   0.020   0.514
            # self.rules_named +                    # 0.602   0.014   0.536
            # self.rules_entity_entity +            # 0.613   0.011   0.546
            # self.rules_flip_relations +           # 0.612  -0.005   0.561

            []                                    # 0.613           0.546
        )

    def annotators(self):
        return [TokenAnnotator(), GeobaseAnnotator(self.geobase)]

    def empty_denotation_feature(self, parse):
        features = defaultdict(float)
        if parse.denotation == ():
            features['empty_denotation'] += 1.0
        return features

    def features(self, parse):
        features = defaultdict(float)
        # TODO: turning off rule features seems to screw up learning
        # figure out what's going on here
        # maybe make an exercise of it!
        # Actually it doesn't seem to mess up final result.
        # But the train accuracy reported during SGD is misleading?
        features.update(rule_features(parse))
        features.update(self.empty_denotation_feature(parse))
        # EXERCISE: Experiment with additional features.
        return features

    def weights(self):
        weights = defaultdict(float)
        weights['empty_denotation'] = -1.0
        return weights

    def grammar(self):
        return Grammar(rules=self.rules(), annotators=self.annotators())

    def execute(self, semantics):
        return self.geobase_executor.execute(semantics)

    def metrics(self):
        return denotation_match_metrics()

    def training_metric(self):
        return DenotationAccuracyMetric()


# GeobaseAnnotator =============================================================

# EXERCISE: Make it more robust, using string edit distance or minhashing.
class GeobaseAnnotator(Annotator):
    def __init__(self, geobase):
        self.geobase = geobase

    def annotate(self, tokens):
        phrase = ' '.join(tokens)
        places = self.geobase.binaries_rev['name'][phrase]
        # places |= self.geobase.rev_index['abbreviation'][phrase]
        # TODO: $Entity?  $Location?  something that indicates type?
        return [('$Entity', place) for place in places]


# demos and experiments ========================================================

if __name__ == '__main__':
    domain = GeoQueryDomain()
    evaluate_for_domain(domain, print_examples=False)
    # evaluate_dev_examples_for_domain(domain)
    # train_test_for_domain(domain, seed=1)
    # test_executor(domain)
    # sample_wins_and_losses(domain, metric=DenotationOracleAccuracyMetric())
    # learn_lexical_semantics(domain, seed=1)
    # interact(domain, "the largest city in the largest state", T=0)
    # find_best_rules(domain)
