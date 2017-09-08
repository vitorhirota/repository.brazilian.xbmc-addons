import json
import re
import sys
import urllib
import xbmc
import auth
from resources.lib.modules import hlshelper
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules.util import get_signed_hashes

import threading

PLAYER_VERSION = '1.1.23'
PLAYER_SLUG = 'ios'

HISTORY_URL = 'https://api.user.video.globo.com/watch_history/'


class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.sources = []
        self.offset = 0.0
        self.isLive = False
        self.m3u8 = None
        self.cookies = None
        self.url = None
        self.item = None
        self.stopPlayingEvent = None
        self.credentials = None
        self.program_id = None
        self.video_id = None

    def onPlayBackStopped(self):
        control.log("PLAYBACK STOPPED")

        if not self.isLive:
            total_time = self.getTotalTime()
            current_time = self.getTime()
            percentage_watched = current_time / total_time if total_time > 0 else 1.0 / 1000000.0
            fully_watched = 0.9 < percentage_watched <= 1 if percentage_watched else False
            self.save_video_progress(self.credentials, self.program_id, self.video_id, self.getTime() * 1000,
                                     fully_watched=fully_watched)

        if self.stopPlayingEvent:
            self.stopPlayingEvent.set()

    def onPlayBackEnded(self):
        control.log("PLAYBACK ENDED")

        if not self.isLive:
            total_time = self.getTotalTime()
            current_time = self.getTime()
            percentage_watched = current_time / total_time if total_time > 0 else 1.0 / 1000000.0
            fully_watched = 0.9 < percentage_watched <= 1 if percentage_watched else False
            self.save_video_progress(self.credentials, self.program_id, self.video_id, self.getTime() * 1000,
                                     fully_watched=fully_watched)

        if self.stopPlayingEvent:
            self.stopPlayingEvent.set()

    def onPlayBackStarted(self):
        control.log("PLAYBACK STARTED")
        if self.offset > 0: self.seekTime(float(self.offset))

    def play_stream(self, id, meta):

        if id == None: return

        try: meta = json.loads(meta)
        except: meta = {
            "playcount": 0,
            "overlay": 6,
            "mediatype": "video",
            "aired": None
        }

        self.isLive = False

        if 'live' in meta and meta['live'] == True:
            self.isLive = True
            info = self.__getLiveVideoInfo(id, meta['affiliate'] if 'affiliate' in meta else None)
        else:
            info = self.__getVideoInfo(id)

        title = meta['title'] if 'title' in meta else info['title']

        signed_hashes = get_signed_hashes(info['hash'])

        query_string = re.sub(r'{{(\w*)}}', r'%(\1)s', info['query_string_template'])

        query_string = query_string % {
            'hash': signed_hashes[0],
            'key': 'app',
            'openClosed': 'F',
            'user': info['user'] if info['subscriber_only'] else ''
        }

        url = '?'.join([info['url'], query_string])

        control.log("live media url: %s" % url)

        meta.update({
            "genre": info["category"],
            "plot": info["title"],
            "plotoutline": info["title"],
            "title": title
        });

        poster = meta['poster'] if 'poster' in meta else control.addonPoster()
        thumb = meta['thumb'] if 'thumb' in meta else info["thumbUri"]

        syshandle = int(sys.argv[1])

        self.offset = float(meta['milliseconds_watched']) / 1000.0 if 'milliseconds_watched' in meta else 0

        self.isLive = 'live' in meta and meta['live']

        self.url, mime_type, stopEvent = hlshelper.pick_bandwidth(url)

        if self.url is None:
            control.infoDialog(message=control.lang('34100').encode('utf-8'), icon='ERROR')
            return

        control.log("Resolved URL: %s" % repr(self.url))

        item = control.item(path=self.url)
        item.setInfo(type='video', infoLabels=meta)
        item.setArt({'icon': thumb, 'thumb': thumb, 'poster': poster, 'tvshow.poster': poster, 'season.poster': poster})
        item.setProperty('IsPlayable', 'true')

        if mime_type:
            item.setMimeType(mime_type)

        item.setContentLookup(False)

        control.resolve(syshandle, True, item)

        self.stopPlayingEvent = threading.Event()
        self.stopPlayingEvent.clear()

        self.credentials = info['credentials'] if 'credentials' in info else None
        self.program_id = info['program_id'] if 'program_id' in info else None
        self.video_id = info['id'] if 'id' in info else None

        last_time = 0.0
        while not self.stopPlayingEvent.isSet():
            if control.monitor.abortRequested():
                control.log("Abort requested")
                break
            control.log("IS PLAYING: %s" % self.isPlaying())
            if not self.isLive and self.isPlaying():
                total_time = self.getTotalTime()
                current_time = self.getTime()
                if current_time - last_time > 5 or (last_time == 0 and current_time > 1):
                    last_time = current_time
                    percentage_watched = current_time / total_time if total_time > 0 else 1.0 / 1000000.0
                    self.save_video_progress(self.credentials, self.program_id, self.video_id, current_time * 1000, fully_watched=percentage_watched>0.9 and percentage_watched<=1)
            control.sleep(1000)

        if stopEvent:
            control.log("Setting stop event for proxy player")
            stopEvent.set()

        control.log("Done playing. Quitting...")

    def __getVideoInfo(self, id):

        proxy = control.proxy_url
        proxy = None if proxy == None or proxy == '' else {
            'http': proxy,
            'https': proxy,
        }

        playlistUrl = 'http://api.globovideos.com/videos/%s/playlist'
        playlistJson = client.request(playlistUrl % id, headers={"Accept-Encoding": "gzip"})

        if not playlistJson or not 'videos' in playlistJson or len(playlistJson['videos']) == 0: #Video Not Available
            control.infoDialog(message=control.lang(34101).encode('utf-8'), sound=True, icon='ERROR')
            control.idle()
            sys.exit()
            return None
            # raise Exception("Player version not found.")

        playlistJson = playlistJson['videos'][0]

        for node in playlistJson['resources']:
            if any(PLAYER_SLUG in s for s in node['players']):
                resource = node
                break

        if resource == None:
            control.infoDialog(message=control.lang(34102).encode('utf-8'), sound=True, icon='ERROR')
            control.idle()
            sys.exit()
            return None

        #cuepoints = playlistJson['cuepoints']

        #"cuepoints": [
        #     {
        #         "type": "next_segment",
        #         "title": "",
        #         "description": "",
        #         "time": 596062
        #     },
        #     {
        #         "type": "next_segment",
        #         "title": "",
        #         "description": "",
        #         "time": 1136068
        #     },
        #     {
        #         "type": "next_segment",
        #         "title": "",
        #         "description": "",
        #         "time": 1687152
        #     },
        #     {
        #         "type": "next_segment",
        #         "title": "",
        #         "description": "",
        #         "time": 2020151
        #     }
        # ]

        resource_id = resource['_id']

        username = control.setting('globoplay_username')
        password = control.setting('globoplay_password')

        #authenticate
        credentials = auth.auth().authenticate(username, password)
        hashUrl = 'http://security.video.globo.com/videos/%s/hash?resource_id=%s&version=%s&player=%s' % (id, resource_id, PLAYER_VERSION, PLAYER_SLUG)
        hashJson = client.request(hashUrl, cookie=credentials, mobile=True, headers={"Accept-Encoding": "gzip"}, proxy=proxy)

        return {
            "id": playlistJson["id"],
            "title": playlistJson["title"],
            "duration": int(resource["duration"]),
            "program": playlistJson["program"],
            "program_id": playlistJson["program_id"],
            "provider_id": playlistJson["provider_id"],
            "channel": playlistJson["channel"],
            "channel_id": playlistJson["channel_id"],
            "category": playlistJson["category"],
            "subscriber_only": playlistJson["subscriber_only"],
            "exhibited_at": playlistJson["exhibited_at"],
            "player": PLAYER_SLUG,
            "url": resource["url"],
            "query_string_template": resource["query_string_template"],
            "thumbUri": None,
            "hash": hashJson["hash"],
            "user": None,
            "credentials": credentials
        }

    def     __getLiveVideoInfo(self, id, geolocation):

        username = control.setting('globoplay_username')
        password = control.setting('globoplay_password')

        # authenticateurl
        credentials = auth.auth().authenticate(username, password)

        affiliate_temp = control.setting('globo_affiliate')

        # In settings.xml - globo_affiliate
        # 0 = All
        # 1 = Rio de Janeiro
        # 2 = Sao Paulo
        # 3 = Brasilia
        # 4 = Belo Horizonte
        # 5 = Recife
        if affiliate_temp == "0":
            affiliate = "All"
        elif affiliate_temp == "2":
            affiliate = "Sao Paulo"
        elif affiliate_temp == "3":
            affiliate = "Brasilia"
        elif affiliate_temp == "4":
            affiliate = "Belo Horizonte"
        elif affiliate_temp == "5":
            affiliate = "Recife"
        else:
            affiliate = "Rio de Janeiro"

        if affiliate == "All" and geolocation != None:
            pass
        elif affiliate == "Sao Paulo":
            geolocation = 'lat=-23.5505&long=-46.6333'
        elif affiliate == 'Brasilia':
            geolocation = 'lat=-15.7942&long=-47.8825'
        elif affiliate == 'Belo Horizonte':
            geolocation = 'lat=-19.9245&long=-43.9352'
        elif affiliate == "Recife":
            geolocation = 'lat=-8.0476&long=-34.8770'
        else: #Rio de Janeiro
            geolocation = 'lat=-22.900&long=-43.172'

        post_data = "%s&player=%s&version=%s" % (geolocation, PLAYER_SLUG, PLAYER_VERSION)

        #4452349
        hashUrl = 'http://security.video.globo.com/videos/%s/hash' % id
        hashJson = client.request(hashUrl, error=True, cookie=credentials, mobile=True, headers={
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Globo Play/0 (iPhone)"
        }, post=post_data)

        return {
            "id": "-1",
            "title": hashJson["name"],
            # "program": playlistJson["program"],
            # "program_id": playlistJson["program_id"],
            # "provider_id": playlistJson["provider_id"],
            # "channel": playlistJson["channel"],
            # "channel_id": playlistJson["channel_id"],
            "category": 'Live',
            # "subscriber_only": playlistJson["subscriber_only"],
            "subscriber_only": 'true',
            # "exhibited_at": playlistJson["exhibited_at"],
            "player": PLAYER_SLUG,
            "url": hashJson["url"],
            "query_string_template": "h={{hash}}&k={{key}}&a={{openClosed}}&u={{user}}",
            "thumbUri": hashJson["thumbUri"],
            "hash": hashJson["hash"],
            "user": hashJson["user"],
            "credentials": credentials
        }

    def save_video_progress(self, credentials, program_id, video_id, milliseconds_watched, fully_watched=False):

        post_data = {
            'resource_id': video_id,
            'milliseconds_watched': int(round(milliseconds_watched)),
            'program_id': program_id,
            'fully_watched': fully_watched
        }

        control.log("--- SAVE WATCH HISTORY --- %s" % repr(post_data))

        post_data = urllib.urlencode(post_data)

        client.request(HISTORY_URL, error=True, cookie=credentials, mobile=True, headers={
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Globo Play/0 (iPhone)"
        }, post=post_data)