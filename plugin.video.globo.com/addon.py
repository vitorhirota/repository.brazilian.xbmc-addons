# -*- coding: UTF-8 -*-
'''
Globo plugin for XBMC


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
from resources.lib import globo
# from resources.lib import globotv, globosat
from xbmcswift2 import Plugin, xbmc
from resources.lib import util

# xbmcswift2 patches
# to-be removed once it's fixed in the mainstream
from resources.lib import swift_patch
swift_patch.patch()

# datetime
from datetime import datetime
cache = util.Cache("Globosat", 0.05)
cache.dbg = True
plugin = Plugin()
api = globo.GloboApi(plugin, cache)


@plugin.route('/')
def index():
    return [{
        'label': name,
        'path': plugin.url_for(slug)
    } for slug, name in api.get_path('index')]


@plugin.route('/favorites')
def favorites():
    return []


@plugin.route('/live')
def live():
    index = api.get_path('live')
    return [{
        'label': channel.name,
        'icon': channel.logo,
        'thumbnail': channel.thumb,
        'path': plugin.url_for('play_live', channel=channel.slug),
        'is_playable': True,
        'info': {
            'plot': channel.plot,
        },
    } for channel in map(util.struct, index)]


@plugin.route('/channels')
def channels():
    index = api.get_path('channels')
    return [{
        'label': name,
        'path': plugin.url_for('list_shows', channel=slug),
        'thumbnail': img
    } for slug, name, img in index]


@plugin.route('/<channel>', name='list_shows')
@plugin.route('/globo/<category>', name='list_globo_categories', options={'channel': 'globo'})
def list_shows(channel, category=None):
    # import pydevd; pydevd.settrace()
    index = api.get_path(category or channel)
    return [{
        'label': name,
        'path': (plugin.url_for('list_globo_categories', category=slug) if channel == 'globo' and not category else
                 plugin.url_for('list_episodes', channel=channel, show=slug, page=1)),
        'thumbnail': img
    } for slug, name, img in index]


@plugin.route('/<channel>/<show>/page/<page>')
def list_episodes(channel, show, page=1):
    videos = api.get_episodes(channel, show, int(page))
    items = [{
        'label': video.title,
        'icon': video.thumb,
        'thumbnail': video.thumb,
        'path': plugin.url_for('play', video_id=video.id),
        'is_playable': True,
        'info': {
            'date': video.date.replace('/', '.'),
            # 'duration': video.duration,
            'plot': video.plot,
            'plotoutline': video.plot,
            'title': video.title,
        },
        'stream_info': {
            'duration': video.duration,
        }
    } for video in videos.list]
    if videos.next:
        items.append({
            'label': plugin.get_string(33001),
            'path': plugin.url_for('list_episodes',
                                   channel=channel, show=show,
                                   page=str(videos.next))
        })
    return items


@plugin.route('/play/<video_id>')
def play(video_id):
    videos = api.get_videos(video_id)
    items = [{
        'label': video.title,
        'label2': video.subtitle,
        'icon': video.thumb,
        'thumbnail': video.thumb,
        'path': plugin.url_for('play', video_id=str(video.id)),
        'is_playable': True,
        'info': {
            'date': video.date,
            'plot': video.plot,
            'plotoutline': video.plot,
            'title': video.title,
            'id': video.id
        },
        'stream_info': {
            'duration': video.duration,
        }
    } for video in videos]

    if len(items) > 1:
        plugin.log.debug('playlist found, adding %s items: %s' %
                         (len(items), [it['info']['id'] for it in items]))
        xbmc.PlayList(1).clear()
        plugin.add_to_playlist(items)

    item = items[0]
    _id = item['info']['id']
    plugin.log.debug('setting resolved url for first item %s' % _id)
    try:
        item['path'] = api.resolve_video_url(_id)
        item['info']['date'] = str(datetime.now().date())
        plugin.set_resolved_url(item, 'video/mp4')
    except Exception as e:
        plugin.notify(str(e))


@plugin.route('/live/<channel>')
def play_live(channel):
    print channel
    return
    # videos = api.get_videos(vid)
    # items = [{
    #     'label': video.title,
    #     'label2': video.subtitle,
    #     'icon': video.thumb,
    #     'thumbnail': video.thumb,
    #     'path': plugin.url_for('play', vid=str(video.id)),  # video.url,
    #     'is_playable': True,
    #     'info': {
    #         'date': video.date,
    #         'plot': video.plot,
    #         'plotoutline': video.plot,
    #         'title': video.title,
    #         'id': video.id
    #     },
    #     'stream_info': {
    #         'duration': video.duration,
    #     }
    # } for video in videos]

    # if len(items) > 1:
    #     plugin.log.debug('playlist found, adding %s items: %s' %
    #                      (len(items), [i['info']['id'] for i in items]))
    #     xbmc.PlayList(1).clear()
    #     plugin.add_to_playlist(items)

    # item = items[0]
    # _id = item['info']['id']
    # plugin.log.debug('setting resolved url for first item %s' % _id)
    # try:
    #     item['path'] = api.resolve_video_url(_id)
    #     plugin.set_resolved_url(item, 'video/mp4')
    # except Exception as e:
    #     # plugin.notify(plugin.get_string(32001))
    #     plugin.notify(e.message)


if __name__ == '__main__':
    plugin.run()
