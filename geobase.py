from __future__ import print_function

"""
Defines GeobaseReader, which reads geobase (a geography database from Ray
Mooney's group at UT Austin) from a Prolog file and parses it into a set of
triples, each consisting of:

  - the relation name, one of 17 described below
  - the source (or subject), an entity id such as '/state/nevada'
  - the destination (or object), an entity id or a numeric value

An entity id resembles a Unix pathname.  The first segment indicates the
entity's type, while the rest is an identifier based on the entity's ordinary
name.  There are eight types, or unary relations, listed here by number of
instances:

     386  city
     102  place
      51  state
      50  mountain
      46  river
      40  road
      22  lake
       1  country

     698  TOTAL

Note that 'place' is the type used for places identified by geobase as the
highest or lowest point in a state.  Highest points are typically mountains;
lowest points are often rivers or lakes. Consequently, entity ids may not be
unique identifiers of entities.  For example, we have both '/mountain/mckinley'
and '/place/mount_mckinley', and '/lake/erie' and '/place/lake_erie'.

There are 14 ordinary binary relations, which contain the primary geographical
content of geobase.

    742  contains                # state to city or mountain, or country to state
                                     '/state/alaska' => '/city/anchorage_ak'
    438  population              # city, state, or country to integer
                                     '/state/nevada' => 800500
    436  borders                 # state to state, with symmetry
                                     '/state/nevada' <=> '/state/utah'
    367  traverses               # river, road, or lake to state
                                     '/road/15' => '/state/nevada'
    152  height                  # mountain to height in meters,
                                   or high-low place to elevation in meters
     74  area                    # state, country, or lake to area in square meters
                                     '/state/nevada' => 286193686192.128
     51  abbreviation            # state to two-letter abbrevation
                                     '/state/nevada' => 'nv'
     51  capital                 # state to capital city
                                     '/state/oregon' => '/city/salem_or'
     51  highest_elevation       # state to highest elevation in meters
                                     '/state/illinois' => 376
     51  highest_point           # state to place
                                     '/state/illinois' => '/place/charles_mound'
     51  lowest_elevation        # state to lowest elevation in meters
                                     '/state/illinois' => 85
     51  lowest_point            # state to place
                                     '/state/illinois' => '/place/mississippi_river'
     51  state_number            # state to integer
                                     '/state/nevada' => 36
     46  length                  # river to length in meters
                                     '/river/snake' => 1670000

Note that the source file geobase.pl is not consistent about units, but here we
convert everything to SI (metric) units.

There is also one special binary relation, which records the mapping between
names and ids.

    698  name                    # from entity id to ordinary name: '/city/reno_nv' => 'reno'

The Prolog file defining geobase can be obtained from
ftp://ftp.cs.utexas.edu/pub/mooney/nl-ilp-data/geosystem/geobase
Here we assume it can be read from the local directory as geobase.pl.
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
from six.moves import urllib

valid_line = re.compile(r'^[a-z]+\((.*)\)\.$')

def filter_by_prefix(prefix, lines):
  return [line for line in lines if line.startswith(prefix)]

def strip_brackets(string):
  if string.startswith('['):
    string = string[1:]
  if string.endswith(']'):
    string = string[:-1]
  return string

def strip_quotes(string):
  if string.startswith("'") and string.endswith("'"):
    return string[1:-1]
  else:
    return string

def extract_fields(line):
  fields = valid_line.match(line).group(1).split(',')
  fields = [strip_quotes(strip_brackets(field.strip())) for field in fields]
  fields = [field for field in fields if field != '']
  return fields

def make_state_id(state_name):
  return "/state/%s" % state_name.replace(" ", "_")

def make_city_id(city_name, state_abbrev):
  return "/city/%s_%s" % (city_name.replace(" ", "_"), state_abbrev)

def make_river_id(river_name):
  return "/river/%s" % river_name.replace(" ", "_")

def make_place_id(place_name):
  return "/place/%s" % place_name.replace(" ", "_")

def make_mountain_id(mountain_name):
  return "/mountain/%s" % mountain_name.replace(" ", "_")

def make_road_id(road_name):
  return "/road/%s" % road_name.replace(" ", "_")

def make_lake_id(lake_name):
  return "/lake/%s" % lake_name.replace(" ", "_")

def make_country_id(country_name):
  return "/country/%s" % country_name.replace(" ", "_")


class GeobaseReader:

  def __init__(self):
    self.tuples = set()
    self.prolog_file = '/tmp/geobase.pl'
    self.ensure_prolog_file()
    lines = self.read_lines()
    self.parse(lines)
    self.transitive_closure('contains')

  def ensure_prolog_file(self):
    try:
      f = open(self.prolog_file, 'rU')
    except IOError as e:
      print('No local cache for Geobase Prolog file', file=sys.stderr)
      self.download_prolog_file()

  def download_prolog_file(self):
    try:
      from_url = 'ftp://ftp.cs.utexas.edu/pub/mooney/nl-ilp-data/geosystem/geobase'
      print('Downloading from %s' % from_url, file=sys.stderr)
      opener = urllib.request.URLopener()
      opener.retrieve(from_url, self.prolog_file)
      print('Download successful', file=sys.stderr)
    except IOError as e:
      print('Download failed!', file=sys.stderr)
      raise e

  def read_lines(self):
    lines = []
    try:
      f = open(self.prolog_file, 'rU')
      for line in f.readlines():
        if valid_line.match(line):
          lines.append(line[:-1])
      f.close()
    except IOError as e:
      print('No local cache for Geobase Prolog file', file=sys.stderr)
      raise e
    return lines

  def parse(self, lines):
    self.parse_state(lines)
    self.parse_city(lines)
    self.parse_river(lines)
    self.parse_border(lines)
    self.parse_highlow(lines)
    self.parse_mountain(lines)
    self.parse_road(lines)
    self.parse_lake(lines)
    self.parse_country(lines)

  def parse_state(self, lines):
    lines = filter_by_prefix('state', lines)
    for line in lines:
      # state(name, abbreviation, capital, population, area, state_number, city1, city2, city3, city4)
      fields = extract_fields(line)
      state_name = fields[0]
      state_abbrev = fields[1]
      state_id = make_state_id(state_name)
      capital_id = make_city_id(fields[2], state_abbrev)
      population = int(float(fields[3]))
      # convert from square miles to square meters
      area = int(float(fields[4])) * 1609.344 * 1609.344
      state_number = int(fields[5])
      city1_id = make_city_id(fields[6], state_abbrev)
      city2_id = make_city_id(fields[7], state_abbrev)
      city3_id = make_city_id(fields[8], state_abbrev)
      city4_id = make_city_id(fields[9], state_abbrev)
      self.add_unary('state', state_id)
      self.add_binary('name', state_id, state_name)
      self.add_binary('abbreviation', state_id, state_abbrev)
      self.add_binary('capital', state_id, capital_id)
      self.add_binary('contains', state_id, capital_id)
      self.add_binary('population', state_id, population)
      self.add_binary('area', state_id, area)
      self.add_binary('state_number', state_id, state_number)
      self.add_binary('contains', state_id, city1_id)
      self.add_binary('contains', state_id, city2_id)
      self.add_binary('contains', state_id, city3_id)
      self.add_binary('contains', state_id, city4_id)
      self.add_binary('contains', '/country/usa', state_id)
    print('GeobaseReader read %d state rows.' % len(lines))

  def parse_city(self, lines):
    lines = filter_by_prefix('city', lines)
    for line in lines:
      # city(state, state_abbreviation, name, population)
      fields = extract_fields(line)
      state_name = fields[0]
      state_id = make_state_id(state_name)
      state_abbrev = fields[1]
      city_name = fields[2]
      city_id = make_city_id(city_name, state_abbrev)
      population = int(fields[3])
      self.add_unary('city', city_id)
      self.add_binary('name', city_id, city_name)
      self.add_binary('contains', state_id, city_id)
      self.add_binary('population', city_id, population)
    print('GeobaseReader read %d city rows.' % len(lines))

  def parse_river(self, lines):
    lines = filter_by_prefix('river', lines)
    for line in lines:
      # river(name, length, [states through which it flows])
      fields = extract_fields(line)
      river_name = fields[0]
      river_id = make_river_id(river_name)
      # convert kilometers to meters
      length = int(fields[1]) * 1000
      traversed_state_names = fields[2:]
      self.add_unary('river', river_id)
      self.add_binary('name', river_id, river_name)
      self.add_binary('length', river_id, length)
      for state_name in traversed_state_names:
        self.add_binary('traverses', river_id, make_state_id(state_name))
    print('GeobaseReader read %d river rows.' % len(lines))

  def parse_border(self, lines):
    lines = filter_by_prefix('border', lines)
    for line in lines:
      # border(state, state_abbreviation, [states that border it])
      fields = extract_fields(line)
      state_name = fields[0]
      state_id = make_state_id(state_name)
      bordered_state_names = fields[2:]
      for bordered_state_name in bordered_state_names:
        bordered_state_id = make_state_id(bordered_state_name)
        self.add_binary('borders', state_id, bordered_state_id)
        self.add_binary('borders', bordered_state_id, state_id)
    print('GeobaseReader read %d border rows.' % len(lines))

  def parse_highlow(self, lines):
    lines = filter_by_prefix('highlow', lines)
    for line in lines:
      # highlow(state, state_abbreviation, highest_point, highest_elevation, lowest_point, lowest_elevation)
      fields = extract_fields(line)
      state_name = fields[0]
      state_id = make_state_id(state_name)
      highest_point_name = fields[2]
      # TODO: consider whether it should be a mountain id
      highest_point_id = make_place_id(highest_point_name)
      highest_elevation = int(fields[3])
      lowest_point_name = fields[4]
      lowest_point_id = make_place_id(lowest_point_name)
      lowest_elevation = int(fields[5])
      # TODO: consider whether the type should be mountain, not place
      self.add_unary('place', highest_point_id)
      self.add_binary('name', highest_point_id, highest_point_name)
      self.add_unary('place', lowest_point_id)
      self.add_binary('name', lowest_point_id, lowest_point_name)
      self.add_binary('highest_point', state_id, highest_point_id)
      self.add_binary('highest_elevation', state_id, highest_elevation)
      self.add_binary('height', highest_point_id, highest_elevation)
      self.add_binary('lowest_point', state_id, lowest_point_id)
      self.add_binary('lowest_elevation', state_id, lowest_elevation)
      self.add_binary('height', lowest_point_id, lowest_elevation)
    print('GeobaseReader read %d highlow rows.' % len(lines))

  def parse_mountain(self, lines):
    lines = filter_by_prefix('mountain', lines)
    for line in lines:
      # mountain(state, state_abbreviation, name, height)
      fields = extract_fields(line)
      state_name = fields[0]
      state_id = make_state_id(state_name)
      mountain_name = fields[2]
      mountain_id = make_mountain_id(mountain_name)
      height = int(fields[3])
      self.add_unary('mountain', mountain_id)
      self.add_binary('name', mountain_id, mountain_name)
      self.add_binary('contains', state_id, mountain_id)
      self.add_binary('height', mountain_id, height)
    print('GeobaseReader read %d mountain rows.' % len(lines))

  def parse_road(self, lines):
    lines = filter_by_prefix('road', lines)
    for line in lines:
      # road(number, [states it passes through])
      fields = extract_fields(line)
      road_name = fields[0]
      road_id = make_road_id(road_name)
      traversed_state_names = fields[1:]
      self.add_unary('road', road_id)
      self.add_binary('name', road_id, road_name)
      for traversed_state_name in traversed_state_names:
        self.add_binary('traverses', road_id, make_state_id(traversed_state_name))
    print('GeobaseReader read %d road rows.' % len(lines))

  def parse_lake(self, lines):
    lines = filter_by_prefix('lake', lines)
    for line in lines:
      # lake(name, area, [states it is in])
      fields = extract_fields(line)
      lake_name = fields[0]
      lake_id = make_lake_id(fields[0])
      # convert from square kilometers to square meters
      area = int(fields[1]) * 1e6
      traversed_state_names = fields[2:]
      self.add_unary('lake', lake_id)
      self.add_binary('name', lake_id, lake_name)
      self.add_binary('area', lake_id, area)
      for traversed_state_name in traversed_state_names:
        # 'traverses' may sound odd here, but, logically, it's the same relation.
        self.add_binary('traverses', lake_id, make_state_id(traversed_state_name))
    print('GeobaseReader read %d lake rows.' % len(lines))

  def parse_country(self, lines):
    lines = filter_by_prefix('country', lines)
    for line in lines:
      # country(name, population, area)
      fields = extract_fields(line)
      country_name = fields[0]
      country_id = make_country_id(country_name)
      population = int(fields[1])
      # convert from square kilometers to square meters
      area = int(fields[2]) * 1e6
      self.add_unary('country', country_id)
      self.add_binary('name', country_id, country_name)
      self.add_binary('population', country_id, population)
      self.add_binary('area', country_id, area)
    print('GeobaseReader read %d country row.' % len(lines))

  def add_unary(self, rel, elt):
    self.tuples.add((rel, elt))
    # print 'add_unary(%s, %s)' % (rel, elt)

  def add_binary(self, rel, src, dst):
    self.tuples.add((rel, src, dst))
    # print 'add_binary(%s, %s, %s)' % (rel, src, dst)

  def transitive_closure(self, rel):
    edges = [edge for edge in self.tuples if edge[0] == rel]
    for edge_1 in edges:
      for edge_2 in edges:
        if edge_1[2] == edge_2[1]:
          edges.append((rel, edge_1[1], edge_2[2]))
    before_size = len(self.tuples)
    for edge in edges:
      self.tuples.add(edge)
    print('GeobaseReader computed transitive closure of \'%s\', adding %d edges' % (
      rel, len(self.tuples) - before_size))


if __name__ == '__main__':
  geobase = GeobaseReader()
