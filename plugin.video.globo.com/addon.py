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
from xbmcswift2 import actions
from xbmcswift2 import Plugin
from xbmcswift2 import xbmc

from resources.lib import globo
from resources.lib import util

plugin = Plugin()
api = globo.GloboApi(plugin)

# background views
@plugin.route('/clear_index')
def clear_index():
    api._clear_index()
    plugin.notify(plugin.get_string(32004), image=None)

@plugin.route('/favorites/del/<channel>/<show>')
def add_show_to_favs(channel, show):
    # this is a background view
    plugin.log.debug('adding (%s, %s) to favorites' % (channel, show))
    try:
        api.favorites.add((channel, show))
        # show_name =
        plugin.notify('[%s] %s added to favorites.' % (channel, show), image=None)
    except AttributeError as e:
        plugin.log.error(e)
        plugin.notify('Error while adding to favorites. You might need to '
                      'clear the addon data in the addon settings',
                      delay=7500)

@plugin.route('/favorites/add/<channel>/<show>')
def del_show_from_favs(channel, show):
    plugin.log.debug('removing (%s, %s) to favorites' % (channel, show))
    try:
        api.favorites.remove((channel, show))
        # show_name =
        plugin.notify('[%s] %s removed from favorites.' % (channel, show), image=None)
    except AttributeError as e:
        plugin.log.error(e)


# context menu helpers
def make_favorite_ctx(channel, show):
    label = 'Add show to add-on favorites'
    new_url = plugin.url_for('add_show_to_favs', channel=channel, show=show)
    return (label, actions.background(new_url))

def make_remove_favorite_ctx(channel, show):
    label = 'Remove show from favorites'
    new_url = plugin.url_for('del_show_from_favs', channel=channel, show=show)
    return (label, actions.background(new_url))


@plugin.route('/')
def index():
    try:
        return [{
            'label': name,
            'path': plugin.url_for(slug)
        } for slug, name in api.get_path('index')]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/favorites')
def favorites():
    try:
        index = api.get_path('channels')
        favorites = api.get_path('favorites')
        return [{
            'label': '[%s] %s' % ((index.get(channel) or index.get('globo'))[0],
                                  api.get_path(channel)[slug][0]),
            'path': plugin.url_for('list_episodes',
                                   channel=(channel if index.get(channel) else 'globo'),
                                   show=slug,
                                   page=1),
            'thumbnail': api.get_path(channel)[slug][1],
            'context_menu': [
                make_remove_favorite_ctx(channel, slug),
            ],
        } for channel, slug in sorted(favorites)]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/premiere')
def premiere():
    try:
        #plugin.set_content('LiveTV')
        index = api.get_path('premiere')
        return [{
            'label': data['name'],
            'path': plugin.url_for('play_premiere_live', channel=slug),
            'thumbnail': data['logo'],
            'is_playable': data['playable'],
            'info': {
                'plot': data['plot'],
            },
        } for slug, data in sorted(index.items())]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/sportvlive')
def sportvlive():
    try:
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        #plugin.set_content('LiveTV')
        index = api.get_path('sportvlive')
        return [{
            'label': data['name'],
            'path': plugin.url_for('play_sportv_live', channel=slug),
            'thumbnail': data['logo'],
            'is_playable': data['playable'],
            'info': {
                'plot': data['plot'],
            },
        } for slug, data in sorted(index.items())]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/live')
def live():
    try:
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        #plugin.set_content('LiveTV')
        index = api.get_path('live')
        return [{
            'label': data['name'],
            'path': plugin.url_for('play_live', channel=slug) if slug not in ['premiere', 'sportvlive'] else plugin.url_for(slug),
            'thumbnail': data['logo'],
            'is_playable': slug not in ['premiere', 'sportvlive'] and data['playable'],
            'info': {
                'plot': data['plot'],
            },
        } for slug, data in sorted(index.items())]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/channels')
def channels():
    try:
        index = api.get_path('channels')
        return [{
            'label': name,
            'path': plugin.url_for('list_shows', channel=slug),
            'thumbnail': img
        } for slug, (name, img, channelid) in sorted(index.items())]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/<channel>', name='list_shows')
@plugin.route('/globo/<category>', name='list_globo_categories', options={'channel': 'globo'})
def list_shows(channel, category=None):
    try:
        #import rpdb2; rpdb2.start_embedded_debugger('pw')
        plugin.set_content('tvshows')
        index = api.get_path(category or channel)
        return [{
            'label': name,
            'path': (plugin.url_for('list_globo_categories', category=slug) if channel == 'globo' and not category else
                     plugin.url_for('list_episodes', channel=channel, show=slug, page=1)),
            'thumbnail': img,
            'context_menu': [
                make_favorite_ctx(category or channel, slug),
            ],
        } for slug, (name, img) in sorted(index.items())]
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

@plugin.route('/<channel>/<show>/page/<page>')
@plugin.route('/globo/<show>/page/<page>', name='list_globo_episodes', options={'channel': 'globo'})
def list_episodes(channel, show, page=1):
    #import rpdb2; rpdb2.start_embedded_debugger('pw')
    try:
        content_strs = {
            'megapix':'movies',
            'telecine':'movies',
        }
        try:
            content = content_strs[channel]
        except:
            content = 'episodes'
        plugin.set_content(content)
        videos = api.get_episodes(channel, show, int(page))
        items = [{
            'label': video.title,
            'icon': video.thumb,
            'thumbnail': video.thumb,
            'path': plugin.url_for('play', video_id=video.id),
            'is_playable': True,
            'info': {
                'date': video.date.replace('/', '.'),
                'duration': video.duration,
                'plot': video.plot,
                'plotoutline': video.plot,
                'title': video.title,
                'originaltitle': video.title,
                'mpaa': video.mpaa,
                'episode': video.episode,
                'season': video.season,
                'tvshowtitle': video.tvshowtitle,
                'aired': video.date.replace('/', '-'),
            },
            'stream_info': {
                'duration': video.duration,
            }
        } for video in videos.list]
        if videos.next:
            items.append({
                'label': plugin.get_string(33001) if channel <> 'globo' else plugin.get_string(33002),
                'path': plugin.url_for('list_episodes',
                                       channel=channel, show=show,
                                       page=str(videos.next))
            })
        return items
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)

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
        plugin.set_resolved_url(item, 'video/mp4')
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)


@plugin.route('/live/<channel>')
@plugin.route('/premiere/<channel>', name='play_premiere_live', options={'index': 'premiere'})
@plugin.route('/sportvlive/<channel>', name='play_sportv_live', options={'index': 'sportvlive'})
def play_live(channel, index='live'):
    #import rpdb2; rpdb2.start_embedded_debugger('pw')
    util.clear_cookies()
    video_index = api.get_path(index)[channel]
    video_id = video_index['id']
    video_info = api.get_videos(video_id)[0]
    plugin.log.debug('setting live url for %s' % video_id)
    try:
        item = {
            'label': video_index['name'],
            'thumbnail': video_index['logo'],
            # Forces URL Resolution as M3U8 for Live streams
            'path': api.resolve_video_url_m3u8(video_id),
            'is_playable': True,
            'info': {
                'date': video_info.date,
                'plot': video_index['plot'],
                'title': video_index['name'],
                'id': video_id
            },
        }
        plugin.set_resolved_url(item, 'video/mp4')
    except Exception as e:
        plugin.log.error(e, exc_info=1)
        plugin.notify(plugin.get_string(32003) % e.message)


if __name__ == '__main__':
    plugin.run()
