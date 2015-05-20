from BeautifulSoup import BeautifulSoup as bs
import json
import re
import requests

import util

# url masks
BASE_URL = 'http://%s.globo.com'

GLOBOTV_URL = BASE_URL % 'globotv'
GLOBOTV_MAIS_URL = GLOBOTV_URL + '/mais/'
GLOBOTV_EPS_JSON = GLOBOTV_URL + '/rede-globo/%s/integras/recentes/%d.json'
GLOBOTV_PROGIMG_URL = 'http://s.glbimg.com/vi/mk/program/%s/logotipo/2/149x84.png'

GLOBOSAT_URL = BASE_URL % 'globosatplay'
GLOBOSAT_SHOW_URL = GLOBOSAT_URL + '/%s'
GLOBOSAT_LIVE_JSON = GLOBOSAT_URL + '/xhr/transmissoes/ao-vivo.json'
GLOBOSAT_EPS_JSON = GLOBOSAT_SHOW_URL + '/videos/recentes.json?quantidade=15&pagina=%d'
GLOBOSAT_SEASON_JSON = GLOBOSAT_SHOW_URL + '/temporada/%d/episodios.json'

EPSTHUMB_URL = 'http://s01.video.glbimg.com/x360/%s.jpg'
# RAIL_URL = SHOW_URL + '/_/trilhos/%(rail)s/page/%(page)s/'
INFO_URL = 'http://api.globovideos.com/videos/%s/playlist'
HASH_URL = ('http://security.video.globo.com/videos/%s/hash?'
            + 'resource_id=%s&version=%s&player=flash')
LOGIN_URL = 'https://login.globo.com/login/151?tam=widget'
JSAPI_URL = 'http://s.videos.globo.com/p2/j/api.min.js'


# @util.cacheFunction
def get_page(url, **kwargs):
    '''
        Helper for requests get, automatically returning a json object if
        applicable or regular text otherwise.
    '''
    r = requests.get(url, **kwargs)
    return ('application/json' in r.headers.get('content-type')
            and json.loads(r.text, object_hook=lambda x: dict((str(k), v) for k, v in x.items()))
            or r.text)

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
    channels, live = soup.findAll('ul', attrs={'class': 'submenu-desktop'})
    # get children tags and filter as imgs
    channels = dict([(util.slugify(img['alt']),
                       (img['alt'],
                        img['src'].replace(img['src'][7:img['src'].index('=/')+2], '')))
                       for img in channels.findChildren()[2::3]])
    # build live data
    live = dict([(util.slugify(img['alt']), {
                'name': img['alt'],
                'logo': json['canal_logotipo'],
                # 'plot': ', '.join(reversed(json['programacao'].values())),
                # some items have a null value for programacao
                'plot': '',
                'id': json['midia']['id_midia'],
            }) for img, json in zip(live.findChildren()[2::3],
                                    get_page(GLOBOSAT_LIVE_JSON))])

    return (channels, live)


def get_globo_shows():
    soup = bs(get_page(GLOBOTV_MAIS_URL))
    content = soup.findAll('div', attrs={'class': re.compile('trilho-tag')})
    categories = [c.find('h2').text for c in content]
    shows = [dict([(util.slugify(img['alt']),
                    (img['alt'],
                     img['data-src'].replace(img['data-src'][7:img['data-src'].index('=/')+2], '')))
                    for img in c.findAll('img') if '=/' in img['data-src']])
             for c in content]
    return (categories, shows)

def get_gplay_shows(channel):
    soup = bs(get_page(GLOBOSAT_SHOW_URL % channel))
    search_strs = {
        'megapix':'submenu-generos',
        'combate':'submenu-competicoes',
    }
    try:
        search = search_strs[channel]
    except:
        search = 'mobile-submenu-programas'
    shows = soup.find('ul', attrs={'id':search }).findAll('a')[1:]
    return [(a['href'], a.text, None) for a in shows]


def get_globo_episodes(channel, show, page):
    # page_size = 10
    videos = []
    properties = ('id', 'title', 'plot', 'duration', 'date')
    prop_data = ('id', 'titulo', 'descricao', 'duracao', 'exibicao')

    data = get_page(GLOBOTV_EPS_JSON % (show, page))
    for item in data:
        try:
            video = util.struct(dict(zip(properties,
                                         [item.get(p) for p in prop_data])))
            # update attrs
            video.date = util.time_format(video.date, '%d/%m/%Y')
            video.duration = sum(int(x) * 60 ** i for i, x in
                                 enumerate(reversed(video.duration.split(':'))))
            # video.duration = video.duration.split(':')[0]
            video.thumb = EPSTHUMB_URL % video.id
            # self.cache.set('video|%s' % video.id, repr(video))
            videos.append(video)
        except:
            break
    page = (page+1 if len(data) == 10 else None)
    return videos, page

def get_gplay_episodes(channel, show, page):
    # page_size = 15
    # import pydevd; pydevd.settrace()
    videos = []
    properties = ('id', 'title', 'plot', 'duration', 'date')
    prop_data = ('id', 'titulo', 'descricao', 'duracao_original', 'data_exibicao')

    data = get_page(GLOBOSAT_EPS_JSON % ('%s/%s' % (channel, show), page))

    for item in data['resultado']:
        video = util.struct(dict(zip(properties,
                                     [item.get(p) for p in prop_data])))
        # update attrs
        video.date = util.time_format(video.date[:10], '%Y-%m-%d')
        video.duration = int(video.duration/1000)
        video.thumb = EPSTHUMB_URL % video.id
        # self.cache.set('video|%s' % video.id, repr(video))
        videos.append(video)
    page = (page+1 if page < data['total_paginas'] else None)
    return videos, page


def get_megapix_episodes(channel, show, page):
    # page_size = 15
    # import pydevd; pydevd.settrace()
    # 'http://globosatplay.globo.com/megapix/generos/comedia/videos/pagina/1.json'
    MEGAPIX_EPS_JSON = 'http://globosatplay.globo.com/%s/generos/%s/videos/pagina/%s.json'
    videos = []
    properties = ('id', 'title', 'plot', 'duration', 'date')
    prop_data = ('id', 'titulo')

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
    page = (page+1 if page < 1 else None)
    return videos, page
