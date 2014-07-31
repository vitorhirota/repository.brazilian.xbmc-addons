# -*- coding: UTF-8 -*-
'''
Globo API for plugin.video.globo.com


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
import itertools
import json
import re
import requests

import backends
import hashjs
import util

# xhrsession = requests.session()
# xhrsession.headers['User-Agent'] = 'xbmc.org'
# xhrsession.headers['X-Requested-With'] = 'XMLHttpRequest'

# url masks
BASE_URL = 'http://%s.globo.com'

GLOBOTV_URL = BASE_URL % 'globotv'
GLOBOTV_MAIS_URL = GLOBOTV_URL + '/mais/'
GLOBOTV_EPS_JSON = GLOBOTV_URL + '/rede-globo/%s/integras/recentes/%d.json'
GLOBOTV_SHOWTB_URL = 'http://s01.video.glbimg.com/x360/%s.jpg'
GLOBOTV_PROGIMG_URL = 'http://s.glbimg.com/vi/mk/program/%s/logotipo/2/149x84.png'

GLOBOSAT_URL = BASE_URL % 'globosatplay'
GLOBOSAT_LIVE_JSON = GLOBOSAT_URL + '/xhr/transmissoes/ao-vivo.json'

# RAIL_URL = SHOW_URL + '/_/trilhos/%(rail)s/page/%(page)s/'
INFO_URL = 'http://api.globovideos.com/videos/%s/playlist'
HASH_URL = ('http://security.video.globo.com/videos/%s/hash?'
            + 'resource_id=%s&version=%s&player=flash')
LOGIN_URL = 'https://login.globo.com/login/151?tam=widget'
JSAPI_URL = 'http://s.videos.globo.com/p2/j/api.min.js'


class GloboApi(object):

    def __init__(self, plugin, cache):
        self.plugin = plugin
        self.cache = cache
        self.index = self._build_base_index()

    def _get_page(self, url, **kwargs):
        r = requests.get(url, **kwargs)
        return ('application/json' in r.headers.get('content-type')
                and json.loads(r.text) or r.text)

    def _get_player_version(self):
        req = self._get_page(JSAPI_URL)
        rexp = r'playerVersion="([\d\.]+)"'
        playerVersion = re.findall(rexp, req)
        try:
            return playerVersion[0]
        except:
            raise Exception("Player version not found")

    def _get_hashes(self, video_id, resource_ids, auth_retry=False, player_retry=False):
        playerVersion = self.plugin.get_setting('player_version')
        if not playerVersion:
            playerVersion = self._get_player_version()
            self.plugin.set_setting('player_version', playerVersion)

        args = (video_id, '|'.join(resource_ids), playerVersion)
        cookies = {'GLBID': self.authenticate()}

        self.plugin.log.debug('requesting hash: %s' % (HASH_URL % args))

        data = self._get_page(HASH_URL % args, cookies=cookies)

        self.plugin.log.debug('resource ids: %s' % '|'.join(resource_ids))
        self.plugin.log.debug('return: %s' % repr(data).encode('ascii', 'replace'))
        try:
            return data['hash']
        except ValueError:
            msg = 'JSON not returned. Message returned:\n%s' % data
            self.plugin.log.error(msg)
            raise
        except KeyError:
            args = (data['http_status_code'], data['message'])
            self.plugin.log.error('request error: [%s] %s' % args)

            if data['message'] == "Player not recognized":
                self.plugin.log.debug('cleaning player version')
                self.plugin.set_setting('player_version', '')
                if not player_retry:
                    self.plugin.log.debug('retrying player version')
                    return self._get_hashes(video_id, resource_ids, auth_retry, True)

            if str(args[0]) == '403' and cookies['GLBID']:
                # if a 403 is returned (authentication needed) and there is an
                # globo id, then this might be due to session expiration and a
                # retry with a blank id shall be tried
                self.plugin.log.debug('cleaning globo id')
                self.plugin.set_setting('glbid', '')
                if not auth_retry:
                    self.plugin.log.debug('retrying authentication')
                    return self._get_hashes(video_id, resource_ids, True, player_retry)
            raise Exception(data['message'])

    # @cache.cacheFunction
    def _get_video_info(self, video_id):
        # get video info
        data = self._get_page(INFO_URL % video_id)['videos'][0]
        # substitute unicode keys with basestring
        data = dict((str(key), value) for key, value in data.items())

        if 'duration' not in data:
            data['duration'] = sum(x['resources'][0]['duration']/1000
                                   for x in data.get('children') or [data])

        return data

    def _build_base_index(self):
        # get globosat play page
        html = self._get_page(GLOBOSAT_URL)

        # build on demmand channels
        globo = [('globo', 'Rede Globo', 'http://s.glbimg.com/vi/mk/channel/196/logotipo/4/149x84.png')]
        # get globosat channels list
        ptrn_channels = r'<a href="/([\w-]*?)/"[ \w="]*>[\s]*<img alt="([\w+ ]+)" src="([^"]*)"'
        channels = globo + util.find(ptrn_channels, html)

        # build live channels (as items)
        ptrn_live = r'<a href="/([\w/-]*?)/ao-vivo/"[ \w="]*>[\s]*<img alt="([\w+ ]+)"'
        data_html = util.find(ptrn_live, html)
        data_json = self._get_page(GLOBOSAT_LIVE_JSON)
        live = [util.struct({
                'slug': slug,
                'name': name,
                'logo': item['canal_logotipo'],
                'thumb': item['midia']['thumb'],
                'plot': (', '.join(reversed(item['programacao'].values()))
                         if item.get('programacao') else None)
            }) for (slug, name), item in zip(data_html, data_json)
            if item['status'] == 'ativa']

        return {
            'index': [
                ('channels', self.plugin.get_string(30011)),
                ('live', self.plugin.get_string(30012)),
                ('favorites', self.plugin.get_string(30013)),
            ],
            'channel': channels,
            'live': live,
            'favorites': self.plugin.get_setting('favorites'),
        }
        try:
            items = getattr(self, '_build_%s' % key)()
        except:
            items = self._build_globosat(key)
        self.index[key] = items

    def _build_globo(self, key):
        html = self._get_page(GLOBOTV_MAIS_URL)
        ex = (r'<h2>([\w <>]*)</strong></h2>|' +
              r'<li title.*?' +
              r'data-src=".*?=/(.*?program/([\d]*)/logotipo[\w/]*?.png|.*?logotipo_vertical.png)" ' +
              r'data-titulo-canal="([^"]*)".*?' +
              r'<a href="/rede-globo/([\w-]*?)/')
        shows = {'categories': [], 'shows': {}}
        for category, img, showid, name, slug in util.find(ex, html):
            if category:
                category = category.replace('<strong>', '')
                cat = util.slugify(category)
                shows['categories'].append((cat, category))
                shows['shows'][cat] = []
                continue
            else:
                img = GLOBOTV_PROGIMG_URL % showid if showid else 'http://' + img
                shows['shows'][cat].append((slug, util.unescape(name), img))
        return shows

    def _build_globosat(self, key):
        # to-do
        pass
        return []


    def authenticate(self, provider):
        glbid = self.plugin.get_setting('glbid')

        try:
            backend = getattr(backends, provider)
            backend = backend(self.plugin, username, password)
        except AttributeError:
            self.plugin.log.error('%s provider unavailable' % provider)
            self.plugin.notify(self.plugin.get_string(32001) % provider)

        user_id = backend.authenticate()
        return user_id

    def get_path(self, key):
        # import pydevd; pydevd.settrace()
        if not self.index.get(key):
            method = '_build_%s' % (key if key == 'globo' else 'globosat')
            self.index[key] = getattr(self, method)(key)
            # self.cache.set('index', self.index)
        return self.index.get(key)

    def get_episodes(self, channel, show, page):
        page_size = int(self.plugin.get_setting('page_size') or 10)
        video_count = 0
        videos = util.struct({'list': [], 'next': 1})
        if channel == 'globo':
            while video_count < page_size:
                self.plugin.log.debug('getting episodes: %s' % (GLOBOTV_EPS_JSON % (show, page)))
                data = self._get_page(GLOBOTV_EPS_JSON % (show, page))
                try:
                    properties = ('title', 'id', 'date', 'duration', 'plot')
                    prop_data = ('titulo', 'id', 'exibicao', 'duracao', 'descricao')
                    for item in data:
                        video = util.struct(dict(zip(properties,
                                                     [item.get(p) for p in prop_data])))
                        # update attrs
                        video.date = video.date.replace('/', '.')
                        video.duration = sum(int(x) * 60 ** i for i, x in
                                             enumerate(reversed(video.duration.split(':'))))
                        # video.duration = video.duration.split(':')[0]
                        video.thumb = GLOBOTV_SHOWTB_URL % video.id
                        # self.cache.set('video|%s' % video.id, repr(video))
                        videos.list.append(video)
                    self.plugin.log.debug(repr(videos))
                    video_count += len(data)
                    page += 1
                except AttributeError:
                    videos.next = None
                    break
            if videos.next:
                videos.next = page
            return videos
        else:
            # to=do
            return []




    def get_shows_by_categories(self):
        categories = {}
        data = self._get_page(BASE_URL)
        # match categories
        rexp = ('<h4 data-tema-slug="(.+?)">(.+?)' +
                r'<span[\s\S]+?<ul>([\s\S]+?)</ul>')
        for slug, category, content in util.find(rexp, data):
            # match show uri, names and thumb and return an object
            # match: ('/gnt/decora', 'Decora', 'http://s2.glbimg.com/[.].png'),
            shows_re = ('<a href="(.+?)".*programa="(.+?)">' +
                        r'[\s\S]+?<img data-src="(.+?)"')
            shows = util.find(shows_re, content)
            categories[slug] = {'title': category, 'shows': shows}
        return categories

    def get_rails(self, uri):
        data = self._get_page(SHOW_URL % {'uri': uri})
        # match video 'rail's id and name
        # match ex: ('4dff4cf691089163a9000002', 'Edi\xc3\xa7\xc3\xa3o')
        rails_re = r'id="trilho-(.+?)"[\s\S]+?<h2.*title="(.+?)"'
        rails = util.find(rails_re, data)
        return rails

    def get_rail_videos(self, **kwargs):
        video_count = last_count = 0
        videos = util.struct()
        videos.list = []
        videos.next = 1
        while video_count < int(self.plugin.get_setting('page_size') or 15):
            data = self._get_page(RAIL_URL % kwargs)
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
            matches = util.find(regExp, data)
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
        data = self._get_page(OFFER_URL % kwargs)
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
        else:
            items = [util.struct(data)]
        return items

    def resolve_video_url(self, video_id):
        # which index to look in the list
        hd_first = int(self.plugin.get_setting('video_quality') or 0)
        data = self._get_video_info(video_id)
        self.plugin.log.debug('resolving video: %s' % video_id)
        # this method assumes there's no children
        if 'children' in data:
            raise Exception('Invalid video id: %s' % video_id)


        resources = sorted(data['resources'],
                           key=lambda v: v.get('height') or 0,
                           reverse=(not bool(hd_first)))
        while True:
            r = resources.pop()
            if r.has_key('players') and 'flash' in r['players']:
                break

        hashes = self._get_hashes(video_id, [r['_id']])
        signed_hashes = hashjs.get_signed_hashes(hashes)
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

