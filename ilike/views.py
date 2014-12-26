import os
import re
import requests
import urlparse
import logging
import simplejson
import hashlib
import random

from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.conf import settings
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY
from django.db.utils import load_backend
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt

from mailer import send_mail
from ilike.models import *
from ilike.utils import *

logger = logging.getLogger('app')

def render_response(request, template, data=None):
    data = data or {}
    r = RequestContext(request)
    data['ref_path'] = request.get_full_path()
    return render_to_response(template, data, context_instance=r)

def get_friends_from_filter(user, start, end, filter_param):

    if filter_param == 'c':
        return Relationship.objects.filter(from_user=user, count__gt=0)[start:end]

    fb_friends = Relationship.objects.filter(from_user=user)
    if filter_param == 'm':
        fb_friends = fb_friends.filter(to_user__sex='male')[start:end]
    elif filter_param == 'f':
        fb_friends = fb_friends.filter(to_user__sex='female')[start:end]
    else:
        fb_friends = fb_friends[start:end]

    return fb_friends

@csrf_exempt
@login_required
def crushes(request):
    page = request.GET.get('page', 1)
    nItems = 20

    data = {}
    page = int(page)-1 #Masonry assumes that page number starts from 1
    index = page * nItems

    fb_friends = get_friends_from_filter(request.user, index, index + nItems, 'c')
    #old line retained below
    #fb_friends = Relationship.objects.filter(from_user=request.user)[index: index + nItems]
    return render_response(request, 'my_crushes.html', {'data':fb_friends} )

@csrf_exempt
@login_required
def home(request):
    filter_param = request.GET.get('filter', -1) #0 for no filter
    page = request.GET.get('page', 1)
    nItems = 20

    data = {}
    page = int(page)-1 #Masonry assumes that page number starts from 1
    index = page * nItems

    if filter_param == -1:
        fb_user = FacebookUser.objects.filter(user=request.user)
        if fb_user:
            fb_user = fb_user[0]
            filter_param = fb_user.interested_in
        else:
            filter_param = 0
    #applying filter
    fb_friends = get_friends_from_filter(request.user, index, index + nItems, filter_param)
    #old line retained below
    #fb_friends = Relationship.objects.filter(from_user=request.user)[index: index + nItems]
    return render_response(request, 'home.html', {'data':fb_friends,'filter_param':filter_param} )

@csrf_exempt
@login_required
def display_pic(request, uid):
    #uid is the fbuid of user whose picture we need to display
    target_user = FacebookUser.objects.filter(fbuid=uid)
    if not target_user:
        #if a custom invalid query
        return HttpResponse()

    target_user = target_user[0]
    img_url = target_user.profile_pic

    return HttpResponsePermanentRedirect(urlparse.urljoin(settings.MEDIA_URL, img_url))


@csrf_exempt
@login_required
def change_state(request):
    from_user = request.user.get_profile()
    to_user = request.POST.get('uid', None)
    if not to_user:
        return HttpResponse()
    from_user.update_relation(to_user)
    return HttpResponse()

def index(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))
    return render_response(request, 'index.html')

def login_error(request):

    return render_response(request, 'index.html')

def fb_page(request):
    return render_response(request, 'fb_page.html')

def demo_404(request):
    return render_response(request, '404.html')

def terms(request):
    return render_response(request, 'terms.html')

def privacy(request):
    return render_response(request, 'privacy.html')

def press(request):
    return render_response(request, 'press.html')

def how(request):
    return render_response(request, 'how.html')

