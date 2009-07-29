from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.mail import send_mail
from django.conf import settings

import httplib # used for talking to the Fire Eagle server
import oauth # the lib you downloaded

SERVER = 'fireeagle.yahooapis.com' 

REQUEST_TOKEN_URL = 'https://fireeagle.yahooapis.com/oauth/request_token'
ACCESS_TOKEN_URL = 'https://fireeagle.yahooapis.com/oauth/access_token'
AUTHORIZATION_URL = 'http://fireeagle.yahoo.net/oauth/authorize'
QUERY_API_URL = 'https://fireeagle.yahooapis.com/api/0.1/user'
QUERY_API_URL_JSON = 'https://fireeagle.yahooapis.com/api/0.1/user.json'
UPDATE_API_URL = 'https://fireeagle.yahooapis.com/api/0.1/update'

# key and secret you got from Fire Eagle when registering an application
CONSUMER_KEY = settings.FIREEAGLE_CONSUMER_KEY
CONSUMER_SECRET = settings.FIREEAGLE_CONSUMER_SECRET

connection = httplib.HTTPSConnection(SERVER)
consumer = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

"""
Views:
1. / Homepage, not logged in
   - Intro text plus link to auth with fireeagle
2. /auth/ Auth with fireeagle
   - Creates an unauthed token, stashes in COOKIES, redirects user to fireeagle
3. /return/ Return URL
   - Checks user's unauthed token COOKIES matches, if not shows error, otherwise
     exchanges for access token, stashes that in a COOKIES and redirects the
     user to /nearby/ page
4. /nearby/
   - Looks up the user's location using their access token, then finds nearby
     wikipedia places and plots them on a static Google map
"""

def index(request):
    "/"
    if request.get_host().startswith('www.'):
        return HttpResponseRedirect("http://wikinear.com/")
    if request.COOKIES.has_key('access_token'):
        return HttpResponseRedirect('/nearby/')
    else:
        return render_to_response('index.html')

def auth(request):
    "/auth/"
    token = get_unauthorised_request_token()
    auth_url = get_authorisation_url(token)
    response = HttpResponseRedirect(auth_url)
    response.set_cookie('unauthed_token', token.to_string())
    return response

def return_(request):
    "/return/"
    unauthed_token = request.COOKIES.get('unauthed_token', None)
    if not unauthed_token:
        return HttpResponse("No un-authed token cookie")
    token = oauth.OAuthToken.from_string(unauthed_token)   
    if token.key != request.GET.get('oauth_token', 'no-token'):
        return HttpResponse("Something went wrong! Tokens do not match")
    access_token = exchange_request_token_for_access_token(token)
    response = HttpResponseRedirect('/nearby/')
    response.set_cookie('access_token', access_token.to_string())
    return response

import pprint

def nearby(request):
    "/nearby/"
    access_token = request.COOKIES.get('access_token', None)
    if not access_token:
        return HttpResponse("You need an access token COOKIES!")
    token = oauth.OAuthToken.from_string(access_token)   
    location = get_location(token)
    
    #send_mail('A fire eagle lookup', pprint.pformat(location), 'simon@simonwillison.net', ['simon@simonwillison.net'])
    
    if location['stat'] != 'ok':
        return HttpResponse("Something went wrong: <pre>" + json)
    try:
        best_location = location['user']['location_hierarchy'][0]
    except IndexError:
        return HttpResponse("Fire Eagle is not currently sharing your location with wikinear.com")
    geometry = best_location['geometry']
    if geometry['type'] == 'Polygon':
        bbox = geometry['bbox']
        lat, lon = lat_lon_from_bbox(bbox)
        is_exact = False
    elif geometry['type'] == 'Point':
        lon, lat = geometry['coordinates']
        is_exact = True
    else:
        return HttpResponse("Location was not Point or Polygon: <pre>" + json)
    nearby_pages = get_nearby_pages(lat, lon)
    return render_to_response('nearby.html', {
        'lat': lat,
        'lon': lon,
        'location': location,
        'best_location': best_location,
        'nearby_pages': nearby_pages,
        'is_exact': is_exact,
    })

def unauth(request):
    response = HttpResponseRedirect('/')
    for key in request.COOKIES:
        response.delete_cookie(key)
    return response

def fetch_response(oauth_request, connection, debug=False):
    url= oauth_request.to_url()
    connection.request(oauth_request.http_method,url)
    response = connection.getresponse()
    s=response.read()
    if debug:
        print 'requested URL: %s' % url
        print 'server response: %s' % s
    return s

def get_unauthorised_request_token():
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer, http_url=REQUEST_TOKEN_URL
    )
    oauth_request.sign_request(signature_method, consumer, None)
    resp = fetch_response(oauth_request, connection)
    token = oauth.OAuthToken.from_string(resp)
    return token

def get_authorisation_url(token):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer, token=token, http_url=AUTHORIZATION_URL
    )
    oauth_request.sign_request(signature_method, consumer, token)
    return oauth_request.to_url()

def exchange_request_token_for_access_token(request_token):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer, token=request_token, http_url=ACCESS_TOKEN_URL
    )
    oauth_request.sign_request(signature_method, consumer, request_token)
    resp = fetch_response(oauth_request, connection)
    return oauth.OAuthToken.from_string(resp) 

def get_location(access_token):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer, token=access_token, http_url=QUERY_API_URL_JSON
    )
    oauth_request.sign_request(signature_method, consumer, access_token)
    json = fetch_response(oauth_request, connection)
    return simplejson.loads(json)

from django.utils import simplejson
import urllib

def lat_lon_from_bbox(bbox):
    ((lon1, lat1), (lon2, lat2)) = bbox
    lat = min(lat1, lat2) + (max(lat1, lat2) - min(lat1, lat2)) / 2
    lon = min(lon1, lon2) + (max(lon1, lon2) - min(lon1, lon2)) / 2
    return lat, lon

def get_nearby_pages(lat, lon):
    return simplejson.load(urllib.urlopen(
        'http://ws.geonames.org/findNearbyWikipediaJSON?' +
        urllib.urlencode({
            'lat': lat,
            'lng': lon,
#            'username': 'swillison',
#            'token': '',
        })
    ))['geonames']
