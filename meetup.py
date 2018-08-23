#!/usr/bin/env python

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This entire application is built on top of the guestbook application tutorial
# available on Google Cloud

# [START imports]
import os
import random
from google.appengine.api import users
from google.appengine.ext import ndb
import cloudstorage
import json
import urllib, time
from google.appengine.api import search
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests
from google.appengine.api import mail
from models import Theme
from models import Events
from models import UserThemes
from models import Tags
import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

# Replace this value with the client id value that you get from Google console after regsitering your android application
CLIENT_ID = 'YOUR CLIENT ID'
GOOGLE_MAPS_API_KEY = 'YOUR API KEY'

# Helper methods used throughout the application logic
''' Helper method used by all view handlers to get generic template values'''
def get_generic_template_values(self):
    user = users.get_current_user()
    isAdmin = False
    if user:
        isAdmin = users.is_current_user_admin()
        url = users.create_logout_url(self.request.uri)
        url_linktext = 'Logout'
             
    else:
        url = users.create_login_url(self.request.uri)
        url_linktext = 'Login'
            
    template_values = {
        'isAdmin': isAdmin,
        'user':user,
        'url': url,
        'url_linktext': url_linktext
    }
    return template_values


'''Helper method used to convert ndb query results to json. 
Will be used to send back json data to android app 
make_ndb_return_data_json_serializable() & filter_results taken 
from Github gist - https://gist.github.com/bengrunfeld/062d0d8360667c47bc5b'''
def make_ndb_return_data_json_serializable(data):
    """Build a new dict so that the data can be JSON serializable"""

    result = data.to_dict()
    record = {}

    # Populate the new dict with JSON serializiable values
    for key in result.iterkeys():
        if isinstance(result[key], datetime.datetime):
            record[key] = result[key].isoformat()
            continue
        record[key] = result[key]
    
    # Add the key so that we have a reference to the record
    record['key'] = data.key.id()

    return record

def filter_results(qry):
    """
    Send NDB query result to serialize function if single result, 
    else loop through the query result and serialize records one by one
    """

    result = []

    # check if qry is a list (multiple records) or not (single record)
    if type(qry) != list:
        record = make_ndb_return_data_json_serializable(qry)
        return record

    for q in qry:
        result.append(make_ndb_return_data_json_serializable(q))

    return result

'''Helper method used to write images into Google Cloud bucket'''
def writeToGCBucket(uploaded_file):
        #if uploaded_file:
    uploaded_file_content = uploaded_file.file.read()
    uploaded_file_filename = uploaded_file.filename
    uploaded_file_type = uploaded_file.type        
    bucket_name = 'test-image-02'
         
    # This write_retry_params params bit isn't essential, but Google's examples recommend it
    write_retry_params = cloudstorage.RetryParams(backoff_factor=1.1)
    gcs_file = cloudstorage.open(
            "/" + bucket_name + "/" + uploaded_file_filename,
            "w",
            content_type=uploaded_file_type,
            retry_params=write_retry_params
    )
    gcs_file.write(uploaded_file_content)
    gcs_file.close()
 
    url = 'https://storage.googleapis.com' + "/" + bucket_name + "/" + uploaded_file_filename
    return url

'''Helper method used to geocode the location entered on screen and return the coordinates'''
def getCoordinates(address,delay=5):
    baseUrl = r"https://maps.googleapis.com/maps/api/geocode/json?"
    addressParameter = "address=" + address.replace(" ","+")
    geocodingUrl = baseUrl + addressParameter + "&key=" + GOOGLE_MAPS_API_KEY
    response = urllib.urlopen(geocodingUrl)
    jsonRaw = response.read()
    jsonData = json.loads(jsonRaw)
    if jsonData['status'] == 'OK':
        resultObject = jsonData['results'][0]
        placeInfo = [resultObject['formatted_address'],resultObject['geometry']['location']['lat'],resultObject['geometry']['location']['lng']]
    else:
        placeInfo = [None,None,None]
    time.sleep(delay) #in seconds
    return placeInfo





class MainPage(webapp2.RequestHandler):
    
    def get(self):
        template_values = get_generic_template_values(self)     
        template = JINJA_ENVIRONMENT.get_template('/views/home.html')
        self.response.write(template.render(template_values))
        



# [START Manage Page]
class ManageMeetups(webapp2.RequestHandler):
    def get(self):
        
        template_values = get_generic_template_values(self) 
        user = users.get_current_user()
        user_created_Events=[]
        if user:
            eventQuery = Events.query().filter(Events.created_user_id == user.user_id())
            user_created_Events = eventQuery.fetch()
        
        template_values['result'] = user_created_Events
        
        template = JINJA_ENVIRONMENT.get_template('/views/manageMeetup.html')
        self.response.write(template.render(template_values))
        
# [End Manage Page]

class ManageThemes(webapp2.RequestHandler):
    def get(self):
        
        template_values = get_generic_template_values(self) 
        user = users.get_current_user()
        user_subscribed_Themes = []
        themeObjects = []
        if user:
            themeQuery = UserThemes.query().filter(UserThemes.userId == user.user_id())
            user_subscribed_Themes = themeQuery.fetch()
            
            if user_subscribed_Themes != None:
                for theme in user_subscribed_Themes:
                    theme_Ids = theme.themeIds
                    if theme_Ids != None:
                        for key in theme_Ids:
                            t = key.get()
                            themeObjects.append(t)
        template_values['themes'] = themeObjects
        
        template = JINJA_ENVIRONMENT.get_template('/views/manageThemes.html')
        self.response.write(template.render(template_values))
        
# [START CreateTheme Page]
class CreateTheme(webapp2.RequestHandler):
    def get(self):
        template_values = get_generic_template_values(self) 
        template = JINJA_ENVIRONMENT.get_template('/views/createTheme.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        user = users.get_current_user()
        if user:
            theme = Theme()
            name = self.request.get('themeName')
            description = self.request.get('themeDescription')
            theme.name = name
            theme.description = description
            
            uploaded_file = self.request.POST.get("themeImage")
            url = writeToGCBucket(uploaded_file)
            theme.image_url = url
            theme.created_user_email = user.email()
            
            
            theme.put()
            self.redirect('/viewThemes')       

# [START CreateMeetup Page]      
class CreateMeetup(webapp2.RequestHandler):
    def get(self):
        template_values = get_generic_template_values(self) 
        themeQuery = Theme.query()
        themeResults = themeQuery.fetch()
            
        template_values['themeResults'] = themeResults
        template = JINJA_ENVIRONMENT.get_template('/views/createMeetup.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        created_user_id = ""
        user = users.get_current_user()
        if user:
            listOfUrls = []
            
            i = 0
            while True:
                f = self.request.POST.get("file[{}]".format(i))
                if type(f) == type(None):
                    break
                else:
                    url = writeToGCBucket(f)
                    listOfUrls.append(url)
                    i+=1
            
            
        created_user_id = user.user_id()
        themeName = self.request.get('meetupTheme')
        meetupName = self.request.get('meetupName')
        tags = self.request.get('meetupTags[]',allow_multiple=True)
        desc = self.request.get('meetupDescription')
        location = self.request.get('location')
        coordinates = getCoordinates(location)
        
        themeQuery = Theme.query(Theme.name == themeName)
        theme_id = themeQuery.fetch(keys_only=True)
        
        event = Events()
        event.name = meetupName
        event.description = desc
        event.created_user_id = created_user_id
        event.theme_id = theme_id
        event.image_urls = listOfUrls
        event.tag = tags
        event.cover_image = random.choice(listOfUrls)
        event.place = coordinates[0]
        event.lat = coordinates[1]
        event.long = coordinates[2]
        event.created_user_email = user.email()
        
        key = event.put()
        self.redirect('/manageMeetups')
        
class ViewThemes(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        email = self.request.get('email')
        template_values = get_generic_template_values(self) 
        themeQuery = Theme.query()
        results = themeQuery.fetch()
        if user:   
            
            #self.response.write(json.dumps(results))
            # for mobile
    #         serialized_results = filter_results(results)
    #         self.response.headers['Content-Type'] = 'application/json'
    #         self.response.write(json.dumps(serialized_results))
            
            template_values['results'] = results
            template = JINJA_ENVIRONMENT.get_template('/views/viewThemes.html')
            self.response.write(template.render(template_values))
        elif email:
            serialized_results = filter_results(results)
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(json.dumps(serialized_results))
            
class ViewEvents(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        email = self.request.get('email')
        template_values = get_generic_template_values(self) 
        eventsQuery = Events().query()
        results = eventsQuery.fetch()
        if user:   
            
            #self.response.write(json.dumps(results))
            # for mobile
    #         serialized_results = filter_results(results)
    #         self.response.headers['Content-Type'] = 'application/json'
    #         self.response.write(json.dumps(serialized_results))
            
            template_values['results'] = results
            #template = JINJA_ENVIRONMENT.get_template('/views/viewThemes.html')
            #self.response.write(template.render(template_values))
        elif email:
            serialized_results = filter_results(results)
            l = []
            for r in serialized_results:
            #d = serialized_results[0]
                r.pop('theme_id')
                r.pop('tag')
                r.pop('image_urls')
                l.append(r)
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(json.dumps(l))
            
        
class Search(webapp2.RequestHandler):
    def get(self):
        
        tagName = self.request.get('tag')
        eventQuery = Events().query(Events.tag == tagName)
        events = eventQuery.fetch()
        template_values = get_generic_template_values(self)
        template_values['result'] = events
        template = JINJA_ENVIRONMENT.get_template('/views/search.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        tagName = self.request.get('tag')
        eventQuery = Events().query(Events.tag == tagName)
        events = eventQuery.fetch()
        template_values = get_generic_template_values(self)
        template_values['events'] = events
        template = JINJA_ENVIRONMENT.get_template('/views/search.html')
        self.response.write(template.render(template_values))
        
        
class SingleTheme(webapp2.RequestHandler):
    def get(self):
        
        template_values = get_generic_template_values(self) 
        user = users.get_current_user()
        theme = None
        events = None
        if user:
            url_string = self.request.get('val')
            key = ndb.Key(urlsafe=url_string)
            theme = key.get()
            if theme!= None:
                eventsQuery = Events().query(Events.theme_id == key)
                events = eventsQuery.fetch()
         
        template_values['theme'] = theme   
        template_values['events'] = events   
        template = JINJA_ENVIRONMENT.get_template('/views/singleTheme.html')
        self.response.write(template.render(template_values))
        
class Subscribe(webapp2.RequestHandler):
    def get(self):
        
        template_values = get_generic_template_values(self) 
        user = users.get_current_user()
        theme = None
        if user:
            url_string = self.request.get('val')
            key = ndb.Key(urlsafe=url_string)
            
            userTheme = UserThemes()
            userTheme.userId = user.user_id()
            userTheme.themeIds.append(key)
            userTheme.put()

        template_values['theme'] = theme
        self.redirect('/manageMeetups')

 

        
class FetchTags(webapp2.RequestHandler):
    
    def get(self):
        if len(self.request.GET) > 0:
            options = search.QueryOptions(limit=10)
            query_string = self.request.GET['term']
            query = search.Query(query_string=query_string, options=options)
            results = search.Index('tag').search(query)
            l = []
            #print(results)
            for i in range(len(results.results)):
                keyword = results.results[i].fields[0].value.split(',')[-1]
                d = {'id{}'.format(i): i, "label": keyword, "value": keyword}
                l.append(d)
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(json.dumps(l))
        
class Maps(webapp2.RequestHandler):
    
    def get(self):
        location = []
        eventQuery = Events.query()
        events = eventQuery.fetch()
        template_values = get_generic_template_values(self)
        
        for event in events:
            if (event.place != None):
                place = event.place.encode('ascii')
                place1 = event.place
                place2 = event.place.encode('utf-8')
                place3 = event.place.decode('utf-8')
                location.append([place2, event.lat, event.long])
        template_values['result'] = location
        
        template = JINJA_ENVIRONMENT.get_template('/views/maps.html')
        self.response.write(template.render(template_values)) 
        
def send_approved_mail(sender_address):
    # [START send_mail]
    
    mail.send_mail(sender=sender_address,
                   to="ikkili.ikru@gmail.com",
                   subject="Find your favourite event",
                   body="""Dear User:

Some new events and themes have been added.
Please check them out and go over to your next favourite meetup


Regards,
Team Meet@UT
""")
    # [END send_mail]


class SendMailHandler(webapp2.RequestHandler):
    def get(self):
        send_approved_mail('ikkili.ikru@gmail.com')
        self.response.content_type = 'text/plain'
        self.response.write('Sent an email to User.')
        
class MobileAuthenticate(webapp2.RequestHandler):
    
    def get(self):
        print("hello")
        #username = self.request.get('username')
        token = self.request.get('token')

        result = ""
        # based on the example here: https://developers.google.com/identity/sign-in/android/backend-auth
        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                result = " bad issuer"
                raise ValueError('Wrong issuer.')

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            userid = idinfo['sub']
            result = " valid!"

            # YAY! From here we can now do whatever it is we do with google user ids!

        except ValueError, e:
            result = " " + str(e)
            # Invalid token
            pass

        self.response.write('signed in user is '  + result + userid)
        
class CreateMeetupFromMobile(webapp2.RequestHandler):
    def post(self):
        name = self.request.get('name')
        desc = self.request.get('desc')
        url = self.request.get('url')
        token = self.request.get('token')
        imageUrl = url+'&token='+token
        correctUrl = imageUrl.replace("images/", "images%2F")
        location = self.request.get('place')
        tags = self.request.get('tagValues')
        themeName = self.request.get('theme')
        
        email = self.request.get('email')
#         themeQuery = Theme.query(Theme.name == themeName)
#         theme_id = themeQuery.fetch(keys_only=True)
        event = Events()
        event.name = name
        event.description = desc
        event.cover_image = correctUrl
        
        event.created_user_email = email
#         event.theme_id = theme_id
        #event.image_urls = listOfUrls
        #event.tag = tags
        #event.cover_image = random.choice(listOfUrls)
#         coordinates = getCoordinates(location)
#         event.place = coordinates[0]
#         event.lat = coordinates[1]
#         event.long = coordinates[2]
#         event.created_user_email = user.email()
        
        key = event.put()
        self.response.write('Got post request: ' + name + '  ' + desc +  '  ' + location + '  ' + tags + '  ' + correctUrl + ' '  + email +' ' + themeName +  " " + key)
        
class CreateThemeFromMobile(webapp2.RequestHandler):
    def post(self):
            theme = Theme()
            name = self.request.get('name')
            description = self.request.get('description')
            theme.name = name
            theme.description = description
            email = self.request.get('email')
            url = self.request.get('url')
            token = self.request.get('token')
            imageUrl = url+'&token='+token
            correctUrl = imageUrl.replace("images/", "images%2F")
            theme.image_url = correctUrl
            theme.created_user_email = email
            
            
            theme.put()
            self.response.write('Got post request: ' + name + '  ' + description)        
        
    
# [START app]
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/manageMeetups', ManageMeetups),
    ('/manageThemes', ManageThemes),
    ('/createTheme', CreateTheme),
    ('/createMeetup', CreateMeetup),
    ('/viewThemes', ViewThemes),
    ('/viewEvents', ViewEvents),
    ('/search', Search),
    ('/singleTheme', SingleTheme),
    ('/subscribe', Subscribe),
    ('/maps', Maps),
    ('/ind', FetchTags),
    ('/send_mail', SendMailHandler),
    ('/mauthentic', MobileAuthenticate),
    ('/createMeetupFromMobile', CreateMeetupFromMobile),
    ('/createThemeFromMobile', CreateThemeFromMobile)
], debug=True)
# [END app]