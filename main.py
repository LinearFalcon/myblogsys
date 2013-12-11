# Copyright (c) 2013 by LIANG FANG 
# New York University, Courant Institute, Dept. of Computer Science

import os
import urllib

from google.appengine.api import users
from google.appengine.ext import db

import webapp2
import jinja2
import re
import string
import datetime

# Jinja2 Environment Variable
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class Post(db.Model):           
    """ This is Post Model  """
    title = db.StringProperty()
    content = db.TextProperty(default = "")
    created_time = db.DateTimeProperty(auto_now_add=True)   
    modify_time = db.DateTimeProperty(auto_now=True)  # change to current time automatically when post modified
    tags = db.ListProperty(db.Key)                    # store keys of this post's tags
    def tagList(self):                  # return list of tag entities of this post(used in singleblog.html under Jinja2)
        return [Tag.get(key) for key in self.tags]
    def tagStr(self):
        return " ".join([Tag.get(x).tag for x in self.tags])
    def contentFormat(self):
        return content_filter(self.content)

class Tag(db.Model):
    tag = db.StringProperty()

class Blog(db.Model):            # Blog Model
    name = db.StringProperty()
    description = db.StringProperty()
    ownerid = db.StringProperty()   # store owner's user_id
    ownername = db.StringProperty()
    created_time = db.DateTimeProperty(auto_now_add=True)

def content_filter(str): 
    """ replace links in text content with HTML link or picture """
#    matchObj = re.match(r'([^"]|^)(https?|ftp)(://[\w:;/.?%#&=+-]+)', str)
    newstr = re.sub(r'(https?|ftp)(://[\w:;/.?%#&=+-]+)', urlReplacer, str)
    return newstr

def urlReplacer(match, limit = 45):
  return '<a href="%s">%s</a>' % (match.group(), match.group()[:limit] + ('...' if len(match.group()) > limit else ''))

class MainPage(webapp2.RequestHandler):
    def get(self):
        blogs = Blog.all()
        blogs.order("-created_time")
        user = users.get_current_user()
        if user:
            url = users.create_logout_url('/')
            url_linktext = user.nickname() + ' -> Logout'
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
        ownerid = user.user_id()       # user_id() returns a unique string id for google account user
        ownername = user.nickname()
        if name and description:              
            blog = Blog(name=name, description=description, ownerid=ownerid, ownername = ownername)
            blog.put()

        self.redirect('/') 

        

class BlogPage(webapp2.RequestHandler):  # Only display posts belong to selected blog entity
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
            cursor = None     # indicate this is last page
        else:
            cursor = posts.cursor()

        tag_list = []
        for post in posts:
            for tag in post.tagList():
                if tag_list:
                    isTagExist = False
                    for item in tag_list:
                        if item.tag == tag.tag:
                            isTagExist = True
                            break
                    if not isTagExist:
                        tag_list.append(tag)
                else:
                    tag_list.append(tag)

        # pass parent blogkey to singleblog page
        template_values = {'blogkey': blogkey,'posts': items, 'cursor': cursor, 'taglist': tag_list}    

        template = JINJA_ENVIRONMENT.get_template('/templates/singleblog.html')
        self.response.write(template.render(template_values))

class TagHandler(webapp2.RequestHandler):
    def get(self, tagkey, blogkey):
        tag = Tag.get(tagkey)   # get tag entity
        parentblog = Blog.get_by_id(int(blogkey))
        posts = Post.all()
        posts.ancestor(parentblog)
        posts.filter('tags', tag.key())
        posts.order("-created_time") 
 
        cursor = self.request.get('cursor')
        if cursor: 
            posts.with_cursor(start_cursor=cursor)
        items = posts.fetch(10)
        if len(items) < 10:      
            cursor = None     # indicate this is last page
        else:
            cursor = posts.cursor()

        # pass parent blogkey to singleblog page
        template_values = {'blogkey': blogkey,'posts': items, 'cursor': cursor}    

        template = JINJA_ENVIRONMENT.get_template('/templates/singleblog.html')
        self.response.write(template.render(template_values))
        

class Postblog(webapp2.RequestHandler):  
    def get(self, blogkey):        # must have get function to render the new html page
        user = users.get_current_user()
        parentblog = Blog.get_by_id(int(blogkey))
        if user:                                    # need to check if the current user is owner
            if parentblog.ownerid == user.user_id():
                template = JINJA_ENVIRONMENT.get_template('/templates/post.html')
                self.response.write(template.render({'blogkey': blogkey}))
            else:
                template = JINJA_ENVIRONMENT.get_template('/templates/error.html')
                self.response.write(template.render({'dir': 'singleblog','key': blogkey}))
        else:
            self.redirect(users.create_login_url('/post/%s' % blogkey))
    
    def post(self, blogkey):           # tag must be separated by comma ','           to be continue
        parentblog = Blog.get_by_id(int(blogkey))
        post = Post(parent=parentblog)           # set this new post's belonging blog
        post.title = self.request.get('title')
        post.content = self.request.get('content')
        tags = self.request.get('tags')
 #       post.created_time = datetime.datetime.now(pytz.timezone('US/Eastern'))  time need to reset   to be continue
        if post.title and post.content:
            taglist = tags.split(',')
            post.tags = []
            for tagstr in taglist:      # store Tag entity into datastore and they will have key
                tag = Tag.all().filter('tag =', tagstr).get()
                if tag == None:         # if this is not None, then the tag is used before
                    tag = Tag(tag=tagstr)
                    tag.put()
                post.tags.append(tag.key())
            post.put()

        self.redirect('/singleblog/%s' % blogkey)  

class SinglePost(webapp2.RequestHandler):
    def get(self, postkey):
        singlepost = Post.get(postkey)  # This key is string format, return from post.key() in singleblog.html
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
                                                     'precontent':singlepost.content,
                                                     'pretags': singlepost.tagStr()}))
            else:
                template = JINJA_ENVIRONMENT.get_template('/templates/error.html')
                self.response.write(template.render({'dir': 'singlepost','key': postkey}))
        else:
            self.redirect(users.create_login_url('/editpost/%s' % postkey))
    def post(self, postkey):
        singlepost = Post.get(postkey)
        singlepost.title = self.request.get('title')
        singlepost.content = self.request.get('content')
        tags = self.request.get('tags')
        taglist = tags.split(',')
        singlepost.tags = []
        for tagstr in taglist:      # store Tag entity into datastore and they will have key
            tag = Tag.all().filter('tag =', tagstr).get()
            if tag == None:         # if this is not None, then the tag is used before
                tag = Tag(tag=tagstr)
                tag.put()
            singlepost.tags.append(tag.key())
        singlepost.put()     #update entity
        self.redirect('/singlepost/%s' % postkey)

app = webapp2.WSGIApplication([
    ('/', MainPage), 
    ('/createblog', CreateBlog),
    ('/singleblog/(.*)', BlogPage),
    ('/post/(.*)', Postblog), 
    ('/singlepost/(.*)', SinglePost),
    ('/editpost/(.*)', EditPost),
    ('/tag/(.*)/(.*)', TagHandler)
], debug=True)
