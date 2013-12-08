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

class Post(db.Model):            #Post Model
    title = db.StringProperty()
    content = db.TextProperty(default = "")
    created_time = db.DateTimeProperty(auto_now_add=True)   #seems not timezone sensitive, wrong time!!!!!!
    modify_time = db.DateTimeProperty(auto_now=True)  #Whenever post to datastore, it is set to current time

class Blog(db.Model):            #Blog Model
    name = db.StringProperty()
    description = db.StringProperty()
    ownerid = db.StringProperty()   #store owner's user_id
    created_time = db.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler):
    def get(self):
        blogs = Blog.all()
        blogs.order("-created_time")
        
        if users.get_current_user():
            url = users.create_logout_url('/')
            url_linktext = 'Logout'
        else:
            url = users.create_login_url('/')
            url_linktext = 'Login'

        template_values = {
            'url': url,
            'url_linktext': url_linktext,
            'blogs': blogs
        }
        template = JINJA_ENVIRONMENT.get_template('/templates/bloglist.html')
        self.response.write(template.render(template_values))

class CreateBlog(webapp2.RequestHandler):
    def get(self):        
        user = users.get_current_user()
        if user:
            template = JINJA_ENVIRONMENT.get_template('/templates/createblog.html')
            self.response.write(template.render())
        else:
            self.redirect(users.create_login_url('/'))
    
    def post(self):
        name = self.request.get('name')
        description = self.request.get('description') 
        user = users.get_current_user()
        ownerid = user.user_id()       #user_id() returns a unique string id for google account user
        if name and description:              
            blog = Blog(name=name, description=description, ownerid=ownerid)
            blog.put()

        self.redirect('/') 

        

class BlogPage(webapp2.RequestHandler):  #Only display posts belong to selected blog entity
    def get(self, blogkey):
        parentblog = Blog.get_by_id(int(blogkey))    
        posts = Post.all()
        posts.ancestor(parentblog)        
        posts.order("-created_time")

        cursor = self.request.get('cursor')
        if cursor: 
            posts.with_cursor(start_cursor=cursor)
        items = posts.fetch(10)
        if len(items) < 10:      
            cursor = None     #indicate this is last page
        else:
            cursor = posts.cursor()

        #pass parent blogkey to singleblog page
        template_values = {'blogkey': blogkey,'posts': items, 'cursor': cursor}  

        template = JINJA_ENVIRONMENT.get_template('/templates/singleblog.html')
        self.response.write(template.render(template_values))


class Postblog(webapp2.RequestHandler):   #1,check whether login in  2,if login, post and set post's parent
    def get(self, blogkey):        #must have get function to render the new html page
        user = users.get_current_user()
        parentblog = Blog.get_by_id(int(blogkey))
        if user:                                    #need to check if the current user is owner
            if parentblog.ownerid == user.user_id():
                template = JINJA_ENVIRONMENT.get_template('/templates/post.html')
                self.response.write(template.render({'blogkey': blogkey}))
            else:
                template = JINJA_ENVIRONMENT.get_template('/templates/error.html')
                self.response.write(template.render({'dir': 'singleblog','key': blogkey}))
        else:
            self.redirect(users.create_login_url('/post/%s' % blogkey))
    
    def post(self, blogkey):
        parentblog = Blog.get_by_id(int(blogkey))
        post = Post(parent=parentblog)           #set this new post's belonging blog
        post.title = self.request.get('title')
        post.content = self.request.get('content')
        if post.title and post.content:
            post.put()

        self.redirect('/singleblog/%s' % blogkey)  

class SinglePost(webapp2.RequestHandler):
    def get(self, postkey):
        singlepost = Post.get(postkey)  #This key is string format, return from post.key() in singleblog.html
        template = JINJA_ENVIRONMENT.get_template('/templates/singlepost.html')
        self.response.write(template.render({'blogkey':singlepost.parent_key().id(),
                                             'postkey': postkey,
                                             'post':singlepost}))

class EditPost(webapp2.RequestHandler):
    def get(self, postkey):
        user = users.get_current_user()
        singlepost = Post.get(postkey)
        parentblog = Blog.get_by_id(int(singlepost.parent_key().id()))
        if user:
            if parentblog.ownerid == user.user_id():
                template = JINJA_ENVIRONMENT.get_template('/templates/editpost.html')
                self.response.write(template.render({'postkey':postkey, 
                                                     'pretitle':singlepost.title,
                                                     'precontent':singlepost.content}))
            else:
                template = JINJA_ENVIRONMENT.get_template('/templates/error.html')
                self.response.write(template.render({'dir': 'singlepost','key': postkey}))
        else:
            self.redirect(users.create_login_url('/editpost/%s' % postkey))
    def post(self, postkey):
        singlepost = Post.get(postkey)
        singlepost.title = self.request.get('title')
        singlepost.content = self.request.get('content')
        singlepost.put()     #update entity
        self.redirect('/singlepost/%s' % postkey)

app = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/createblog', CreateBlog),
    ('/singleblog/(.*)', BlogPage),
    ('/post/(.*)', Postblog), 
    ('/singlepost/(.*)', SinglePost),
    ('/editpost/(.*)', EditPost)
], debug=True)
