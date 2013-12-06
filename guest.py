#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import db

import webapp2
import jinja2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Post(db.Model):
    title = db.StringProperty()
    content = db.StringProperty(indexed=False)
    created_time = db.DateTimeProperty(auto_now_add=True)
    modify_time = db.DateTimeProperty(auto_now=True)  #Whenever post to datastore, it is set to current time


class MainPage(webapp2.RequestHandler):

    def get(self):

        posts = Post.all()
        posts.order("-created_time")

        template_values = {'posts': posts}

        template = JINJA_ENVIRONMENT.get_template('/templates/index.html')
        self.response.write(template.render(template_values))


class Postblog(webapp2.RequestHandler):

    def post(self):

        post = Post(title = 'title', content = 'content')

	post.title = self.request.get('title')
        post.content = self.request.get('content') 
        post.put()

        self.redirect('/')  #Need to reload page so as to see added stuff

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', Postblog),  
], debug=True)
