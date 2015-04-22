"""
An Annotator which wraps the GeoNames API (geonames.org) to recognize names
of locations and generate semantic representations for them.  For example,
the phrase "boston" will be annotated with the semantic representation
{'id': 4930956, 'name': 'Boston, MA, US'}.

GeoNames defines a geographic database in which each location is identified
by a unique integer, and provides a free, RESTful API for geocoding requests.
See API documentation at http://www.geonames.org/export/web-services.html.
See also the example request and response shown below.

You will soon observe that the annotations are far from perfect.  For example,
"florida" is annotated as {'id': 3442584, 'name': 'Florida, UY'}, which denotes
a city in Uruguay.  The current implementation could be improved in many ways.
For example, while the GeoNames API can return multiple results for ambiguous
queries such as "florida", the GeoNamesAnnotator considers only the first result
-- and there is no guarantee that the first result is the best. It may also be
possible to improve the quality of the results by playing with some of the API
request parameters, such as 'featureClass', 'countryBias', or 'orderby'.

Note that the GeoNamesAnnotator uses a persistent cache which is pre-populated
for phrases in the 100 annotated examples for the travel domain.  If you run
only on those examples, you will not need to make live calls to the GeoNames
API, but if you run on any other examples, you will be making live calls.

By default, requests to the GeoNames API are made with username 'wcmac'.
However, each (free) GeoNames account is limited to 2000 calls per hour.
If too many people are making calls as 'wcmac', that quota could be exhausted
quickly.  If that happens, you'll want to create your own account at
http://www.geonames.org/login.

Example request:

  http://api.geonames.org/searchJSON?q=Solomon+Guggenheim+Museum+NY&username=wcmac

Example response:

  {'totalResultsCount': 1,
   'geonames': [
       {'fcode': 'MUS',
        'countryId': '6252001',
        'name': 'Solomon R Guggenheim Museum',
        'countryCode': 'US',
        'geonameId': 5119572,
        'toponymName': 'Solomon R Guggenheim Museum',
        'fclName': 'spot, building, farm',
        'fcodeName': 'museum',
        'countryName': 'United States',
        'lat': '40.78288',
        'lng': '-73.95903',
        'population': 0,
        'fcl': 'S',
        'adminCode1': 'NY',
        'adminName1': 'New York'}]}
"""

__author__ = "Bill MacCartney"
__copyright__ = "Copyright 2015, Bill MacCartney"
__credits__ = []
__license__ = "GNU General Public License, version 2.0"
__version__ = "0.9"
__maintainer__ = "Bill MacCartney"
__email__ = "See the author's website"

import urllib2
import json
import sys

from annotator import Annotator


class GeoNamesAnnotator(Annotator):
    def __init__(self, max_tokens=4, live_requests=True, refresh_cache=False):
        self.max_tokens = max_tokens
        self.live_requests = live_requests
        self.cache = {}
        if refresh_cache:
            for k, v in self.persistent_cache.items():
                if v == None:
                    self.cache[k] = v
            print 'Kept %d of %d cache entries' % (len(self.cache), len(self.persistent_cache))
        else:
            self.cache = self.persistent_cache
        self.cache_updated = False
        print 'Loaded GeoNamesAnnotator cache with %d items' % len(self.cache)

    def __del__(self):
        self.print_cache_if_updated()

    # Words which could be part of a valid location name should not appear in this list.
    # For example, 'in' doesn't appear, because it could mean Indiana: 'south bend in'.
    stopwords = set([
        'a', 'and', 'at', 'by', 'do', 'for', 'from', 'get',
        'is', 'it', 'of', 'to', 'what', 'with'
    ])

    def annotate(self, tokens):
        if len(tokens) > self.max_tokens:
            return []
        if any([token in self.stopwords for token in tokens]):
            return []
        text = ' '.join(tokens)
        if text in self.cache:
            semantics = self.cache[text]
            if semantics != None:
                return [('$Location', semantics)]
            else:
                return []
        elif self.live_requests:
            try:
                semantics = self.geocode(text)
                self.cache[text] = semantics
                self.cache_updated = True
                print 'geocoded "%s" as %s' % (text, str(semantics))
                if semantics != None:
                    return [('$Location', semantics)]
                else:
                    return []
            except KeyError, e:
                self.print_cache_if_updated()
                raise e
        else:
            print >>sys.stderr, \
                'To make live geocoding requests, use GeoNamesAnnotator(live_requests=True).'
            return []

    def geocode(self, text):
        try:
            request_url = self.build_request_url(text)
            response = json.load(urllib2.urlopen(request_url))
            if 'status' in response:
                print 'GeoNames server returned status:'
                print response['status']
            if len(response['geonames']):
                return self.build_semantics(response['geonames'][0])
            else:
                return None
        except urllib2.URLError, e:
            print e
            print >>sys.stderr, \
                'To run with cache only, use GeoNamesAnnotator(live_requests=False).'
            sys.exit()

    def build_request_url(self, text):
        encoded_text = text.replace(' ', '+')  # TODO: make smarter
        request_params = [
            ('q', encoded_text),
            ('username', 'wcmac'),
            ('maxRows', 3),
            # ('countryBias', 'US'),
        ]
        params_string = '&'.join(['%s=%s' % pair for pair in request_params])
        base_url = 'http://api.geonames.org/searchJSON'
        return '%s?%s' % (base_url, params_string)

    def build_semantics(self, result):
        id = result['geonameId']
        full_name = self.build_full_name(result)
        return {'id': id, 'name': full_name}

    def build_full_name(self, result):
        try:
            full_name_parts = []
            # Start with the ordinary name.
            full_name_parts.append(result['name'])
            # Add the state code for locations in the US, unless it's a state.
            if 'countryCode' in result and result['countryCode'] == 'US':
                if result['name'] != result['adminName1']:
                    if 'adminCode1' in result and result['adminCode1'] != '00':
                        full_name_parts.append(result['adminCode1'])
            # Add the country code, unless it's a country.
            if 'countryCode' in result and str(result['geonameId']) != result['countryId']:
                full_name_parts.append(result['countryCode'])
            return ', '.join(full_name_parts).encode('ascii', 'ignore')
        except KeyError, e:
            print result
            print e
            raise e

    def print_cache_if_updated(self):
        if self.cache_updated:
            print 'GeoNamesAnnotator cache updated (%d entries)' % len(self.cache)
            # print '    persistent_cache = {'
            # for key in sorted(self.cache.keys()):
            #     escaped_key = key.replace("'", "\\'")
            #     print '        \'%s\': %s,' % (escaped_key, str(self.cache[key]))
            # print '    }'
        else:
            print 'GeoNamesAnnotator cache not updated'

    # We have cached interpretations for phrases appearing in the 100 annotated
    # examples for the travel domain.  This avoids the need to make live calls
    # to the GeoNames API.
    persistent_cache = {
        '-detroit': {'id': 4990729, 'name': 'Detroit, MI, US'},
        '000': {'id': 3446370, 'name': 'Toledo, BR'},
        '06': {'id': 2996944, 'name': 'Lyon, FR'},
        '1': {'id': 3037854, 'name': 'Amiens, FR'},
        '10': {'id': 3575733, 'name': 'Mahaut, DM'},
        '10 manhattan': {'id': 7115461, 'name': 'Manhattan Bangkok, TH'},
        '10 manhattan square': None,
        '10 manhattan square drive': None,
        '14607': {'id': 5134086, 'name': 'Rochester, NY, US'},
        '1500': {'id': 2796696, 'name': 'Halle, BE'},
        '1500 miles': None,
        '1500 miles away': None,
        '2000': {'id': 2803138, 'name': 'Antwerp, BE'},
        '2006': {'id': 3645220, 'name': 'Municipio Crdoba, VE'},
        '2006 airfare': None,
        '2006 time': None,
        '2006 time line': None,
        '26': {'id': 161325, 'name': 'Arusha, TZ'},
        '26 06': {'id': 2488835, 'name': 'Mda, DZ'},
        '3': {'id': 2990969, 'name': 'Nantes, FR'},
        '3 26': {'id': 1467205, 'name': 'Jurm, AF'},
        '3 26 06': None,
        '5': {'id': 2992166, 'name': 'Montpellier, FR'},
        '5 2006': None,
        '500': {'id': 400745, 'name': 'North Eastern Province, KE'},
        '500 000': None,
        'accident': {'id': 4099058, 'name': 'Accident, AR, US'},
        'accident report': None,
        'address': {'id': 6949505, 'name': 'The Address Downtown Burj Dubai, AE'},
        'age': {'id': 2696519, 'name': 'Lersj Age, SE'},
        'age pension': None,
        'agency': {'id': 1171388, 'name': 'Malakand, PK'},
        'air': {'id': 934750, 'name': 'Bel Air Rivire Sche, MU'},
        'air fare': None,
        'air fares': None,
        'airbus': {'id': 6288571, 'name': 'Airbus UK FC, GB'},
        'airfare': {'id': 9960013, 'name': 'Airfare Sahara, ES'},
        'airfares': None,
        'airline': {'id': 5882812, 'name': 'Airline Lake, CA'},
        'airline flight': None,
        'airline schedule': None,
        'airline schedule 3': None,
        'airline schedule 3 26': None,
        'airline tickers': None,
        'airlines': {'id': 6344140, 'name': 'American Airlines Arena, FL, US'},
        'airport': {'id': 6299704, 'name': 'Caransebe Airport, RO'},
        'airports': {'id': 6299946, 'name': 'Nausori International Airport, FJ'},
        'airports in': None,
        'airports in florida': None,
        'al': {'id': 285839, 'name': 'Al Ahmadi, KW'},
        'al distance': None,
        'al.': {'id': 285839, 'name': 'Al Ahmadi, KW'},
        'alabama': {'id': 4829764, 'name': 'Alabama, US'},
        'alaska': {'id': 5879092, 'name': 'Alaska, US'},
        'alaska combined': None,
        'all': {'id': 3576397, 'name': 'All Saints, AG'},
        'all airlines': None,
        'amtrak': {'id': 6946340, 'name': 'Miami Amtrak, FL, US'},
        'angeles': {'id': 5368361, 'name': 'Los Angeles, CA, US'},
        'another': {'id': 5885517, 'name': 'Another Lake, CA'},
        'another in': None,
        'another in mobile': None,
        'another in mobile al.': None,
        'apply': {'id': 4984322, 'name': 'Apply Drain, MI, US'},
        'april': {'id': 8298703, 'name': 'April River Airport, PG'},
        'april 1': None,
        'april 5': None,
        'april 5 2006': None,
        'area': {'id': 6295630, 'name': 'Earth'},
        'atlanta': {'id': 4180439, 'name': 'Atlanta, GA, US'},
        'atlanta ga.': {'id': 4180439, 'name': 'Atlanta, GA, US'},
        'atlanta ga. airline': None,
        'atlanta ga. airline schedule': None,
        'atlantic': {'id': 3358844, 'name': 'South Atlantic Ocean'},
        'atlantic city.': {'id': 4500546, 'name': 'Atlantic City, NJ, US'},
        'atlantic city. new': {'id': 4500546, 'name': 'Atlantic City, NJ, US'},
        'atlantic city. new jersey': {'id': 4500546, 'name': 'Atlantic City, NJ, US'},
        'augustine': {'id': 4726259, 'name': 'San Augustine County, TX, US'},
        'austin': {'id': 4671654, 'name': 'Austin, TX, US'},
        'austin texas': {'id': 4671654, 'name': 'Austin, TX, US'},
        'auto': {'id': 5880844, 'name': 'Auto, AS'},
        'away': {'id': 98378, 'name': 'w Karm, IQ'},
        'bahamas': {'id': 3572887, 'name': 'Bahamas'},
        'bakersfield': {'id': 5325738, 'name': 'Bakersfield, CA, US'},
        'bakersfield ca': {'id': 5325738, 'name': 'Bakersfield, CA, US'},
        'ballet': {'id': 5999376, 'name': 'Lac Ballet, CA'},
        'balloons': None,
        'beach': {'id': 4177887, 'name': 'West Palm Beach, FL, US'},
        'beach spirit': {'id': 4159027, 'name': 'Holy Spirit Catholic Church, FL, US'},
        'beach spirit airlines': None,
        'bend': {'id': 935113, 'name': 'Big Bend, SZ'},
        'bend in': {'id': 4926563, 'name': 'South Bend, IN, US'},
        'berlin': {'id': 2950159, 'name': 'Berlin, DE'},
        'berlin germany': {'id': 2950159, 'name': 'Berlin, DE'},
        'best': {'id': 2759040, 'name': 'Best, NL'},
        'best time': {'id': 9885471, 'name': 'Best Western Time Hotel, SE'},
        'bike': {'id': 2110244, 'name': 'Bike, KI'},
        'bike ride': None,
        'bike riding-seattle': None,
        'birmingham': {'id': 2655603, 'name': 'Birmingham, GB'},
        'birmingham al': {'id': 4049979, 'name': 'Birmingham, AL, US'},
        'birmingham al distance': None,
        'blue': {'id': 3491315, 'name': 'Blue Mountain Peak, JM'},
        'blue flights': None,
        'boats': {'id': 2572137, 'name': 'Two Boats Village, SH'},
        'book': {'id': 6001344, 'name': 'Lac Book, CA'},
        'borrows': {'id': 2076016, 'name': 'Borrows Hill, AU'},
        'borrows 500': None,
        'borrows 500 000': None,
        'boston': {'id': 4930956, 'name': 'Boston, MA, US'},
        'buffalo': {'id': 1019330, 'name': 'Bhisho, ZA'},
        'buffalo ny': {'id': 5110629, 'name': 'Buffalo, NY, US'},
        'bus': {'id': 615532, 'name': 'Batumi, GE'},
        'bus service': None,
        'bus service -detroit': None,
        'bus tours': None,
        'buses': {'id': 6011327, 'name': 'Lac des Buses, CA'},
        'ca': {'id': 7729890, 'name': 'Northern America, US'},
        'ca.': {'id': 7729890, 'name': 'Northern America, US'},
        'california': {'id': 4017700, 'name': 'Estado de Baja California, MX'},
        'california coach': {'id': 5338165, 'name': 'Coach Royal Trailer Park, CA, US'},
        'california coach tours': None,
        'california fromn': None,
        'california fromn dc': None,
        'california fromn dc area': None,
        'canada': {'id': 6251999, 'name': 'Canada'},
        'car': {'id': 239880, 'name': 'Central African Republic'},
        'car in': {'id': 1274969, 'name': 'Car Nicobar Island, IN'},
        'car in pennsylvania': None,
        'car service': {'id': 2383129, 'name': 'Service, CF'},
        'carolina': {'id': 4563243, 'name': 'Carolina, PR'},
        'casino': {'id': 2172153, 'name': 'Casino, AU'},
        'casino hammond': None,
        'casino hammond in': None,
        'cedar': {'id': 3576338, 'name': 'Cedar Grove, AG'},
        'cedar rapids': {'id': 4850751, 'name': 'Cedar Rapids, IA, US'},
        'cedar rapids ia': {'id': 4850751, 'name': 'Cedar Rapids, IA, US'},
        'cellular': {'id': 4914249, 'name': 'U S Cellular Field, IL, US'},
        'cellular phone': {'id': 6327265, 'name': 'Lebanon Cellular Phone Tower, FL, US'},
        'charlotte': {'id': 4795467, 'name': 'Charlotte Amalie, VI'},
        'chattanooga': {'id': 4612862, 'name': 'Chattanooga, TN, US'},
        'cheap': {'id': 5915569, 'name': 'Cape Breton Island, CA'},
        'cheap air': None,
        'cheap air fares': None,
        'cheap airfare': None,
        'cheap flight': None,
        'cheap flights': None,
        'cheap tickets': None,
        'cheapest': None,
        'cheapest airline': None,
        'cheapest airline flight': None,
        'cheapest place': None,
        'chicago': {'id': 4887398, 'name': 'Chicago, IL, US'},
        'chile': {'id': 3895114, 'name': 'Chile'},
        'citizen': {'id': 7098763, 'name': 'Citizen Colony, PK'},
        'citizen texas': {'id': 7159092, 'name': 'Orange Police Department - Citizen Service, TX, US'},
        'citizen texas driving': None,
        'city': {'id': 3582677, 'name': 'Belize City, BZ'},
        'city ballet': {'id': 4347782, 'name': 'Baltimore Ballet Center, MD, US'},
        'city.': {'id': 3582677, 'name': 'Belize City, BZ'},
        'city. new': {'id': 5128581, 'name': 'New York, US'},
        'city. new jersey': {'id': 5099836, 'name': 'Jersey City, NJ, US'},
        'close': {'id': 6631280, 'name': 'Close Islands, AQ'},
        'clt': {'id': 3467314, 'name': 'Capela do Alto, BR'},
        'coach': {'id': 3373973, 'name': 'Coach Hill, BB'},
        'coach tours': None,
        'combined': {'id': 5249224, 'name': 'Combined Locks, WI, US'},
        'conduct': None,
        'conduct ticket': None,
        'conduct ticket in': None,
        'conduct ticket in fairborn': None,
        'cost': {'id': 4046252, 'name': 'Cost, TX, US'},
        'cruise': {'id': 6631678, 'name': 'Cruise Nunatak, AQ'},
        'cruise southampton': {'id': 9253608, 'name': 'Southampton Cruise Port, GB'},
        'cruises': {'id': 6351117, 'name': 'Cruises Creek Baptist Church Cemetery, KY, US'},
        'cruises departing': None,
        'cruises lines': None,
        'csaa': None,
        'csaa discount': None,
        'csaa discount ticket': None,
        'ct.': {'id': 3128760, 'name': 'Barcelona, ES'},
        'cunmming': None,
        'cunmming georgia': None,
        'dallas': {'id': 4684888, 'name': 'Dallas, TX, US'},
        'dallas tx': {'id': 4684888, 'name': 'Dallas, TX, US'},
        'day': {'id': 1428970, 'name': 'Dy-e Argisht, AF'},
        'day cruise': None,
        'dc': {'id': 4140963, 'name': 'Washington, DC, US'},
        'dc area': {'id': 4141010, 'name': 'Washington Metropolitan Area Transit Authority Headquarters, DC, US'},
        'delta': {'id': 2565341, 'name': 'Delta, NG'},
        'delta flights': None,
        'denali': {'id': 5859404, 'name': 'Churchill Peaks, AK, US'},
        'departing': None,
        'detroit': {'id': 4990729, 'name': 'Detroit, MI, US'},
        'detroit michigan': {'id': 4990729, 'name': 'Detroit, MI, US'},
        'different': {'id': 4463656, 'name': 'Different Drum Dam, NC, US'},
        'different airports': None,
        'different airports in': None,
        'different airports in florida': None,
        'direct': {'id': 5939560, 'name': 'Direct Lake, CA'},
        'direct flights': None,
        'direction': {'id': 1547375, 'name': 'Direction Island, CC'},
        'directions': {'id': 7241910, 'name': 'New Directions Alternative School, GA, US'},
        'directions one': None,
        'directions one address': None,
        'discount': {'id': 8621273, 'name': 'Bank Barclays Discount, IL'},
        'discount ticket': None,
        'discount tickets': None,
        'discount travel': None,
        'discount travel flights': None,
        'disorderly': None,
        'disorderly conduct': None,
        'disorderly conduct ticket': None,
        'disorderly conduct ticket in': None,
        'distance': {'id': 3709781, 'name': 'Empire Known Distance Range, PA'},
        'distance cunmming': None,
        'distance cunmming georgia': None,
        'distance usa': {'id': 3709781, 'name': 'Empire Known Distance Range, PA'},
        'distance washington': None,
        'distance washington dc': None,
        'drive': {'id': 5942705, 'name': 'Drive Lake, CA'},
        'drive in': {'id': 8477646, 'name': 'Drive-in, KE'},
        'drive in florida': {'id': 4152918, 'name': 'Daytona Beach Drive-In Christian Church, FL, US'},
        'drive in florida using': None,
        'drive rochester': {'id': 7278841, 'name': 'Rochester Drive-In (historical), NY, US'},
        'drive rochester ny': {'id': 7278841, 'name': 'Rochester Drive-In (historical), NY, US'},
        'drive rochester ny 14607': None,
        'drivers': {'id': 2072555, 'name': 'Drivers Hill, AU'},
        'drivers license': None,
        'drivers license away': None,
        'driving': {'id': 5942712, 'name': 'Driving Lake, CA'},
        'driving distance': None,
        'driving distance washington': None,
        'driving distance washington dc': None,
        'duluth': {'id': 5024719, 'name': 'Duluth, MN, US'},
        'duluth mn': {'id': 5024719, 'name': 'Duluth, MN, US'},
        'durham': {'id': 2650628, 'name': 'Durham, GB'},
        'europe': {'id': 7729884, 'name': 'Eastern Europe, RU'},
        'fairborn': {'id': 4511263, 'name': 'Fairborn, OH, US'},
        'fairborn ohio': {'id': 4511263, 'name': 'Fairborn, OH, US'},
        'falls': {'id': 6087892, 'name': 'Niagara Falls, CA'},
        'fare': {'id': 7730131, 'name': 'Huahine  Fare Airport, PF'},
        'fares': {'id': 2508099, 'name': 'Ain Fares, DZ'},
        'farmer': {'id': 6632964, 'name': 'Farmer Island, AQ'},
        'fight': {'id': 5952672, 'name': 'Fight Lake, CA'},
        'finance': {'id': 8556343, 'name': 'Ministry of Finance, EG'},
        'finance war': None,
        'fl': {'id': 2759879, 'name': 'Almere, NL'},
        'fl amtrak': {'id': 6946340, 'name': 'Miami Amtrak, FL, US'},
        'fla': {'id': 6453361, 'name': 'Fl, NO'},
        'flight': {'id': 6639250, 'name': 'Flight Deck Nv, AQ'},
        'flights': {'id': 8193558, 'name': 'Little Flights Bay, AU'},
        'flights newark': None,
        'florida': {'id': 3442584, 'name': 'Florida, UY'},
        'florida name': {'id': 4166036, 'name': 'No Name Key, FL, US'},
        'florida name your': None,
        'florida name your own': None,
        'florida using': None,
        'flowers': {'id': 6633253, 'name': 'Flowers Hills, AQ'},
        'fly': {'id': 8657194, 'name': 'Middle Fly, PG'},
        'fly boston': None,
        'fort': {'id': 3570675, 'name': 'Fort-de-France, MQ'},
        'fort lauderdale': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'fort lauderdale florida': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'fr.': {'id': 9408659, 'name': 'Western Europe, DE'},
        'fr. myers': None,
        'fr. myers fla': None,
        'francisco': {'id': 3621911, 'name': 'San Francisco, CR'},
        'fromn': None,
        'fromn dc': None,
        'fromn dc area': None,
        'ft': {'id': 6298316, 'name': 'Fort Hood, Robert Gray AAF Ft Hood, TX, US'},
        'ft lauderdale': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'ft.': {'id': 6298316, 'name': 'Fort Hood, Robert Gray AAF Ft Hood, TX, US'},
        'ft. lauderdale': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'ft.lauderdale': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'ft.lauderdale florida': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'fun': {'id': 2110394, 'name': 'Funafuti, TV'},
        'fun on': {'id': 4257826, 'name': 'Fun Creek, IN, US'},
        'fun on i10': None,
        'fun on i10 alabama': None,
        'ga.': {'id': 7729886, 'name': 'Central Africa, CD'},
        'ga. airline': {'id': 4179263, 'name': 'Airline Baptist Church, GA, US'},
        'ga. airline schedule': None,
        'ga. airline schedule 3': None,
        'games': {'id': 9017448, 'name': 'Chino Games, MX'},
        'gas': {'id': 197745, 'name': 'Garissa, KE'},
        'george': {'id': 3580661, 'name': 'George Town, KY'},
        'george washington': {'id': 5546220, 'name': 'Saint George, UT, US'},
        'george washington borrows': None,
        'george washington borrows 500': None,
        'georgia': {'id': 614540, 'name': 'Georgia'},
        'germany': {'id': 2921044, 'name': 'Germany'},
        'hammond': {'id': 4921100, 'name': 'Hammond, IN, US'},
        'hammond in': {'id': 4921100, 'name': 'Hammond, IN, US'},
        'hampshire': {'id': 5089178, 'name': 'Manchester, NH, US'},
        'hartford': {'id': 4835797, 'name': 'Hartford, CT, US'},
        'hartford ct.': {'id': 4835797, 'name': 'Hartford, CT, US'},
        'hawaii': {'id': 5855797, 'name': 'Hawaii, US'},
        'honeymoon': {'id': 5976546, 'name': 'Honeymoon Lake, CA'},
        'honeymoon trip': None,
        'honolulu': {'id': 5856195, 'name': 'Honolulu, HI, US'},
        'honolulu hawaii': {'id': 5856195, 'name': 'Honolulu, HI, US'},
        'horse': {'id': 6635155, 'name': 'Horse Bluff, AQ'},
        'horse shoe': {'id': 6024600, 'name': 'Lac Horse Shoe, CA'},
        'horse shoe casino': None,
        'horse shoe casino hammond': None,
        'hotels': {'id': 6500584, 'name': 'Hotel ICON, a member of Preferred Hotels, TX, US'},
        'hotels close': None,
        'how': {'id': 8211807, 'name': 'Lake How, AU'},
        'i': {'id': 1114993, 'name': 'Gasherbrum I, PK'},
        'i10': {'id': 6478153, 'name': 'Hampton Inn Houston I10 E, TX, US'},
        'i10 alabama': None,
        'ia': {'id': 1904975, 'name': 'Ia Grai District, VN'},
        'in': {'id': 7729895, 'name': 'Southern Asia, IN'},
        'in fairborn': None,
        'in fairborn ohio': None,
        'in florida': {'id': 4159315, 'name': 'Howie In The Hills, FL, US'},
        'in florida using': None,
        'in lexington': {'id': 4260324, 'name': 'Lexington, IN, US'},
        'in mobile': {'id': 8096937, 'name': "Spall's Mobile Home Village, IN, US"},
        'in mobile al.': {'id': 7313134, 'name': 'Victory in Praise Ministry, AL, US'},
        'in pennsylvania': {'id': 7148877, 'name': 'University of the Sciences in Philadelphia, PA, US'},
        'in vallejo': None,
        'indianapolish': None,
        'indianapolish in': None,
        'israel': {'id': 294640, 'name': 'Israel'},
        'ithaca': {'id': 261707, 'name': 'Ithaca, GR'},
        'jacksonville': {'id': 4160021, 'name': 'Jacksonville, FL, US'},
        'jacksonville fl': {'id': 4160021, 'name': 'Jacksonville, FL, US'},
        'jacksonville nc': {'id': 6298748, 'name': 'Jacksonville, New River, Marine Corps Air Station, NC, US'},
        'jersey': {'id': 3042142, 'name': 'Jersey'},
        'jet': {'id': 6025896, 'name': 'Lac Jet, CA'},
        'jet blue': {'id': 4296218, 'name': 'Jeffersontown, KY, US'},
        'jet blue flights': None,
        'jfk': {'id': 5122732, 'name': 'John F. Kennedy International Airport, NY, US'},
        'jfk ny': {'id': 5122732, 'name': 'John F. Kennedy International Airport, NY, US'},
        'juan': {'id': 4568127, 'name': 'San Juan, PR'},
        'juan puerto': {'id': 3629672, 'name': 'Puerto Cruz, VE'},
        'juan puerto rico': {'id': 4568127, 'name': 'San Juan, PR'},
        'kemerovo': {'id': 1503901, 'name': 'Kemerovo, RU'},
        'kentucky': {'id': 6254925, 'name': 'Kentucky, US'},
        'land': {'id': 3137678, 'name': 'Sndre Land, NO'},
        'land tours': None,
        'las': {'id': 3550598, 'name': 'Las Tunas, CU'},
        'las vegas': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'las vegas nevada': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'las vegas nv': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'last': {'id': 6636708, 'name': 'Last Hill, AQ'},
        'last minute': {'id': 5301600, 'name': 'Last Minute Well, AZ, US'},
        'last minute flights': None,
        'lauderdale': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'lauderdale florida': {'id': 4155966, 'name': 'Fort Lauderdale, FL, US'},
        'lawton': {'id': 4540737, 'name': 'Lawton, OK, US'},
        'lawton va': None,
        'legal': {'id': 3492269, 'name': 'Trampa Legal, DO'},
        'lexington': {'id': 4297983, 'name': 'Lexington, KY, US'},
        'lexington kentucky': {'id': 4297983, 'name': 'Lexington, KY, US'},
        'license': {'id': 7915388, 'name': 'Wadat Tarkh Murr Shubr, EG'},
        'license away': None,
        'line': {'id': 4030940, 'name': 'Line Islands, KI'},
        'lines': {'id': 1183974, 'name': 'Baghdadi Lines, PK'},
        'live': {'id': 4707076, 'name': 'Live Oak County, TX, US'},
        'live in': None,
        'live in florida': None,
        'loreto': {'id': 3696183, 'name': 'Iquitos, PE'},
        'loreto mexico': {'id': 8581711, 'name': 'Loreto, MX'},
        'los': {'id': 5368361, 'name': 'Los Angeles, CA, US'},
        'los angeles': {'id': 5368361, 'name': 'Los Angeles, CA, US'},
        'maarten': {'id': 6985435, 'name': 'Saint Maarten University, SX'},
        'manhattan': {'id': 5125771, 'name': 'Manhattan, NY, US'},
        'manhattan square': {'id': 5141023, 'name': 'Times Square, NY, US'},
        'manhattan square drive': None,
        'manhattan square drive rochester': None,
        'marine': {'id': 6301844, 'name': 'Futenma Marine Corps Air Facility, JP'},
        'marine world': {'id': 7603097, 'name': 'UShaka Marine World, ZA'},
        'marine world usa': {'id': 4795551, 'name': 'Coral World Marine Park and Observatory, VI'},
        'marine world usa in': None,
        'mcallen': {'id': 4709796, 'name': 'McAllen, TX, US'},
        'mcnally': {'id': 6637893, 'name': 'McNally Peak, AQ'},
        'mcnally direction': None,
        'memphis': {'id': 4641239, 'name': 'Memphis, TN, US'},
        'memphis tn': {'id': 4641239, 'name': 'Memphis, TN, US'},
        'mexico': {'id': 3996063, 'name': 'Mexico'},
        'mi': {'id': 1529484, 'name': 'Kumul, CN'},
        'michigan': {'id': 5001836, 'name': 'Michigan, US'},
        'mileage': {'id': 6073578, 'name': 'Mileage 56, CA'},
        'miles': {'id': 6638099, 'name': 'Miles Island, AQ'},
        'miles away': {'id': 8805396, 'name': 'Miles Away, AU'},
        'minute': {'id': 6170877, 'name': 'Twenty-Five Minute Lake, CA'},
        'minute flights': None,
        'mn': {'id': 7729894, 'name': 'Eastern Asia, CN'},
        'mobile': {'id': 4076598, 'name': 'Mobile, AL, US'},
        'mobile al.': {'id': 4076598, 'name': 'Mobile, AL, US'},
        'monteray': {'id': 6097939, 'name': 'Parc Monteray, CA'},
        'monteray california': None,
        'monteray california fromn': None,
        'monteray california fromn dc': None,
        'moscow': {'id': 524901, 'name': 'Moscow, RU'},
        'myers': {'id': 4155995, 'name': 'Fort Myers, FL, US'},
        'myers fla': None,
        'myrtle': {'id': 8211876, 'name': 'Lake Myrtle, AU'},
        'myrtle beach': {'id': 4588718, 'name': 'Myrtle Beach, SC, US'},
        'myrtle beach spirit': None,
        'myrtle beach spirit airlines': None,
        'name': {'id': 613607, 'name': 'Kutaisi, GE'},
        'name your': {'id': 5687536, 'name': 'Your Name Dam, MT, US'},
        'name your own': None,
        'name your own price': None,
        'nashville': {'id': 4644585, 'name': 'Nashville, TN, US'},
        'nc': {'id': 7729899, 'name': 'Melanesia, PG'},
        'nevada': {'id': 5509151, 'name': 'Nevada, US'},
        'new': {'id': 5128581, 'name': 'New York, US'},
        'new hampshire': {'id': 5090174, 'name': 'New Hampshire, US'},
        'new jersey': {'id': 5105496, 'name': 'Trenton, NJ, US'},
        'new york': {'id': 5128581, 'name': 'New York, US'},
        'new york city': {'id': 5128581, 'name': 'New York, US'},
        'new york city ballet': None,
        'newark': {'id': 5101798, 'name': 'Newark, NJ, US'},
        'newark airport': {'id': 5101809, 'name': 'Newark Liberty International Airport, NJ, US'},
        'niagara': {'id': 6087892, 'name': 'Niagara Falls, CA'},
        'niagara falls': {'id': 6087892, 'name': 'Niagara Falls, CA'},
        'norfolk': {'id': 2155115, 'name': 'Norfolk Island'},
        'norfolk va': {'id': 4776222, 'name': 'Norfolk, VA, US'},
        'norwegian': {'id': 2960847, 'name': 'Norwegian Sea'},
        'norwegian cruises': None,
        'norwegian cruises lines': None,
        'nova': {'id': 3456160, 'name': 'Nova Iguau, BR'},
        'nova scotia': {'id': 6091530, 'name': 'Nova Scotia, CA'},
        'now': {'id': 1131700, 'name': 'Now Qalah, AF'},
        'now ther\'s': None,
        'nv': {'id': 5509151, 'name': 'Nevada, US'},
        'ny': {'id': 7535963, 'name': 'Ny-lesund, SJ'},
        'ny 14607': {'id': 5134086, 'name': 'Rochester, NY, US'},
        'ny bus': {'id': 6353133, 'name': 'George Washington Bridge Bus Station, NY, US'},
        'ny bus tours': None,
        'nyc': {'id': 5128581, 'name': 'New York, US'},
        'nyc flights': None,
        'oakland': {'id': 5378538, 'name': 'Oakland, CA, US'},
        'ohio': {'id': 5165418, 'name': 'Ohio, US'},
        'oklahoma': {'id': 4544349, 'name': 'Oklahoma City, OK, US'},
        'oklahoma vehicle': None,
        'oklahoma vehicle accident': None,
        'oklahoma vehicle accident report': None,
        'old': {'id': 454432, 'name': 'Vec-Liepja, LV'},
        'old age': {'id': 2955932, 'name': 'Anscharhhe, DE'},
        'old age pension': None,
        'on': {'id': 2636841, 'name': 'Stoke-on-Trent, GB'},
        'on i10': None,
        'on i10 alabama': None,
        'one': {'id': 2185571, 'name': 'One Tree Hill, NZ'},
        'one address': None,
        'one day': {'id': 8854013, 'name': 'A-One Hill, AU'},
        'one day cruise': None,
        'one way': {'id': 5307429, 'name': 'One Way Pass, AZ, US'},
        'one way air': None,
        'one way air fare': None,
        'or': {'id': 7280291, 'name': 'Taiwan, TW'},
        'oregon': {'id': 5744337, 'name': 'Oregon, US'},
        'oregon now': None,
        'oregon now ther\'s': None,
        'orlando': {'id': 4167147, 'name': 'Orlando, FL, US'},
        'orlando fl': {'id': 4167147, 'name': 'Orlando, FL, US'},
        'orlando fl amtrak': {'id': 7192120, 'name': 'Orlando Amtrak Station, FL, US'},
        'own': {'id': 17473, 'name': 'Own Br Beygl, IR'},
        'own price': None,
        'oxnard': {'id': 5380184, 'name': 'Oxnard, CA, US'},
        'oxnard ca.': {'id': 5380184, 'name': 'Oxnard, CA, US'},
        'pa': {'id': 5881576, 'name': 'Pago Pago, AS'},
        'packages': None,
        'park': {'id': 3748726, 'name': 'Kingstown Park, VC'},
        'park ca.': {'id': 5331575, 'name': 'Buena Park, CA, US'},
        'pennsylvania': {'id': 6254927, 'name': 'Pennsylvania, US'},
        'pennsylvania farmer': {'id': 5189347, 'name': 'Farmer Shanty Hollow, PA, US'},
        'pension': {'id': 3678149, 'name': 'La Pensin, CO'},
        'personal': {'id': 5238282, 'name': 'Manning Personal Airstrip, VT, US'},
        'personal rights': None,
        'peru': {'id': 3932488, 'name': 'Peru'},
        'petersburg': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'petersburg russia': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'philadelphia': {'id': 4560349, 'name': 'Philadelphia, PA, US'},
        'philadelphia airport': {'id': 4560342, 'name': 'Philadelphia International Airport, PA, US'},
        'phoenix': {'id': 5308655, 'name': 'Phoenix, AZ, US'},
        'phone': {'id': 1655124, 'name': 'Muang Phn-Hng, LA'},
        'photos': None,
        'pittsburgh': {'id': 5206379, 'name': 'Pittsburgh, PA, US'},
        'pittsburgh pa': {'id': 5206379, 'name': 'Pittsburgh, PA, US'},
        'place': {'id': 5881192, 'name': 'Tfuna, AS'},
        'police': {'id': 3088461, 'name': 'Police, PL'},
        'police agency': {'id': 5647164, 'name': 'Crow Agency Police Department, MT, US'},
        'pontiac': {'id': 5006166, 'name': 'Pontiac, MI, US'},
        'pontiac mi': {'id': 5006166, 'name': 'Pontiac, MI, US'},
        'portlad': None,
        'portlad bike': None,
        'portlad bike ride': None,
        'portland': {'id': 5746545, 'name': 'Portland, OR, US'},
        'portland or': {'id': 5746545, 'name': 'Portland, OR, US'},
        'price': {'id': 6623594, 'name': 'Price Nunatak, AQ'},
        'public': {'id': 3578562, 'name': 'Public, BL'},
        'public transportation': {'id': 8090478, 'name': 'State of Alaska Department of Transportation Public Facilities, AK, US'},
        'puerto': {'id': 3493175, 'name': 'Puerto Plata, DO'},
        'puerto rico': {'id': 4566966, 'name': 'Puerto Rico'},
        'raleigh': {'id': 4487042, 'name': 'Raleigh, NC, US'},
        'raleigh durham': {'id': 4487056, 'name': 'Raleigh-Durham International Airport, NC, US'},
        'raleigh nc': {'id': 4487042, 'name': 'Raleigh, NC, US'},
        'rand': {'id': 6629135, 'name': 'Rand Peak, AQ'},
        'rand mcnally': None,
        'rand mcnally direction': None,
        'rapids': {'id': 4994358, 'name': 'Grand Rapids, MI, US'},
        'rapids ia': {'id': 4850751, 'name': 'Cedar Rapids, IA, US'},
        'rent': {'id': 6119503, 'name': 'Rent Lake, CA'},
        'report': {'id': 5069168, 'name': 'Good Report Christian Center, NE, US'},
        'rico': {'id': 6322871, 'name': 'Mato Rico, BR'},
        'ride': {'id': 6039870, 'name': 'Lac Rid, CA'},
        'ride this': None,
        'ride this train': None,
        'riding-seattle': None,
        'rights': {'id': 4049985, 'name': 'Birmingham Civil Rights Institute, AL, US'},
        'rivercats': None,
        'rivercats games': None,
        'road': {'id': 3577430, 'name': 'Road Town, VG'},
        'road trip': None,
        'road trip fun': None,
        'road trip fun on': None,
        'rochester': {'id': 5134086, 'name': 'Rochester, NY, US'},
        'rochester ny': {'id': 5134086, 'name': 'Rochester, NY, US'},
        'rochester ny 14607': {'id': 5134086, 'name': 'Rochester, NY, US'},
        'rochester ny bus': None,
        'rochester ny bus tours': None,
        'rohnert': {'id': 5388564, 'name': 'Rohnert Park, CA, US'},
        'rohnert park': {'id': 5388564, 'name': 'Rohnert Park, CA, US'},
        'rohnert park ca.': {'id': 5388564, 'name': 'Rohnert Park, CA, US'},
        'roseburg': {'id': 2845123, 'name': 'Roseburg, DE'},
        'roseburg oregon': {'id': 5749352, 'name': 'Roseburg, OR, US'},
        'roseburg oregon now': None,
        'roseburg oregon now ther\'s': None,
        'rupparena': None,
        'rupparena in': None,
        'rupparena in lexington': None,
        'russia': {'id': 2017370, 'name': 'Russia'},
        'sacramento': {'id': 5389489, 'name': 'Sacramento, CA, US'},
        'sacramento rivercats': None,
        'sacramento rivercats games': None,
        'salem': {'id': 3578037, 'name': 'Salem, MS'},
        'san': {'id': 3583361, 'name': 'San Salvador, SV'},
        'san francisco': {'id': 3621911, 'name': 'San Francisco, CR'},
        'san juan': {'id': 4568127, 'name': 'San Juan, PR'},
        'san juan puerto': {'id': 4566947, 'name': 'Puerto Nuevo, PR'},
        'san juan puerto rico': {'id': 4568127, 'name': 'San Juan, PR'},
        'santiago': {'id': 3871336, 'name': 'Santiago, CL'},
        'santiago chile': {'id': 3871336, 'name': 'Santiago, CL'},
        'scenic': {'id': 7839390, 'name': 'Scenic Rim, AU'},
        'scenic drive': {'id': 5612287, 'name': 'White Pine Scenic Drive, ID, US'},
        'schedule': {'id': 4977893, 'name': 'Schedule Brook, ME, US'},
        'schedule 3': None,
        'schedule 3 26': None,
        'schedule 3 26 06': None,
        'scotia': {'id': 6091530, 'name': 'Nova Scotia, CA'},
        'scranton': {'id': 5211303, 'name': 'Scranton, PA, US'},
        'scranton trains': None,
        'seatac': {'id': 5809805, 'name': 'SeaTac, WA, US'},
        'seatle': {'id': 9857945, 'name': 'Comfort Suites Downtown Seatle, WA, US'},
        'seatle airport': None,
        'seattle': {'id': 5809844, 'name': 'Seattle, WA, US'},
        'seattle wa': {'id': 5809844, 'name': 'Seattle, WA, US'},
        'selling': {'id': 1279983, 'name': 'Siling Co, CN'},
        'senior': {'id': 6144187, 'name': 'Senior Lake, CA'},
        'senior citizen': {'id': 6347908, 'name': 'Senior Citizen Park, OR, US'},
        'senior citizen texas': None,
        'senior citizen texas driving': None,
        'service': {'id': 2383129, 'name': 'Service, CF'},
        'service -detroit': None,
        'shares': {'id': 3573041, 'name': 'Point Shares, BM'},
        'shares florida': None,
        'shoe': {'id': 2182741, 'name': 'Shoe Island, NZ'},
        'shoe casino': None,
        'shoe casino hammond': None,
        'shoe casino hammond in': None,
        'shoreline': {'id': 5810301, 'name': 'Shoreline, WA, US'},
        'shoreline train': None,
        'shutle': None,
        'sioux': {'id': 6296317, 'name': 'Sioux Lookout Airport, CA'},
        'sioux falls': {'id': 5231851, 'name': 'Sioux Falls, SD, US'},
        'south': {'id': 7729896, 'name': 'South Eastern Asia, ID'},
        'south bend': {'id': 4926563, 'name': 'South Bend, IN, US'},
        'south bend in': {'id': 4926563, 'name': 'South Bend, IN, US'},
        'south carolina': {'id': 4575352, 'name': 'Columbia, SC, US'},
        'southampton': {'id': 2637487, 'name': 'Southampton, GB'},
        'spirit': {'id': 6625867, 'name': 'Spirit, Cape, AQ'},
        'spirit airlines': None,
        'square': {'id': 2113910, 'name': 'Square Top, SB'},
        'square drive': None,
        'square drive rochester': None,
        'square drive rochester ny': None,
        'st': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'st maarten': {'id': 6985435, 'name': 'Saint Maarten University, SX'},
        'st.': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'st. augustine': {'id': 3573796, 'name': 'Saint Augustine, TT'},
        'st. petersburg': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'st. petersburg russia': {'id': 498817, 'name': 'Saint-Petersburg, RU'},
        'stadium': {'id': 200164, 'name': 'Bukhungu Stadium, KE'},
        'taking': {'id': 7589184, 'name': 'Buttu Taking, ID'},
        'taking drivers': None,
        'taking drivers license': None,
        'taking drivers license away': None,
        'tampa': {'id': 4174757, 'name': 'Tampa, FL, US'},
        'tampa florida': {'id': 4174757, 'name': 'Tampa, FL, US'},
        'tampa florida name': None,
        'tampa florida name your': None,
        'tennessee': {'id': 4662168, 'name': 'Tennessee, US'},
        'texas': {'id': 4736286, 'name': 'Texas, US'},
        'texas city': {'id': 4705692, 'name': 'League City, TX, US'},
        'texas driving': {'id': 7149528, 'name': 'American Truck Driving School, TX, US'},
        'the': {'id': 3573374, 'name': 'The Valley, AI'},
        'the bahamas': {'id': 3572887, 'name': 'Bahamas'},
        'the philadelphia': {'id': 7148877, 'name': 'University of the Sciences in Philadelphia, PA, US'},
        'the philadelphia airport': None,
        'ther\'s': {'id': 1418647, 'name': 'Jatoi Ther, PK'},
        'this': {'id': 6165255, 'name': 'This Lake, CA'},
        'this train': None,
        'tickers': None,
        'ticket': {'id': 5981558, 'name': 'le Pay Ticket, CA'},
        'ticket in': None,
        'ticket in fairborn': None,
        'ticket in fairborn ohio': None,
        'tickets': {'id': 9539428, 'name': 'Vienna International Dream Castle Hotel Tickets Disneyland Park Package'},
        'time': {'id': 3134628, 'name': 'Time, NO'},
        'time line': {'id': 9497514, 'name': 'Line, NO'},
        'time shares': None,
        'time shares florida': None,
        'tn': {'id': 7729887, 'name': 'Northern Africa, EG'},
        'tours': {'id': 2972191, 'name': 'Tours, FR'},
        'town': {'id': 3580661, 'name': 'George Town, KY'},
        'train': {'id': 6018822, 'name': 'Lac du Train, CA'},
        'train schedule': None,
        'trains': {'id': 7870755, 'name': 'Hina Station, JP'},
        'trains tours': None,
        'transatlantic': None,
        'transatlantic cruise': None,
        'transatlantic cruise southampton': None,
        'transportation': {'id': 5174172, 'name': 'Transportation Research Center of Ohio Airport, OH, US'},
        'travel': {'id': 6168542, 'name': 'Travel Lake, CA'},
        'travel boston': None,
        'travel flights': None,
        'travel orlando': None,
        'travel orlando fl': None,
        'travel packages': None,
        'trip': {'id': 664605, 'name': 'Trip, RO'},
        'trip fun': None,
        'trip fun on': None,
        'trip fun on i10': None,
        'tulsa': {'id': 4553433, 'name': 'Tulsa, OK, US'},
        'tulsa oklahoma': {'id': 4553433, 'name': 'Tulsa, OK, US'},
        'tx': {'id': 4671654, 'name': 'Austin, TX, US'},
        'uk': {'id': 6696201, 'name': 'Sark, GG'},
        'uk old': {'id': 2641014, 'name': 'Old Kilpatrick, GB'},
        'uk old age': None,
        'uk old age pension': None,
        'university': {'id': 6627240, 'name': 'University Peak, AQ'},
        'usa': {'id': 6252001, 'name': 'United States'},
        'usa in': {'id': 1643084, 'name': 'Indonesia'},
        'usa in vallejo': None,
        'used': {'id': 3107148, 'name': 'Used, ES'},
        'used car': None,
        'used car in': None,
        'used car in pennsylvania': None,
        'using': None,
        'va': {'id': 9408658, 'name': 'Southern Europe, IT'},
        'vallejo': {'id': 5405380, 'name': 'Vallejo, CA, US'},
        'vancouver': {'id': 6173331, 'name': 'Vancouver, CA'},
        'vancouver airport': {'id': 6301485, 'name': 'Vancouver International Airport, CA'},
        'vegas': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'vegas nevada': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'vegas nv': {'id': 5506956, 'name': 'Las Vegas, NV, US'},
        'vehicle': {'id': 5307893, 'name': 'Palo Verde Mobile Home and Recreational Vehicle Park, AZ, US'},
        'vehicle accident': None,
        'vehicle accident report': None,
        'vermont': {'id': 5242283, 'name': 'Vermont, US'},
        'visit': {'id': 3343370, 'name': 'Maja e Visit, AL'},
        'visit niagara': None,
        'visit niagara falls': None,
        'wa': {'id': 2294206, 'name': 'Wa, GH'},
        'war': {'id': 1121743, 'name': 'Kh-e Wr, AF'},
        'washington': {'id': 4140963, 'name': 'Washington, DC, US'},
        'washington borrows': None,
        'washington borrows 500': None,
        'washington borrows 500 000': None,
        'washington dc': {'id': 4140963, 'name': 'Washington, DC, US'},
        'washington transportation': {'id': 5242240, 'name': 'Vermont Agency of Transportation Librayr, VT, US'},
        'way': {'id': 3490165, 'name': 'Half Way Tree, JM'},
        'way air': None,
        'way air fare': None,
        'will': {'id': 1831142, 'name': 'Kampong Saom, KH'},
        'winston': {'id': 4499612, 'name': 'Winston-Salem, NC, US'},
        'winston salem': {'id': 4499612, 'name': 'Winston-Salem, NC, US'},
        'world': {'id': 6295630, 'name': 'Earth'},
        'world usa': {'id': 6949562, 'name': 'Disneyworld, FL, US'},
        'world usa in': {'id': 6338707, 'name': 'Church of God (WMC), FL, US'},
        'world usa in vallejo': None,
        'ya': {'id': 6255147, 'name': 'Asia'},
        'yankees': {'id': 6185179, 'name': 'Yankees Gully, CA'},
        'yankees stadium': None,
        'york': {'id': 5128581, 'name': 'New York, US'},
        'york city': {'id': 5128581, 'name': 'New York, US'},
        'york city ballet': None,
        'your': {'id': 6185774, 'name': 'Your Lake, CA'},
        'your own': None,
        'your own price': None,
    }


# testing ----------------------------------------------------------------------

texts = [
    # US cities
    'austin texas', 'boston', 'charlotte', 'duluth mn', 'fr. myers fla', 'ft lauderdale', 'nashville', 'niagara falls', 'orlando', 'oxnard ca.', 'phoenix', 'rohnert park ca.', 'roseburg oregon', 'texas city',
    # foreign cities
    'kemerovo', 'st. petersburg russia',
    # states
    'texas', 'alabama', 'florida', 'new jersey',
    # countries
    'usa', 'uk', 'france', 'russia',
    # other
    'europe', 'horse shoe casino hammond in', 'philadelphia airport', 'jfk', 'jfk', 'jfk'
]

if __name__ == '__main__':
    annotator = GeoNamesAnnotator()
    for text in texts:
        print
        print '"%s"' % text
        result = annotator.annotate(text.split())
        print result
