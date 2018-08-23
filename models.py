from google.appengine.ext import ndb
from google.appengine.api import search


class Theme(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    image_url = ndb.StringProperty()
    created_user_email = ndb.StringProperty()
    
def tokenize_autocomplete(tags):
    a = []
    for phrase in tags:
        for word in phrase.split(" "):
            j = 1
            while True:
                for i in range(len(word) - j + 1):
                    a.append(word[i:i + j])
                if j == len(word):
                    break
                j += 1
    return a
    
class Events(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    created_user_id = ndb.StringProperty()
    time = ndb.TimeProperty()
    date = ndb.DateProperty()
    theme_id = ndb.KeyProperty(repeated=True)
    tag = ndb.StringProperty(repeated=True)
    coordinates = ndb.GeoPtProperty()
    image_urls = ndb.StringProperty(repeated=True)
    cover_image = ndb.StringProperty()
    lat = ndb.FloatProperty()
    long = ndb.FloatProperty()
    place = ndb.StringProperty()
    created_user_email = ndb.StringProperty()
    
    def _post_put_hook(self,future):
        tokens = tokenize_autocomplete(self.tag)
        value = ','.join(tokens)
        doc = search.Document(doc_id=self.key.string_id(), fields=[search.TextField(name='tag', value=value)])
        add_result = search.Index('tag').put(doc)
        print(add_result)
    
class UserThemes(ndb.Model):
    userId = ndb.StringProperty()
    themeIds = ndb.KeyProperty(repeated=True)
    emailId = ndb.StringProperty()

class Tags(ndb.Model):
    tag_id = ndb.StringProperty()
    tag_name = ndb.StringProperty()