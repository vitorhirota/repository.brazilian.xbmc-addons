from BeautifulSoup import BeautifulSoup as bs
import json
import re
import requests

import util

# url masks
BASE_URL = 'http://%s.globo.com'

GLOBOPLAY_URL = 'https://api.globoplay.com.br'
GLOBOPLAY_APIKEY = '***REMOVED***'
GLOBOPLAY_CATEGORIAS = GLOBOPLAY_URL + '/v1/categories/?api_key=' + GLOBOPLAY_APIKEY
#GLOBOPLAY_EPISODIOS = GLOBOPLAY_URL + '/v2/programs/%d?api_key=' + GLOBOPLAY_APIKEY
GLOBOPLAT_DAYS = GLOBOPLAY_URL + '/v1/programs/%d/videos/days?api_key=' + GLOBOPLAY_APIKEY
GLOBOPLAY_VIDEOS = GLOBOPLAY_URL + '/v1/programs/%d/videos?day=%s&order=asc&page=%d&api_key=' + GLOBOPLAY_APIKEY

GLOBOPLAY_LIVE = 'http://s.glbimg.com/vi/p3/restrictions.js'

GLOBOSAT_URL = BASE_URL % 'globosatplay'
GLOBOSAT_SHOW_URL = GLOBOSAT_URL + '/%s'
GLOBOSAT_LIVE_JSON = GLOBOSAT_URL + '/xhr/transmissoes/ao-vivo.json'
GLOBOSAT_EPS_JSON = GLOBOSAT_SHOW_URL + '/videos/recentes.json?quantidade=15&pagina=%d'
GLOBOSAT_SEASON_JSON = GLOBOSAT_SHOW_URL + '/temporada/%d/episodios.json'

PREMIERE_LIVE_JSON = GLOBOSAT_URL + '/premierefc/ao-vivo/add-on/jogos-ao-vivo/%s.json'

EPSTHUMB_URL = 'http://s01.video.glbimg.com/x720/%s.jpg'

# RAIL_URL = SHOW_URL + '/_/trilhos/%(rail)s/page/%(page)s/'
INFO_URL = 'http://api.globovideos.com/videos/%s/playlist'
LOGIN_URL = 'https://login.globo.com/login/151?tam=widget'
JSAPI_URL = 'http://s.videos.globo.com/p2/j/api.min.js'


# @util.cacheFunction
def get_page(url, **kwargs):
    '''
        Helper for requests get, automatically returning a json object if
        applicable or regular text otherwise.
    '''
    r = requests.get(url, **kwargs)
    if r.status_code != 200:
        r.raise_for_status()
    return ('application/json' in r.headers.get('content-type')
            and json.loads(r.text, object_hook=lambda x: dict((str(k), v) for k, v in x.items()))
            or r.text)

def get_globo_live_id():
    req = get_page(GLOBOPLAY_LIVE)
    rexp = r'WM\.Player3\.ID_MOBILE_WHITELIST=\[([\d]+)[,\d]*\]'
    liveIds = re.findall(rexp, req)
    try:
        return liveIds[0]
    except:
        return false

def get_player_version():
    req = get_page(JSAPI_URL)
    rexp = r'playerVersion="([\d\.]+)"'
    playerVersion = re.findall(rexp, req)
    try:
        return playerVersion[0]
    except:
        raise Exception("Player version not found.")


# @util.cacheFunction
def get_gplay_channels():
    soup = bs(get_page(GLOBOSAT_URL))
    # get lists
    # uls = soup.find('ul', attrs={'class': 'lista-canais'}).findAll('li')
    # uls = soup.find('ul', attrs={'id': 'mobile-submenu-canais-on-demand'}).findAll('li')[1:]
    channels, live, dummy = soup.findAll('ul', attrs={'class': 'submenu-desktop'})
    # get children tags and filter as imgs
    channels = dict([(util.slugify(img['alt']),
                       (img['alt'],
                        img['src'].replace(img['src'][7:img['src'].index('=/')+2], '')))
                       for img in channels.findChildren()[2::3]])
    # build live data
    live = dict([(util.slugify(img['alt']), {
                'name': img['alt'],
                'logo': json['canal_logotipo'],
                'playable': json['status'] == 'ativa',
                'plot': ', '.join(reversed(json['programacao'].values())) if json['programacao'] != None else '',
                'id': json['midia']['id_midia'],
            }) for img, json in zip(live.findChildren()[2::3],
                                    get_page(GLOBOSAT_LIVE_JSON))])

    return (channels, live)


def get_premiere_live(logo):
    #provider_id is hardcoded right now. 
    provider_id = '520142353f8adb4c90000008'
    live = dict([(util.slugify(json['time_mandante']['sigla'] + 'x' + json['time_visitante']['sigla']), {
                'name': json['time_mandante']['sigla'] + ' x ' + json['time_visitante']['sigla'],
                'logo': logo,
                'playable': True,
                'plot': json['campeonato'] + ': ' + json['time_mandante']['nome'] + ' x ' + json['time_visitante']['nome'] + ' (' + json['estadio'] + '). ' + json['data'],
                'id': json['id_midia'],
            }) for json in get_page(PREMIERE_LIVE_JSON % provider_id)['jogos']])
    return live

def get_globo_shows():
    dic = get_page(GLOBOPLAY_CATEGORIAS)['categories']
    categories = [json['title'] for json in dic]
    shows = [dict([(j['id'], (
                    j['name'],
                    j['thumb'])) for j in json['programs']
            ]) for json in dic]
    return (categories, shows)

def get_gplay_shows(channel):
    soup = bs(get_page(GLOBOSAT_SHOW_URL % channel))
    search_strs = {
        'megapix':'submenu-generos',
        'combate':'submenu-competicoes',
        'telecine':'submenu-generos',
    }
    try:
        search = search_strs[channel]
    except:
        search = 'mobile-submenu-programas'
    shows = soup.find('ul', attrs={'id':search }).findAll('a')[1:]
    return [(a['href'], a.text, None) for a in shows]

def get_globo_episodes(channel, show, page):
    videos = []
    properties = ('id', 'title', 'plot', 'duration', 'date')
    prop_data = ('id', 'title', 'description', 'duration', 'exhibited')
    days = get_page(GLOBOPLAT_DAYS % int(show))['days']
    video_page_size = 10
    size_videos = 10
    page_num = 1
    while size_videos >= video_page_size:
        try:
            data = get_page(GLOBOPLAY_VIDEOS % (int(show), days[page-1], page_num))
            size_videos = len(data['videos'])
            for item in data['videos']:
                video = util.struct(dict(zip(properties,
                                            [item.get(p) for p in prop_data])))
                # update attrs
                video.date = util.time_format(video.date, '%Y-%m-%d')
                video.duration = sum(int(x) * 60 ** i for i, x in
                                    enumerate(reversed(video.duration.split(':'))))
                # video.duration = video.duration.split(':')[0]
                video.thumb = EPSTHUMB_URL % video.id
                # self.cache.set('video|%s' % video.id, repr(video))
                videos.append(video)
            page_num += 1
        except:
            break
    page = (page+1 if page < len(days) else None)
    return videos, page

def get_gplay_episodes(channel, show, page):
    videos = []
    properties = ('id', 'title', 'plot', 'duration', 'date', 'episode', 'season', 'mpaa', 'tvshowtitle')
    prop_data = ('id', 'titulo', 'descricao', 'duracao_original', 'data_exibicao', 'episodio', 'temporada', 'classificacao_indicativa', 'programa')

    data = get_page(GLOBOSAT_EPS_JSON % ('%s/%s' % (channel, show), page))

    for item in data['resultado']:
        video = util.struct(dict(zip(properties,
                                     [item.get(p) for p in prop_data])))
        # update attrs
        video.date = util.time_format(video.date[:10], '%Y-%m-%d')
        video.mpaa = util.getMPAAFromCI(video.mpaa)
        video.tvshowtitle = video.tvshowtitle['titulo']
        video.duration = int(video.duration/1000)
        video.thumb = EPSTHUMB_URL % video.id
        # self.cache.set('video|%s' % video.id, repr(video))
        videos.append(video)
    page = (page+1 if page < data['total_paginas'] else None)
    return videos, page


def get_megapix_episodes(channel, show, page):
    page_size = 20
    MEGAPIX_EPS_JSON = 'http://globosatplay.globo.com/%s/generos/%s/videos/pagina/%s.json'
    videos = []
    properties = ('id', 'title', 'icon', 'plot', 'duration', 'date')
    prop_data = ('id', 'titulo', 'poster')

    data = get_page( MEGAPIX_EPS_JSON % (channel, show, page) )

    for item in data:
        video = util.struct(dict(zip(properties,
                                     [item.get(p) for p in prop_data])))
        # update attrs
        video.date = '2014-01-01'
        # video.duration = int(video.duration/1000)
        video.thumb = EPSTHUMB_URL % video.id
        # self.cache.set('video|%s' % video.id, repr(video))
        videos.append(video)
    page = (page+1 if len(videos) == page_size else None)
    return videos, page
