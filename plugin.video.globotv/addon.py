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
from resources.lib import globo
from xbmcswift2 import Plugin, xbmc
try:
    import StorageServer
except:
    import test.storageserverdummy as StorageServer

# xbmcswift2 patches
# to-be removed once it's fixed in the mainstream
from resources.lib import swift_patch
swift_patch.patch()

cache = StorageServer.StorageServer("Globosat", 12)
plugin = Plugin()
api = globo.GloboApi(plugin, cache)


@plugin.route('/')
def index():
    # items = [
    #     {'label': 'Canais'},
    #     {'label': 'Categorias'},
    #     {'label': 'Globo+'},
    #     {'label': 'Ao vivo'},
    #     {'label': 'Buscar'}
    # ]

    categories = cache.cacheFunction(api.get_shows_by_categories)
    items = [{
        'label': '%s (%s shows)' % (category['title'], len(category['shows'])),
        'path': plugin.url_for('list_shows', slug=slug)
    } for slug, category in categories.items()]
    # return items
    return sorted(items, key=lambda item: item['label'])


@plugin.route('/play/<vid>')
def play(vid):
    videos = api.get_videos(vid)
    items = [{
        'label': video.title,
        'label2': video.subtitle,
        'icon': video.thumb,
        'thumbnail': video.thumb,
        'path': plugin.url_for('play', vid=str(video.id)),  # video.url,
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
                         (len(items), [i['info']['id'] for i in items]))
        xbmc.PlayList(1).clear()
        plugin.add_to_playlist(items)

    item = items[0]
    _id = item['info']['id']
    plugin.log.debug('setting resolved url for first item %s' % _id)
    # from pysrc import pydevd; pydevd.settrace()
    try:
        item['path'] = api.resolve_video_url(_id)
        plugin.set_resolved_url(item, 'video/mp4')
    except Exception as e:
        # plugin.notify(plugin.get_string(31001))
        plugin.notify(e.message)


@plugin.route('/category/<slug>')
def list_shows(slug):
    shows = cache.cacheFunction(api.get_shows_by_categories)[slug]['shows']
    # offer = [{'label': u'Últimos vídeos',
    #           'path': plugin.url_for('list_offer_videos',
    #                                  **{'slug': slug, 'filter': 'last'})},
    #          {'label': u'Mais vistos',
    #           'path': plugin.url_for('list_offer_videos',
    #                                  **{'slug': slug, 'filter': 'popular'})}]
    items = [{
        'label': name,
        'icon': icon,
        'path': plugin.url_for('list_rails',
                               **dict(zip(('channel', 'show'),
                                          filter(None, uri.split('/')))))
    } for uri, name, icon in shows]
    # return offer + sorted(items, key=lambda item: item['label'])
    return sorted(items, key=lambda item: item['label'])


@plugin.route('/<channel>/<show>')
def list_rails(channel, show):
    rails = cache.cacheFunction(api.get_rails, plugin.request.path)
    items = [{
        'label': ' '.join(x.capitalize() for x in name.split(' ')),
        'path': plugin.url_for('list_rail_videos',
                               channel=channel, show=show, rail=rail)
    } for rail, name in rails]
    return items


@plugin.route('/offer/<slug>/<filter>')
def list_offer_videos(slug, filter):
    pass


@plugin.route('/<channel>/<show>/<rail>')
@plugin.route('/<channel>/<show>/<rail>/page/<page>',
              name='list_rail_videos_page')
def list_rail_videos(channel, show, rail, page=1):
    kwargs = {
        'uri': '/'.join(plugin.request.path.split('/')[:3]),
        'rail': rail,
        'page': int(page)
    }
    videos = api.get_rail_videos(**kwargs)
    items = [{
        'label': video.title,
        'icon': video.thumb,
        'thumbnail': video.thumb,
        'path': plugin.url_for('play', vid=video.id),
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
    next = []
    if videos.next:
        next.append({
            'label': plugin.get_string(32001),
            'path': plugin.url_for('list_rail_videos_page',
                                   channel=channel, show=show,
                                   rail=rail, page=str(videos.next))
        })
    return items + next


if __name__ == '__main__':
    plugin.run()
