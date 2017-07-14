# -*- coding: utf-8 -*-

from resources.lib.modules import control
from resources.lib.modules import client
import auth

GLOBOSAT_API_URL = 'https://api.vod.globosat.tv/globosatplay'
GLOBOSAT_API_AUTHORIZATION = 'token b4b4fb9581bcc0352173c23d81a26518455cc521'
GLOBOSAT_API_CHANNELS = GLOBOSAT_API_URL + '/channels.json?page=%d'
GLOBOSAT_SEARCH = 'https://globosatplay.globo.com/busca/pagina/%s.json?q=%s'
GLOBOSAT_FEATURED = 'https://api.vod.globosat.tv/globosatplay/featured.json'
GLOBOSAT_TRACKS = 'https://api.vod.globosat.tv/globosatplay/tracks.json'
GLOBOSAT_TRACKS_ITEM = 'https://api.vod.globosat.tv/globosatplay/tracks/%s.json'

artPath = control.artPath()


def get_authorized_channels():

    provider = control.setting('globosat_provider').lower().replace(' ', '_')
    username = control.setting('globosat_username')
    password = control.setting('globosat_password')

    if not username or not password or username == '' or password == '':
        return []

    authenticator = getattr(auth, provider)()
    token, sessionKey = authenticator.get_token(username, password)

    client_id = "85014160-e953-4ddb-bbce-c8271e4fde74"
    channels_url = "https://gsatmulti.globo.com/oauth/sso/login/?chave=%s&token=%s" % (client_id, token)

    channels = []

    pkgs = client.request(channels_url, headers={"Accept-Encoding": "gzip"})['pacotes']

    channel_ids = []
    for pkg in pkgs:
        for channel in pkg['canais']:
            if control.setting('show_adult') == 'false' and channel['slug'] == 'sexyhot':
                continue

            if channel['id_cms'] == 0 and channel['slug'] != 'combate' and channel['slug'] != 'sexyhot' or channel['slug'] == 'telecine-zone' :
                continue

            elif "vod" in channel['acls'] and channel['id_globo_videos'] not in channel_ids:
                channel_ids.append(channel['id_globo_videos'])
                channels.append({
                    "id": channel['id_globo_videos'],
                    # "channel_id": channel['id_globo_videos'],
                    "id_cms": channel['id_cms'],
                    "logo": channel['logo_fundo_claro'],
                    "name": channel['nome'],
                    "slug": channel['slug']
                })

    return channels


def get_channel_programs(channel_id):

    base_url = 'https://api.vod.globosat.tv/globosatplay/cards.json?channel_id=%s&page=%s'
    headers = {'Authorization': GLOBOSAT_API_AUTHORIZATION, 'Accept-Encoding': 'gzip'}

    page = 1
    url = base_url % (channel_id, page)
    result = client.request(url, headers=headers)

    next = result['next'] if 'next' in result else None
    programs_result = result['results'] or []

    while next:
        page = page + 1
        url = base_url % (channel_id, page)
        result = client.request(url, headers=headers)
        next = result['next'] if 'next' in result else None
        programs_result = programs_result + result['results']

    programs = []

    for program in programs_result:
        programs.append({
                'id': program['id_globo_videos'],
                'title': program['title'],
                'name': program['title'],
                'fanart': program['background_image_tv_cropped'],
                'poster': program['image'],
                'plot': program['description'],
                'kind': program['kind'] if 'kind' in program else None
            })

    return programs


def search(term, page=1):
    try:
        page = int(page)
    except:
        page = 1

    videos = []
    headers = {'Accept-Encoding': 'gzip'}
    data = client.request(GLOBOSAT_SEARCH % (page, term), headers=headers)
    total = data['total']
    next_page = page + 1 if len(data['videos']) < total else None

    for item in data['videos']:
        video = {
            'id': item['id'],
            'label': item['canal'] + ' - ' + item['programa'] + ' - ' + item['titulo'],
            'title': item['titulo'],
            'tvshowtitle': item['programa'],
            'studio': item['canal'],
            'plot': item['descricao'],
            'duration': sum(int(x) * 60 ** i for i, x in
                            enumerate(reversed(item['duracao'].split(':')))) if item['duracao'] else 0,
            'thumb': item['thumb_large'],
            'fanart': item['thumb_large'],
            'mediatype': 'episode',
            'brplayprovider': 'globosat'
        }

        videos.append(video)

    return videos, next_page, total


def get_featured(channel_id=None):
    headers = {
            'Accept-Encoding': 'gzip',
            'Authorization': GLOBOSAT_API_AUTHORIZATION
       }
    channel_filter = '?channel_id=%s' % channel_id if channel_id else ''
    featured_list = client.request(GLOBOSAT_FEATURED + channel_filter, headers=headers)

    results = featured_list['results']

    while featured_list['next'] is not None:
        featured_list = client.request(featured_list['next'], headers=headers)
        results += featured_list['results']

    videos = []

    for item in results:

        media = item['media']

        if media:
            video = {
                'id': item['id_globo_videos'],
                'label': media['channel']['title'] + ' - ' + item['title'] + ' - ' + media['title'],
                'title': media['title'],
                'tvshowtitle': item['title'],
                'studio': media['channel']['title'],
                'plot': media['description'],
                'tagline': item['subtitle'],
                'duration': float(media['duration_in_milliseconds']) / 1000.0,
                'logo': media['program']['logo_image'] if 'program' in media and media['program'] else item['channel']['color_logo'],
                'clearlogo': media['program']['logo_image'] if 'program' in media and media['program'] else item['channel']['color_logo'],
                'poster': media['program']['poster_image'] if 'program' in media and media['program'] else media['card_image'],
                'thumb': media['thumb_image'],
                'fanart': media['background_image_tv_cropped'] if 'program' in media and media['program'] else media['background_image'],
                'mediatype': 'episode',
                'brplayprovider': 'globosat'
            }
        else:
            video = {
                'id': item['id_globo_videos'],
                'label': item['channel']['title'] + ' - ' + item['title'],
                'title': item['title'],
                'tvshowtitle': item['title'],
                'studio': item['channel']['title'],
                'plot': item['subtitle'],
                #'tagline': item['subtitle'],
                #'duration': float(media['duration_in_milliseconds']) / 1000.0,
                #'logo': media['program']['logo_image'],
                #'clearlogo': media['program']['logo_image'],
                #'poster': media['program']['poster_image'],
                'thumb': item['background_image'],
                'fanart': item['background_image'],
                'mediatype': 'episode',
                'brplayprovider': 'globosat'
            }

        videos.append(video)

    return videos


def get_tracks(channel_id=None):
    headers = {
        'Accept-Encoding': 'gzip',
        'Authorization': GLOBOSAT_API_AUTHORIZATION
    }
    channel_filter = '?channel_id=%s' % channel_id if channel_id else ''
    tracks_response = client.request(GLOBOSAT_TRACKS + channel_filter, headers=headers)

    results = tracks_response['results']

    tracks = []

    for item in results:
        video = {
            'id': item['id'],
            'label': item['title'],
            'title': item['title'],
            'kind': item['kind']
        }

        tracks.append(video)

    return tracks


def get_track_list(id):
    headers = {
        'Accept-Encoding': 'gzip',
        'Authorization': GLOBOSAT_API_AUTHORIZATION
    }
    track_list = client.request(GLOBOSAT_TRACKS_ITEM % id, headers=headers)

    results = track_list['results']

    while track_list['next'] is not None:
        track_list = client.request(track_list['next'], headers=headers)
        results += track_list['results']

    videos = []

    for item in results:

        media = item['media']
        if media:
            video = {
                'id': item['id_globo_videos'],
                'label': media['channel']['title'] + ' - ' + media['title'],
                'title': media['title'],
                'tvshowtitle': media['program']['title'] if 'program' in media and media['program'] else None,
                'studio': media['channel']['title'],
                'plot': media['description'],
                'tagline': media['subtitle'],
                'duration': float(media['duration_in_milliseconds']) / 1000.0,
                'logo': media['program']['logo_image'] if 'program' in media and media['program'] else media['channel']['color_logo'],
                'clearlogo': media['program']['logo_image'] if 'program' in media and media['program'] else media['channel']['color_logo'],
                'poster': media['program']['poster_image'] if 'program' in media and media['program'] else media['card_image'],
                'thumb': media['thumb_image'],
                'fanart': media['background_image_tv_cropped'],
                'mediatype': 'episode',
                'brplayprovider': 'globosat'
            }
        else:
            program = item['program']
            video = {
                'id': item['id_globo_videos'],
                'label': program['title'],
                'title': program['title'],
                'tvshowtitle': program['title'],
                'studio': program['channel']['title'],
                'plot': program['description'],
                'tagline': None,
                'logo': program['logo_image'],
                'clearlogo': program['logo_image'],
                'poster': program['poster_image'],
                'thumb': None,
                'fanart': program['background_image_tv_cropped'],
                'mediatype': 'tvshow',
                'isplayable': False,
                'brplayprovider': 'globosat'
            }
        videos.append(video)

    return videos