import os
import urllib

from google.appengine.api import users
from google.appengine.ext import db

import webapp2
import jinja2
import re
import string


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Post(db.Model):
    title = db.StringProperty()
    content = db.StringProperty(indexed=False)
    created_time = db.DateTimeProperty(auto_now_add=True)   #seems not timezone sensitive, wrong time!!!!!!
    modify_time = db.DateTimeProperty(auto_now=True)  #Whenever post to datastore, it is set to current time


class MainPage(webapp2.RequestHandler):

    def get(self):

        posts = Post.all()
        posts.order("-created_time")

        template_values = {'posts': posts}

        template = JINJA_ENVIRONMENT.get_template('/templates/index.html')
        self.response.write(template.render(template_values))


class Postblog(webapp2.RequestHandler):
    def get(self):        #must have get function to render the new html page
        template = JINJA_ENVIRONMENT.get_template('/templates/post.html')
        self.response.write(template.render())
    
    def post(self):
        title = self.request.get('title')
        content = self.request.get('content') 
        if title and content:
            post = Post(title=title, content=content)
            post.put()

        self.redirect('/')  

class SinglePost(webapp2.RequestHandler):
    def get(self, key):
        singlepost = Post.get_by_id(int(key))
        template = JINJA_ENVIRONMENT.get_template('/templates/singlepost.html')
        self.response.write(template.render(post=singlepost))

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/post', Postblog), 
    ('/singlepost/(.*)', SinglePost)
], debug=True)
