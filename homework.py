#!/usr/bin/env python
# coding: utf-8

# # [CS224U](https://web.stanford.edu/class/cs224u/) Homework 5
# 
# This homework is distributed in three content-identical formats (html, py,
# ipynb) as part of the SippyCup codebase. All seven problems are required.
# You're encouraged to turn your work in as iPython HTML output or as a Python
# script. This work is due by the start of class on May 16.
# 
# Be sure to put this code, or run this notebook, inside [the SippyCup
# codebase](https://github.com/wcmac/sippycup).
# 
# * [Arithmetic domain](#Arithmetic-domain)
#   * [Question 1](#Question-1)
#   * [Question 2](#Question-2)
#   * [Question 3](#Question-3)
#   
# * [Travel domain](#Travel-domain)  
#   * [Question 4](#Question-4)
#   * [Question 5](#Question-5)
#   
# * [GeoQuery domain](#GeoQuery-domain)  
#   * [Question 6](#Question-6)
#   * [Question 7](#Question-7)

# ## Arithmetic domain
#
# SippyCup includes a module `arithmetic` with a class
# `ArithmeticDomain` that brings together the examples from unit 1.
# Here's an example of the sort of use you'll make of this domain
# for these homework problems.

# In[ ]:

from arithmetic import ArithmeticDomain
from parsing import parse_to_pretty_string

# Import the domain and make sure all is well:
math_domain = ArithmeticDomain()

# Core grammar:
math_grammar = math_domain.grammar()

# A few examples:
parses = math_grammar.parse_input("minus two plus three")
for parse in parses:
    print '\nParse:\n', parse_to_pretty_string(parse, show_sem=True)
    print 'Denotation:', math_domain.execute(parse.semantics)


# This is a convenience function we'll use for seeing what the grammar
# is doing:

# In[ ]:

def display_examples(utterances, grammar=None, domain=None):
    for utterance in utterances:        
        print "="*70
        print utterance
        parses = grammar.parse_input(utterance)
        for parse in parses:
            print '\nParse:\n', parse_to_pretty_string(parse, show_sem=True)
            print 'Denotation:', domain.execute(parse.semantics)


# ### Question 1
# 
# Your task is to extend `ArithmeticDomain` to include the unary
# operators `squared` and `cubed`, which form expressions like `three
# squared` and `nine cubed`. The following code will help
# you get started on this. __Submit__: your completion of this code.

# In[ ]:

from arithmetic import ArithmeticDomain
from parsing import Rule, add_rule

# Resort to the original grammar to avoid repeatedly adding the same
# rules to the grammar during debugging, which multiplies the number
# of parses without changing the set of parses produced:
math_domain = ArithmeticDomain()
math_grammar = math_domain.grammar()

# Here's where your work should go:

# Add rules to the grammar:

# Extend domain.ops appropriately:

# Make sure things are working:
display_examples(('three squared', 'minus three squared', 'four cubed'), 
                 grammar=math_grammar, domain=math_domain)


# ### Question 2
# 
# Your task is to extend `ArithmeticDomain` to support numbers with
# decimals, so that you can parse all expressions of the form `N point
# D` where `N` and `D` both denote `int`s. You can assume that both
# numbers are both spelled out as single words, as in "one point
# twelve" rather than "one point one two". (The grammar fragment has
# only "one", "two", "three", and "four" anyway.) __Submit__: your
# completion of the following code.
# 
# __Important__: your grammar should not create spurious parses like
# `(two times three) point four`. This means that you can't treat
# `point` like the other binary operators in your syntactic grammar.
# This will require you to add special rules to handle the internal
# structure of these decimal numbers.

# In[ ]:

from arithmetic import ArithmeticDomain
from parsing import Rule, add_rule

# Clear out the grammar; remove this if you want your question 1 
# extension to combine with these extensions:
math_domain = ArithmeticDomain()
math_grammar = math_domain.grammar()

# Remember to add these rules to the grammar!
integer_rules = [ 
    Rule('$I', 'one', 1), 
    Rule('$I', 'two', 2), 
    Rule('$I', 'three', 3), 
    Rule('$I', 'four', 4) ]

tens_rules = [
    Rule('$T', 'one', 1),
    Rule('$T', 'two', 2),
    Rule('$T', 'three', 3),
    Rule('$T', 'four', 4) ]

# Add the above rules to math_grammar:

# Add rules to the grammar for using the above:

# Extend domain.ops:

# Make sure things are working:
display_examples(('four point two', 'minus four point one', 'two minus four point one'),
                 grammar=math_grammar, domain=math_domain)


# ### Question 3
# 
# Extend the grammar to support the multi-word expression `the average of` as 
# in `the average of one and four`. Your solution is required to treat
# each word in this multi-word expression as its own lexical item.
# Other than that, you have a lot of design freedom. Your solution can
# be limited to the case where the conjunction consists of just two
# numbers. __Submit__: your completion of this starter code.

# In[ ]:

from arithmetic import ArithmeticDomain
from parsing import Rule, add_rule
import numpy as np

math_domain = ArithmeticDomain()
math_grammar = math_domain.grammar()

# Add rules to the grammar:

# Extend domain.ops:

# Make sure things are working:
display_examples(('the one', 'the average of one and four'),
                 grammar=math_grammar, domain=math_domain)


# ## Travel domain

# Here's an illustration of how parsing and interpretation work in
# this domain:

# In[ ]:

from travel import TravelDomain

travel_domain = TravelDomain()
travel_grammar = travel_domain.grammar()

display_examples(
    ("flight from Boston to San Francisco",
     "directions from New York to Philadelphia",
     "directions New York to Philadelphia"),
    grammar=travel_grammar,
    domain=travel_domain)


# For these questions, we'll combine grammars with machine learning.
# Here's now to train and evaluate a model using the grammar 
# that is included in `TravelDomain` along with a basic feature
# function.

# In[ ]:

from travel import TravelDomain
from scoring import Model
from experiment import train_test
from travel_examples import travel_train_examples, travel_test_examples
from collections import defaultdict

travel_domain = TravelDomain()
travel_grammar = travel_domain.grammar()

def basic_feature_function(parse):
    """Features for the rule used for the root node and its children"""
    features = defaultdict(float)
    features[str(parse.rule)] += 1.0
    for child in parse.children:
        features[str(child.rule)] += 1.0
    return features
        
# This code evaluates the current grammar:    
train_test(
    model=Model(grammar=travel_grammar, feature_fn=basic_feature_function), 
    train_examples=travel_train_examples, 
    test_examples=travel_test_examples, 
    print_examples=False)


# ### Question 4
# 
# With the default travel grammar, many of the errors on training
# examples occur because the origin isn't marked by "from". You might
# have noticed that "directions New York to Philadelphia" is not
# handled properly in our opening example. Other examples include
# "transatlantic cruise southampton to tampa", "fly boston to myrtle
# beach spirit airlines", and "distance usa to peru". __Your tasks__:
# (i) extend the grammar with a single rule to handle examples like
# these, and run another evaluation using this expanded grammar
# (submit your completion of the following starter code); (ii) in
# 1&ndash;2 sentences, summarize what happened to the post-training
# performance metrics when this rule was added.

# In[ ]:

from travel import TravelDomain
from parsing import Rule, add_rule
from scoring import Model
from experiment import train_test
from travel_examples import travel_train_examples, travel_test_examples

travel_domain = TravelDomain()
travel_grammar = travel_domain.grammar()

# Add your rule here:

# This code evaluates the new grammar:
train_test(
    model=Model(grammar=travel_grammar, feature_fn=basic_feature_function), 
    train_examples=travel_train_examples, 
    test_examples=travel_test_examples, 
    print_examples=False)


# ### Question 5
# 
# Your extended grammar for question 4 likely did some harm to the
# space of parses we consider. Consider how `number of parses` has
# changed. (If it's not intuitively clear why, check out some of the
# parses to see what's happening!)
# 
# __Your task__: to try to make amends, expand the feature function to
# improve the ability of the optimizer to distinguish good parses from
# bad. You can write your own function and/or combine it with scoring
# functions that are available inside SippyCup. You should be able to
# achieve a gain in post-training train and test `semantics accuracy`.
# (Note: you should _not_ spend hours continualy improving your score
# unless you are planning to develop this into a project. Any gain over
# the previous run will suffice here.) __Submit__: your completion of
# this code.

# In[ ]:

from parsing import Parse

def expanded_feature_function(parse):  
    pass

# Evaluate the new grammar:
train_test(
    model=Model(grammar=travel_grammar, feature_fn=expanded_feature_function), 
    train_examples=travel_train_examples, 
    test_examples=travel_test_examples, 
    print_examples=False)


# ## GeoQuery domain

# Here are a few simple examples from the GeoryQuery domain:

# In[ ]:

from geoquery import GeoQueryDomain

geo_domain = GeoQueryDomain()
geo_grammar = geo_domain.grammar()

display_examples(
    ("what is the biggest city in california ?",
     "how many people live in new york ?",
     "where is rochester ?"),
    grammar=geo_grammar,
    domain=geo_domain)


# And we can train models just as we did for the travel domain, though
# we have to be more attentive to special features of semantic parsing
# in this domain. Here's a run with the default scoring model,
# metrics, etc.:

# In[ ]:

from geoquery import GeoQueryDomain
from scoring import Model
from experiment import train_test

geo_domain = GeoQueryDomain()
geo_grammar = geo_domain.grammar()

# We'll use this as our generic assessment interface for these questions:
def special_geo_evaluate(grammar=None, feature_fn=geo_domain.features):
    # Build the model by hand so that we can see all the pieces:
    geo_mod = Model(
        grammar=grammar, 
        feature_fn=feature_fn, 
        weights=geo_domain.weights(),
        executor=geo_domain.execute)
    # This can be done with less fuss using experiment.train_test_for_domain, 
    # but we want full access to the model, metrics, etc.
    train_test(
        model=geo_mod, 
        train_examples=geo_domain.train_examples(), 
        test_examples=geo_domain.test_examples(), 
        metrics=geo_domain.metrics(),
        training_metric=geo_domain.training_metric(),    
        seed=0,
        print_examples=False)
    
special_geo_evaluate(grammar=geo_grammar)


# ### Question 6
# 
# Two deficiencies of the current grammar:
# 
# * The words "where" and "is" are treated as being of category
# `$Optional`, which means they are ignored. As a result, the grammar
# construes all questions of the form "where is X" as being about the
# identity of X!
# 
# * Queries like "how many people live in Florida" are not handled
# correctly.
# 
# __Your task__: Add grammar rules that address these problems and
# assess impact of the changes using the `train_test` based interface
# illustrated above. __Submit__: your expanded version of the starter
# code below.

# In[ ]:

from geoquery import GeoQueryDomain
from parsing import Rule, add_rule

geo_domain = GeoQueryDomain()
geo_grammar = geo_domain.grammar()

# Your rules go here:

# Evaluation of the new grammar:
special_geo_evaluate(grammar=geo_grammar)


# ### Question 7
# 
# The success of the `empty_denotation` feature demonstrates the
# potential of denotation features. Can we go further? Experiment with
# a feature or features that characterize the _size_ of the denotation
# (that is, the number of answers). This will involve extending
# `geo_domain.features` and running another assessment. __Submit__:
# your completion of the code below and 1&ndash;2 sentences saying how
# this feature seems to behave in the model.

# In[ ]:

from geoquery import GeoQueryDomain

def feature_function(parse):
    # Bring in all the default features:
    f = geo_domain.features(parse)
    # Extend dictionary f with your new denotation-count feature
    
    return f

# Evaluation of the new grammar:
special_geo_evaluate(grammar=geo_grammar, feature_fn=feature_function)

