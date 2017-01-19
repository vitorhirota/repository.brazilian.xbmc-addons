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
import datetime
import backends
import m3u8
import re
import requests
import scraper
import util
import urllib

# url masks
INFO_URL = 'http://api.globovideos.com/videos/%s/playlist'
HASH_URL = ('http://security.video.globo.com/videos/%s/hash?'
            + 'resource_id=%s&version=%s&player=%s&udid=null')

GLOBO_LOGO = 'http://s3.glbimg.com/v1/AUTH_180b9dd048d9434295d27c4b6dadc248/media_kit/42/f3/a1511ca14eeeca2e054c45b56e07.png'

class GloboApi(object):

    def __init__(self, plugin):
        self.plugin = plugin
        self.index = plugin.get_storage('index')
        if not isinstance(self.index.get('favorites'), set):
            # needed for v1.3
            # TBD: remove in the future
            self.index.clear()
        if not any(self.index.items()):
            # kick start index for first runs
            self.index.update(self._build_index())
        elif 'loaded' not in self.index.keys() or (datetime.datetime.now() - self.index['loaded']).seconds > 600:
            self.index.update(self._build_index())
        self.index.sync()
        self.favorites = self.index['favorites']

    def _build_index(self):
        # get gplay channels
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        channels, live = scraper.get_gplay_channels()
        liveglobo = scraper.get_globo_live_id()
        if liveglobo:
            liveinfo = self._get_video_info(liveglobo)
            live.update({
                'globo': {
                    'name': 'Rede Globo',
                    'logo': GLOBO_LOGO,
                    'playable': True,
                    'plot': liveinfo['program'],
                    'id': liveglobo,
                },
            })
        premiere = scraper.get_premiere_live(live['premiere']['logo'])
        sportv = scraper.get_sportv_live(live['sportvlive']['logo'])
        # add globo
        channels.update({
            'globo': ('Rede Globo', GLOBO_LOGO, None),
        })
        return {
            'index': [
                ('channels', self.plugin.get_string(30011)),
                ('live', self.plugin.get_string(30012)),
                ('favorites', self.plugin.get_string(30013)),
            ],
            'channels': channels,
            'live': live,
            'premiere': premiere,
            'sportvlive': sportv,
            'favorites': set(),
			'loaded': datetime.datetime.now()
        }

    def _build_globo(self, channel=None):
        categories, shows = scraper.get_globo_shows()
        data = { 'globo': {} }
        for cat, show_list in zip(categories, shows):
            slug = util.slugify(cat)
            data['globo'].update({slug: (cat, None)})
            data[slug] = show_list
        return data

    def _build_globosat(self, channel):
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        index = self.get_path('channels')
        channelid = [id for slug, (name, img, id) in sorted(index.items()) if channel == slug]
        shows = scraper.get_gplay_shows(channelid[0])
        data = {
            channel: dict([(showid, (name, img))
                           for showid, name, img in shows])
        }
        return data

    def _clear_index(self):
        self.index.clear()
        self.index.sync()
        self.plugin.log.debug('data cleared')

    def _get_hashes(self, video_id, resource_ids, player, auth_retry=False, player_retry=False):
        playerVersion = self.plugin.get_setting('player_version')
        video_data = self._get_video_info(video_id)
        provider = ('globo' if video_data['channel_id'] == 196
                    else self.plugin.get_setting('play_provider').lower().replace(' ', '_'))
        credentials = self.authenticate(provider, video_data['provider_id'])

        args = (video_id, '|'.join(resource_ids), playerVersion, player)
        self.plugin.log.debug('hash requested: %s' % (HASH_URL % args))
        data = scraper.get_page(HASH_URL % args, cookies=credentials)
        self.plugin.log.debug('resource ids: %s' % '|'.join(resource_ids))
        self.plugin.log.debug('return: %s' % repr(data).encode('ascii', 'replace'))
        try:
            return (data['hash'], data)
        except ValueError:
            msg = 'JSON not returned. Message returned:\n%s' % data
            self.plugin.log.error(msg)
            raise
        except KeyError:
            args = (data['http_status_code'], data['message'])
            self.plugin.log.error('request error: [%s] %s' % args)

            if data['message'] == 'Player not recognized':
                # If a 'Player not recognized' message is received, it is
                # either because the player version is not yet set, or it's
                # outdated. In either case, player version is reset and hash
                # computation retried once
                self.plugin.log.debug('reset player version')
                if not player_retry:
                    playerVersion = scraper.get_player_version()
                    self.plugin.set_setting('player_version', playerVersion)
                    self.plugin.log.debug('retrying with new player version %s' % playerVersion)
                    return self._get_hashes(video_id, resource_ids, player, auth_retry, True)

            if str(args[0]) == '403' and any(credentials.values()):
                # If a 403 is returned (authentication needed) and there is an
                # globo id, then this might be due to session expiration and a
                # retry with a blank id shall be tried
                self.plugin.log.debug('cleaning credentials')
                credentials_key = '%s_credentials' % ('globo' if 'globo' == provider else 'play')
                self.plugin.set_setting(credentials_key, '')
                if not auth_retry:
                    self.plugin.log.debug('retrying authentication')
                    return self._get_hashes(video_id, resource_ids, player, True, player_retry)
            raise Exception(data['message'])

    # @util.cacheFunction
    def _get_video_info(self, video_id):
        # get video info
        data = scraper.get_page(INFO_URL % video_id)['videos'][0]
        if 'date' not in data:
            # original date is not part of INFO_URLs metadata response
            data['date'] = util.time_format()
        if 'duration' not in data:
            data['duration'] = sum(x['resources'][0]['duration']/1000
                                   for x in data.get('children') or [data])
        return data

    def authenticate(self, provider, provider_id):
        try:
            backend = getattr(backends, provider)(self.plugin)
        except AttributeError:
            self.plugin.log.error('%s provider unavailable' % provider)
            self.plugin.notify(self.plugin.get_string(32002) % provider)
        return backend.authenticate(provider_id)

    def get_path(self, key):
        data = self.index.get(key)
        if data == None:
            method = '_build_%s' % (key if key == 'globo' else 'globosat')
            data = getattr(self, method)(key)
            self.index.update(data)
            data = self.index.get(key)
        return data

    def get_episodes(self, channel, show, page):
        # page_size = int(self.plugin.get_setting('page_size') or 10)
        self.plugin.log.debug('getting episodes for %s/%s, page %s' % (channel, show, page))
        # define scraper method
        method_strs = {
            'megapix': 'get_megapix_episodes',
			'telecine': 'get_megapix_episodes',
            'globo':'get_globo_episodes',
        }
        method = method_strs.get(channel) or 'get_gplay_episodes'
        episodes, next = getattr(scraper, method)(channel, show, page)
        return util.struct({'list': episodes, 'next': next})

    def get_videos(self, video_id):
        data = self._get_video_info(video_id)
        try:
            items = [util.struct(self._get_video_info(video['id']))
                     for video in data['children']]
        except KeyError:
            items = [util.struct(data)]
        return items

    def resolve_video_url(self, video_id):       
        use_playlist_m3u8 = self.plugin.get_setting('use_m3u8') == 'true'
        if use_playlist_m3u8:
            url = self.resolve_video_url_m3u8(video_id)
        else:
            url = self.resolve_video_url_mp4(video_id)
        return url

    def resolve_video_url_mp4(self, video_id):
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        # which index to look in the list
        heights = [360, 480, 720]
        video_res = int(self.plugin.get_setting('video_quality') or 0)
        # get video info
        data = self._get_video_info(video_id)
        self.plugin.log.debug('resolving video: %s' % video_id)
        # this method assumes there's no children
        if 'children' in data:
            raise Exception('Invalid video id: %s' % video_id)
        # build resources dict based on heights
        resources = dict((d['height'], d) for d in data['resources']
                        if 'players' in d and 'height' in d and 'desktop' in d['players'])
        # No height info, skip to m3u8
        if len(resources) == 0:
            return self.resolve_video_url_m3u8(video_id)
        # get resource based on video quality setting
        while True:
            try:
                r = resources[heights[video_res]]
                break
            except:
                video_res -= 1
        # get hashes
        hashes, data_hashes = self._get_hashes(video_id, [r['_id']], 'html5')
        signed_hashes = util.get_signed_hashes(hashes)
        query_string = re.sub(r'{{([a-z]*)}}',
                              r'%(\1)s',
                              r['query_string_template']) % {
                                'hash': signed_hashes[0],
                                'key': 'html5'
                              }
        # build resolved url
        url = '?'.join([r['url'], query_string])
        self.plugin.log.debug('video playlist url: %s' % url)
        return url
        
    def resolve_video_url_m3u8(self, video_id):
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        # get video info
        data = self._get_video_info(video_id)
        self.plugin.log.debug('resolving video: %s' % video_id)
        # this method assumes there's no children
        if 'children' in data:
            raise Exception('Invalid video id: %s' % video_id)
        
        # check if resources is empty
        if len(data['resources']) == 0:
            # get hashes
            hashes, data_hashes = self._get_hashes(video_id, [], 'html5')
            url = data_hashes['url']
            template = 'h={{hash}}&k={{key}}&a={{openClosed}}&u={{user}}'
        else:
            # find playlist in resources list
            reslist = [resource for resource in data['resources'] if 'players' in resource and 'desktop' in resource['players'] and '.m3u8' in resource['url']]
            # don't have a m3u8 video available
            if len(reslist) == 0:
                return self.resolve_video_url_mp4(video_id)
            res = reslist[0]
            url = res['url']
            # get hashes
            hashes, data_hashes = self._get_hashes(video_id, [res['_id']], 'html5')
            template = res['query_string_template']
        signed_hashes = util.get_signed_hashes(hashes)
        # resolve query string template
        query_string = re.sub(r'{{(\w*)}}', r'%(\1)s',
                              template)
        try:
            query_string = query_string % {
                'hash': signed_hashes[0],
                'key': 'html5'
            }
        except KeyError:
            # live videos
            query_string = query_string % {
                'hash': signed_hashes[0],
                'key': 'html5',
                'openClosed': 'F' if data['subscriber_only'] else 'A',
                'user': data_hashes['user'] if data['subscriber_only'] else ''
            }
        # build resolved url
        url = '?'.join([url, query_string])
        self.plugin.log.debug('video playlist url: %s' % url)
        return url

