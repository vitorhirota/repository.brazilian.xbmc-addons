# -*- coding: UTF-8 -*-
'''
    Globo.tv plugin for XBMC

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import json
import re
import requests
import util


# xhrsession = requests.session()
# xhrsession.headers['User-Agent'] = 'xbmc.org'
# xhrsession.headers['X-Requested-With'] = 'XMLHttpRequest'

# url masks
BASE_URL = 'http://globotv.globo.com'
SHOW_URL = BASE_URL + '%(uri)s'
RAIL_URL = SHOW_URL + '/_/trilhos/%(rail)s/page/%(page)s/'
INFO_URL = 'http://api.globovideos.com/videos/%s/playlist'
OFFER_URL = 'http://globotv.globo.com/_/oferta_tematica/%(slug)s.json'
HASH_URL = ('http://security.video.globo.com/videos/%s/hash?'
            + 'resource_id=%s&version=%s&player=flash')
LOGIN_URL = 'https://login.globo.com/login/151?tam=widget'
API_MIN_URL = 'http://s.videos.globo.com/p2/j/api.min.js'


class GloboApi(object):
    def __init__(self, plugin, cache):
        self.plugin = plugin
        self.cache = cache

    def _get_cached(self, key):
        data = self.cache.get(key)
        if data:
            try:
                data = eval(data)
            except:
                pass
        elif 'http://' in key:
            r = requests.get(key)
            data = (r.headers.get('content-type') == 'application/json'
                    and json.loads(r.text) or r.text)
            self.cache.set(key, repr(data))
        return data
        
    def _get_player_version(self):
        req = requests.get(API_MIN_URL)
        rexp = r'playerVersion="([\d\.]+)"'
        playerVersion = re.findall(rexp,req.text)
        if playerVersion:
            return playerVersion[0]
        raise Exception("Player version not found")
     
    def _get_hashes(self, video_id, resource_ids, auth_retry=False, player_retry=False):
        playerVersion = self.plugin.get_setting('player_version')
        if not playerVersion:
            playerVersion = self._get_player_version()
            self.plugin.set_setting('player_version', playerVersion)
        args = (video_id, '|'.join(resource_ids), playerVersion)
        _cookies = {'GLBID': self.authenticate()}
        self.plugin.log.debug('requesting hash: %s' % (HASH_URL % args))
        req = requests.get(HASH_URL % args, cookies=_cookies)
        self.plugin.log.debug('resource ids: %s' % '|'.join(resource_ids))
        self.plugin.log.debug('return: %s' %
                              req.text.encode('ascii', 'replace'))
        try:
            data = json.loads(req.text)
            return data['hash']
        except ValueError:
            msg = 'JSON not returned. Message returned:\n%s' % req.text
            self.plugin.log.error(msg)
            raise
        except KeyError:
            args = (data['http_status_code'], data['message'])
            self.plugin.log.error('Request error: [%s] %s' % args)
            
            if data['message'] == "Player not recognized":
                self.plugin.log.debug('cleaning player version')
                self.plugin.set_setting('player_version', '')
                if not player_retry:
                    self.plugin.log.debug('retrying player version')
                    return self._get_hashes(video_id, resource_ids, auth_retry, True)
                    
            if str(args[0]) == '403' and _cookies['GLBID']:
                # if a 403 is returned (authentication needed) and there is an
                # globo id, then this might be due to session expiration and a
                # retry with a blank id shall be tried
                self.plugin.log.debug('cleaning globo id')
                self.plugin.set_setting('glbid', '')
                if not auth_retry:
                    self.plugin.log.debug('retrying authentication')
                    return self._get_hashes(video_id, resource_ids, True, player_retry)
            raise Exception(data['message'])

    def _get_video_info(self, video_id):
        recache = False
        info = self._get_cached('video|%s' % video_id) or dict()
        if 'resources' not in info:
            data = self._get_cached(INFO_URL % video_id)['videos'][0]
            # substitute unicode keys with basestring
            data = dict((str(key), value) for key, value in data.items())
            info.update(data)
            recache = True
        if 'duration' not in info:
            info['duration'] = sum(x['resources'][0]['duration']/1000
                                   for x in info.get('children') or [info])
            recache = True
        if recache:
            self.cache.set('video|%s' % video_id, repr(info))
        return info

    def _get_show_tree(self):
        # two trees shall be built, one base on categories, the other on channels
        tree = {}
        data = self._get_cached(BASE_URL)

        # match channels
        rexp = (r'<a href="/([\w-]*)/" .* data-event-listagem-canais.*=' +
                r'([\s\S]+?)>')
        channels = re.compile(rexp).findall(data)

        # match categories
        rexp = (r'<h4 data-tema-slug="(.+?)">(.+?)<span[\s\S]+?<ul>' +
                r'([\s\S]+?)</ul>')
        categories_match = re.compile(rexp).findall(data)

        shows = {}
        channels = set()
        for slug, category, content in categories_match:
            # match show uri, names and thumb and return an object
            # match: ('/gnt/decora', 'Decora', 'http://s2.glbimg.com/[.].png'),
            shows_re = (r'<a href="/([\w-]*)/([\w-]*)/".*programa="(.+?)">' +
                        r'[\s\S]+?<img data-src="(.+?)"')
            shows_match = re.compile(shows_re).findall(content)
            channels |= set([i[0] for i in shows_match])
            shows[slug] = {'title': category, 'shows': shows_match}


        tree['categories'] = dict(zip(shows.keys(),
                                      [i['title'] for i in shows.values()]))

        return tree

    def authenticate(self):
        glbid = self.plugin.get_setting('glbid')
        username = self.plugin.get_setting('username')
        password = self.plugin.get_setting('password')

        if not glbid and (username and password):
            payload = {
                'botaoacessar': 'acessar',
                'login-passaporte': username,
                'senha-passaporte': password
            }
            self.plugin.log.debug('username/password set. trying to authenticate')
            r = requests.post(LOGIN_URL, data=payload)
            glbid = r.cookies.get('GLBID')
            if glbid:
                self.plugin.log.debug('successfully authenticated')
                self.plugin.set_setting('glbid', glbid)
            else:
                self.plugin.log.debug('wrong username or password')
                self.plugin.notify(self.plugin.get_string(31001))
        elif glbid:
            self.plugin.log.debug('already authenticated with id %s' % glbid)
        return glbid

    def get_shows_by_categories(self):
        categories = {}
        data = self._get_cached(BASE_URL)
        # match categories
        rexp = ('<h4 data-tema-slug="(.+?)">(.+?)' +
                r'<span[\s\S]+?<ul>([\s\S]+?)</ul>')
        for slug, category, content in re.compile(rexp).findall(data):
            # match show uri, names and thumb and return an object
            # match: ('/gnt/decora', 'Decora', 'http://s2.glbimg.com/[.].png'),
            shows_re = ('<a href="(.+?)".*programa="(.+?)">' +
                        r'[\s\S]+?<img data-src="(.+?)"')
            shows = re.compile(shows_re).findall(content)
            categories[slug] = {'title': category, 'shows': shows}
        return categories

    def get_rails(self, uri):
        data = self._get_cached(SHOW_URL % {'uri': uri})
        # match video 'rail's id and name
        # match ex: ('4dff4cf691089163a9000002', 'Edi\xc3\xa7\xc3\xa3o')
        rails_re = r'id="trilho-(.+?)"[\s\S]+?<h2.*title="(.+?)"'
        rails = re.compile(rails_re).findall(data)
        return rails

    def get_rail_videos(self, **kwargs):
        video_count = last_count = 0
        videos = util.struct()
        videos.list = []
        videos.next = 1
        while video_count < int(self.plugin.get_setting('page_size') or 15):
            data = requests.get(RAIL_URL % kwargs).text
            # match video 'rail's
            # match: (title, video_id, date [DD/MM/AAAA],
            #         thumb, duration [MM:SS], plot)
            regExp = (
                r'<li.*data-video-title="(.+?)"[\s]+data-video-id="(.+?)"[\s]+'
                + r'data-video-data-exibicao="(.+?)">[\s\S]+?'
                + r'<img.+src="(.+?)"[\s\S]+?'
                + r'<span class="duracao.*?">(.+?)</span>[\s\S]+?'
                + r'div class="balao">[\s]+?<p>[\s]+?([\w].+?)[\s]+?</p>'
            )
            matches = re.compile(regExp).findall(data)
            mcount = len(matches)
            properties = ('title', 'id', 'date', 'thumb', 'duration', 'plot')
            for item in matches:
                video = util.struct(dict(zip(properties, item)))
                # update attrs
                video.title = util.unescape(video.title)
                video.plot = util.unescape(video.plot)
                video.date = video.date.replace('/', '.')
                _split = video.duration.split(':')
                video.duration = sum(int(x) * 60 ** i for i, x in
                                     enumerate(reversed(_split)))
                self.cache.set('video|%s' % video.id, repr(video))
                videos.list.append(video)
            if mcount == 0 or mcount < last_count:
                videos.next = None
                break
            video_count += mcount
            last_count = mcount
            kwargs['page'] += 1
        if videos.next:
            videos.next = kwargs['page']
        return videos

    def get_offer_videos(**kwargs):
        data = json.loads(requests.get(OFFER_URL % kwargs).text)
        key = {'last': 'ultimos_videos',
               'popular': 'videos_mais_vistos'}[kwargs.get('filter') or 'last']
        content = json.loads(data)[key]
        items = []
        for entry in content:
            date, duration, descr = (entry['exibicao'],
                                     entry['duracao'],
                                     entry['descricao'])
            # params = {'action': 'play', 'video_id': _id}
            items.append({
                'Date': date.replace('/', '.'),
                'Duration': duration,
                'PlotOutline': descr,
            })
            # addItem(title, thumb, params, listItemAttr)
            # self.cache.set(_id, repr([title, date, thumb, duration, descr]))
        return items

    def get_videos(self, video_id):
        data = self._get_video_info(video_id)
        if 'children' in data:
            items = [util.struct(self._get_video_info(video['id']))
                     for video in data.get('children')]
            return items
        else:
            return [util.struct(data)]

    def resolve_video_url(self, video_id):
        # which index to look in the list
        hd_first = int(self.plugin.get_setting('video_quality') or 0)
        data = self._get_video_info(video_id)
        self.plugin.log.debug('resolving video: %s' % video_id)
        # this method assumes there's no children
        if 'children' in data:
            raise Exception('Invalid video id: %s' % video_id)

        resources = [r for r in sorted(data['resources'],
                                       key=lambda v: v.get('height') or 0)
                     if r.has_key('players') and 'flash' in r['players']]

        r = resources[-1] if hd_first else resources[0]
        hashes = self._get_hashes(video_id, [r['_id']])
        signed_hashes = util.hashJS.get_signed_hashes(hashes)
        # live videos might differ
        query_string = re.sub(r'{{([a-z]*)}}',
                              r'%(\1)s',
                              r['query_string_template']) % {
                                'hash': signed_hashes[0],
                                'key': 'html5'
                              }
        url = '?'.join([r['url'], query_string])
        self.plugin.log.debug('video url: %s' % url)
        return url

