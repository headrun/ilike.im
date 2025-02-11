from django.db import models, IntegrityError
from django.contrib.auth.models import User
from django.conf import settings
from django.core.urlresolvers import reverse
from django import template
from django.template import Context
from mailer import send_mail, send_html_mail

from django.db.models.signals import post_save, pre_delete
from social_auth.signals import pre_update, socialauth_registered
from social_auth.backends.facebook import FacebookBackend
from social_auth.models import UserSocialAuth
from os.path import join
from django.core.files.base import ContentFile

from utils import *

import urllib2

class FacebookUser(models.Model):
    name = models.CharField(max_length=255)
    fbuid = models.CharField(max_length=50)
    profile_pic_url = models.TextField(blank=True) #the facebook profile pic url
    sex = models.CharField(max_length=10, blank=True)
    user = models.ForeignKey(User, blank=True, null=True)
    picture = models.ImageField("profile_pic", upload_to="images", null=True, blank=True)
    meeting_sex = models.CharField(max_length=10, blank=True)
    email = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        if self.user:
            return "%s : on our network" % self.name
        else:
            return "%s : not on our network" % self.name

    @property
    def interested_in(self):
        if not self.meeting_sex == "":
            return self.meeting_sex

        #query facebook to find meeting sex
        if not self.user:
            return 0

        opposite = lambda x: 'f' if x=='male' else 'm'
        meeting_sex = get_meeting_sex(self.user.get_profile().fb_access_token)
        if not meeting_sex:
            self.meeting_sex = opposite(self.gender)
        elif meeting_sex == 'both':
            self.meeting_sex = '0'
        else:
            self.meeting_sex = meeting_sex[0]

        self.save()
        return self.meeting_sex

    @property
    def gender(self):
        if not self.sex == "":
            return self.sex
        #get gender for username with fbuid
        if self.user:
            user_profile = self.user.get_profile()
            self.sex = get_gender(user_profile.fb_access_token, self.fbuid)[0].get('sex')

        else:
            #find a friend's access token and query through his for gender
            friendship = Relationship.objects.filter(to_user=self)
            if friendship:
                friend = friendship[0].from_user
                self.sex = get_gender(friend.get_profile().fb_access_token, self.fbuid)[0].get('sex')

        self.save()
        return self.sex

    @property
    def profile_pic(self):
        if self.picture:
            return "/media/%s" % self.picture.name

        '''
        #if not self.profile_pic_url == "": return self.profile_pic_url

        if self.user:
            user_profile = self.user.get_profile()
            self.profile_pic_url = get_profile_picture(user_profile.fb_access_token, self.fbuid)
        else:
            #find a friends access token and query his profile pic
            friendship = Relationship.objects.filter(to_user=self)
            if friendship:
                friend = friendship[0].from_user
                self.profile_pic_url = get_profile_picture(friend.get_profile().fb_access_token, self.fbuid)

        self.save()
        '''
        #get the picture from facebook url
        print "Downloading picture for %s" % self.name
        img_data = urllib2.urlopen(self.profile_pic_url, timeout=5)
        filename = self.fbuid + ".png"
        self.picture = filename
        self.picture.save(
            filename,
            ContentFile(img_data.read()),
            save=True)

        self.save()
        return "/media/%s" % self.picture.name

class UserProfile(models.Model):
    """A property get_profile used on a user object that gives
    features to find friends, friendsoffriends etc,
    Usage: <User>.get_profile() gives a userprofile object
    On a UserProfile object, say up
    up.friends returns the user's friends
    """

    user = models.OneToOneField(User)
    sex = models.CharField(max_length=10, blank=True)

    def __unicode__(self):
        return "%s User Profile" % self.user

    @property
    def gender(self):
        if not self.sex == "":
            return self.sex

        social_auth_user = self.social_auth
        access_token = social_auth_user.tokens['access_token']
        uid = social_auth_user.uid
        self.sex = get_gender(access_token, uid)[0].get('sex')
        self.save()
        return self.sex

    @property
    def social_auth(self):
        user = self.user
        if user.social_auth.all():
            return user.social_auth.all()[0]
        return None

    @property
    def fbuid(self):
        social_auth_user = self.social_auth
        if social_auth_user:
            return social_auth_user.uid

        #TODO: fix this, where is it -1
        else: return -1

    @property
    def fb_access_token(self):
        return self.social_auth.tokens['access_token']

    def update_relation(self, to_user):
        to_user = FacebookUser.objects.filter(fbuid=to_user)[0]
        r = Relationship.objects.filter(from_user=self.user, to_user=to_user)
        r = r[0]
        r.count = 1 # make this +1 later
        r.save()
        if not to_user.user:
            return
        from_user = FacebookUser.objects.get(user=self.user)
        mutual = Relationship.objects.filter(from_user=to_user.user, to_user=from_user)
        if not mutual:
            return
        mutual = mutual[0]
        if mutual.count == 1:
            r.is_mutual = True
            mutual.is_mutual = True
            r.save()
            mutual.save()
            send_email(r, mutual)

def send_email(relation1, relation2):
    if relation1.count == relation2.count:
        if relation1.count == 1: # heart
            user1 = relation1.to_user
            user2 = relation2.to_user
            subject = 'Congratulations! Looks like the feeling is mutual'
            t = template.loader.get_template('mail/mutual.html')

            c = Context({'username':user1.name, 'friend':user2.name})
            body = t.render(c)
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user1.email])

            c = Context({'username':user2.name, 'friend':user1.name})
            body = t.render(c)
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user2.email])



def create_user_profile(sender, instance, created, **kwargs):
    """defined to create the UserProfile instance when a User
    object is created
    Also, updates or creates an entry for FacebookUser
    """
    if created:
        user_profile = UserProfile.objects.create(user=instance)


#signal to create the UserProfile which in turn creates a FacebookUser entry as well
post_save.connect(create_user_profile, sender=User)

def new_user_handler(sender, user, response, details, **kwargs):
        fb_user = FacebookUser.objects.filter(fbuid=response['id'])
        if fb_user:
            fb_user = fb_user[0]
            fb_user.name = user.get_full_name()
            fb_user.sex = response['gender']
            fb_user.email = response['email']
            fb_user.user = user
            fb_user.save()
        else:
            access_token = user.get_profile().fb_access_token
            gender = get_gender(access_token, response['id'])[0].get('sex')
            pic = get_profile_picture(access_token, response['id'])
            FacebookUser.objects.create(name=user.get_full_name(), fbuid=response['id'], user=user, sex=gender,profile_pic_url=pic, email=response['email'])

        update_friendships(sender, user, response, details, **kwargs)

class Relationship(models.Model):
    #Relationship entry is a Friend
    from_user = models.ForeignKey(User, related_name='from_user')
    to_user = models.ForeignKey(FacebookUser, related_name='to_user')
    count = models.IntegerField(default=0)
    is_mutual = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s friends with %s" % (self.from_user, self.to_user)


def update_friendships(sender, user, response, details, **kwargs):
    '''When a new user registers: Gets all fb friends and
    creates FacebookUser accounts for them if not existing already'''

    user_access_token = response['access_token']
    #update this person's facebook profile picture
    user_profile_pic = get_profile_picture(user_access_token, response['id'])
    current_fb_user = FacebookUser.objects.filter(user=user)
    if current_fb_user:
        current_fb_user = current_fb_user[0]
        current_fb_user.profile_pic_url = user_profile_pic
        current_fb_user.save()


    fb_friends = get_facebook_user_info(user_access_token)
    for fbuid, name, gender,pic in fb_friends:
        fb_user = FacebookUser.objects.filter(fbuid=fbuid)
        if fb_user:
            fb_user = fb_user[0]
        else:
            fb_user = FacebookUser.objects.create(name=name, fbuid=fbuid, sex=gender, profile_pic_url=pic)

        #Change to get or create
        if Relationship.objects.filter(from_user=user, to_user=fb_user):
            continue
        Relationship.objects.create(from_user=user, to_user=fb_user)

pre_update.connect(update_friendships, sender=FacebookBackend)
socialauth_registered.connect(new_user_handler, sender=None)

