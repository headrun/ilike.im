from facepy import GraphAPI
import facepy
import simplejson
import requests
import logging
import urlparse
import Image
import os
from itertools import chain, islice

from django.conf import settings
from django.db.models.query import QuerySet

logger = logging.getLogger('app')


def notify_user(fbuid):
    import pdb;pdb.set_trace()
    token_app = facepy.utils.get_application_access_token(settings.FACEBOOK_APP_ID, settings.FACEBOOK_API_SECRET)
    graph = GraphAPI(token_app)

    template = 'this is a test'
    path = '%s/notiffications' % fbuid
    href = 'www.dev.incog.im'

    response = graph.post(path=path, template=template, href=href)

    return "yes"


def get_facebook_friends(access_token):
    """given the access token, returns the user's friends
    it is a list of dictionaries, each dictionary containing
    name, id. """

    graph = GraphAPI(access_token)
    resp = graph.get('me/friends')
    next_page = resp['paging']
    #TODO: traverse next page (i don't know how :( )

    friends = resp['data']
    return friends

def get_meeting_sex(access_token):
    '''returns meeting sex of the user, None if null'''
    graph = GraphAPI(access_token)
    query = 'SELECT meeting_sex from user where uid=me()'
    resp = graph.fql(query)
    data = resp['data']
    data = data[0]
    meeting_sex = data['meeting_sex']
    if not meeting_sex:
        return None
    if len(meeting_sex) == 1:
        return meeting_sex[0]
    else:
        return "Both"

def get_facebook_user_info(access_token):
    '''returns uid, name, sex list of friends'''
    big_size = True

    graph = GraphAPI(access_token)
    query = 'SELECT uid,name,sex,pic, pic_big FROM user WHERE uid in (select uid2 FROM friend WHERE uid1=me())'
    resp = graph.fql(query)
    data = resp['data']

    if big_size:
        data = [(i['uid'], i['name'], i['sex'], i['pic_big']) for i in data]
    else:
        data = [(i['uid'], i['name'], i['sex'], i['pic']) for i in data]
    return data

def get_facebook_friend_names_and_ids(access_token):
    """Given the access_token, return a list of tuples. Each tuple
    contains (id, name) of a friend"""
    friends = get_facebook_friends(access_token)
    return [(friend['id'],friend['name']) for friend in friends]

def get_facebook_friend_ids(access_token):
    """given the access_token, returns the user's friends id's"""

    friends = get_facebook_friends(access_token)
    friend_ids = [friend['id'] for friend in friends]

    return friend_ids
'''
def get_bulk_pictures(access_token, id_list, width=180):
    graph = GraphAPI(access_token)
    query = "SELECT url from profile_pic WHERE "
    len_ids = len(id_list)

    string = "id=%s "*len_ids
    query += string
    query += ""
'''

def get_profile_picture(access_token, facebook_id, width=180):
    """get given profile picture given the facebook id"""

    graph = GraphAPI(access_token)
    query = 'SELECT url from profile_pic WHERE id=%s and width=%s'
    resp = graph.fql(query % (facebook_id, width))
    img = resp['data'][0]['url']
    return img

def post_to_wall(access_token, message, link="www.incog.im"):
    READY_TO_POST = False
    if not READY_TO_POST: return None

    graph = GraphAPI(access_token)
    if link:
        response = graph.post(path="me/feed", retry=1, message=message, link=link)
    else:
        response = graph.post(path="me/feed", retry=1, message=message)
    return response

def resize_picture(code, size):
    IDENTICONS_DIR = os.path.join(settings.PROJECT_DIR, 'static', 'images', 'identicons')
    fpath = os.path.join(IDENTICONS_DIR, '%s_%s.png' % (code, size))
    if os.path.exists(fpath):
        return code+'_'+size

    fpath = os.path.join(IDENTICONS_DIR, '%s.png' % code)
    try:
        im = Image.open(fpath)
        x, y = size.split('x')
        im_resized = im.resize((int(x), int(y)), Image.ANTIALIAS)
        new_fpath = os.path.join(IDENTICONS_DIR, '%s_%s.png' % (code, size))
        im_resized.save(new_fpath, 'PNG')
        code = code + '_' + size
        return code

    except:
        return code

def count_facebook_friends(access_token, facebook_id):
    graph = GraphAPI(access_token)
    query = 'SELECT friend_count from user where uid=me()'
    resp = graph.fql(query)
    friend_count = resp['data']
    return friend_count

def get_gender(access_token, facebook_id):
    graph = GraphAPI(access_token)
    query = 'SELECT sex FROM user WHERE uid=%s'
    resp = graph.fql(query % (facebook_id))
    sex = resp['data']
    return sex


class dotdictify(dict):
    marker = object()
    def __init__(self, value=None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError, 'expected dict'

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, dotdictify):
            value = dotdictify(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        found = self.get(key, dotdictify.marker)
        if found is dotdictify.marker:
            found = dotdictify()
            dict.__setitem__(self, key, found)
        return found

    __setattr__ = __setitem__
    __getattr__ = __getitem__


class QuerySetMerge(QuerySet):
    def __init__(self, querysets, key='-date_added'):
        self.querysets = querysets
        if key.startswith('-'):
            self.ascending = False
            self.key = key[1:]
        else:
            self.ascending = True
            self.key = key

    def xmerge(self, ln, ascending=True):
         """ Iterator version of merge.

         Assuming l1, l2, l3...ln sorted sequences, return an iterator that
         yield all the items of l1, l2, l3...ln in ascending order.
         Input values doesn't need to be lists: any iterable sequence can be used.
         """
        # Adapted from: http://code.activestate.com/recipes/141934-merging-sorted-sequences/

         pqueue = []
         for i in map(iter, ln):
             try:
                 pqueue.append((i.next(), i.next))
             except StopIteration:
                 pass
         pqueue.sort()
         if ascending:
             pqueue.reverse()
         X = max(0, len(pqueue) - 1)
         while X:
             d,f = pqueue.pop()
             yield d
             try:
                 # Insort in reverse order to avoid pop(0)
                 pqueue.append((f(), f))
                 pqueue.sort()
                 if ascending:
                     pqueue.reverse()
             except StopIteration:
                 X-=1
         if pqueue:
             d,f = pqueue[0]
             yield d
             try:
                 while 1: yield f()
             except StopIteration:pass

    def __len__(self):
        return self.count()

    def count(self):
        return sum(q.count() for q in self.querysets)

    def __iter__(self):
        qsets = [((getattr(x, self.key), x) for x in q) for q in self.querysets]
        merged = self.xmerge(qsets, self.ascending)
        return (x for k, x in merged)

    def __nonzero__(self):
        return self.count() != 0

    def all(self):
        return self

    def __getitem__(self, k):
        if k == 'count':
            return self.count()

        elif isinstance(k, slice):
            start, stop, step = k.indices(self.count())
            return islice(iter(self), start, stop, step)


