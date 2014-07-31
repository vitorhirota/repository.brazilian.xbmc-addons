# -*- coding: UTF-8 -*-
'''
Backend providers for Globo.tv and Globosat Play


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
import re
import requests
import urlparse

class Backends(object):
    ENDPOINT_URL = None

    def authenticate(self):
        raise Exception('Not implemented.')

    def debug(msg):
        self.plugin.log.debug('[%s] %s' % (self.__class__.__name__, msg))

    def notify(string_id):
        self.plugin.notify('[%s] %s' % (self.__class__.__name__,
                                        self.plugin.get_string(string_id)))


class globo(Backends):
    ENDPOINT_URL = 'https://login.globo.com/login/151?tam=widget'

    def __init__(self, plugin):
        self.plugin = plugin
        self.glbid = self.plugin.get_setting('glbid')
        self.username = self.plugin.get_setting('globo_username')
        self.password = self.plugin.get_setting('globo_password')

    def authenticate(self):
        if not self.glbid and (self.username and self.password):
            payload = {
                'botaoacessar': 'acessar',
                'login-passaporte': self.username,
                'senha-passaporte': self.password
            }
            self.debug('username/password set. trying to authenticate')
            r = requests.post(self.ENDPOINT_URL, data=payload)
            self.glbid = r.cookies.get('GLBID')
            if self.glbid:
                self.debug('successfully authenticated')
                self.plugin.set_setting('glbid', self.glbid)
            else:
                self.debug('wrong username or password')
                self.notify_error(32001)
        elif self.glbid:
            self.debug('already authenticated with id %s' % self.glbid)
        else:
            self.debug('no username set to authenticate')

        return self.glbid


class GlobosatBackends(Backends):
    AUTHORIZE_URL = 'http://globosatplay.globo.com/-/gplay/authorize/'
    OAUTH_URL = 'https://auth.globosat.tv/oauth/authorize'
    OAUTH_QS = {
        'redirect_uri': 'http://globosatplay.globo.com/-/auth/gplay/?callback',
        'response_type': 'code',
    }
    PROVIDER_ID = None

    def __init__(self, plugin):
        self.plugin = plugin
        self.playid = self.plugin.get_setting('playid')
        self.username = self.plugin.get_setting('play_username')
        self.password = self.plugin.get_setting('play_password')

    def _prepare_auth(self):
        # get a client_id token
        # https://auth.globosat.tv/oauth/authorize/?redirect_uri=http://globosatplay.globo.com/-/auth/gplay/?callback&response_type=code
        r1 = requests.get(self.OAUTH_URL, params=self.OAUTH_QS)
        # get backend url
        r2 = requests.post(r1.url, data={'config': self.PROVIDER_ID})
        return r2.url.split('?', 1) + [dict(r2.cookies), ]


class gvt(GlobosatBackends):
    PROVIDER_ID = 62

    def authenticate(self):
        url, qs, cookies = self._prepare_auth()
        qs = urlparse.parse_qs(qs)
        r3 = requests.post(url,
                           cookies=dict(cookies),
                           data={
                                 'code': qs['code'][0],
                                 'user_Fone': None,
                                 'user_CpfCnpj': self.username,
                                 'password': self.password,
                                 'login': 'Login',
                                 })
        # validate authentication on globosat
        params = urlparse.parse_qs(r3.url.split('?', 1)[1])
        r4 = requests.get(params['redirect_uri'][0])
        # save session id
        print r4, dict(r4.cookies)
        return


        if not self.playid and (self.username and self.password):


            # post form_data to ENDPOINT_URL
            payload = {
                'code': '',
                'user_Fone': None,
                'user_CpfCnpj': None,
                # 'user_Fone': '',
                'user_CpfCnpj': '',
                'password': '',
                'login': 'Login',
            }

            if len(self.username) >= 11:
                payload['user_CpfCnpj'] = self.username
            else:
                payload['user_Fone'] = self.username
            self.debug('username/password set. trying to authenticate')
            r = requests.post(self.ENDPOINT_URL, data=payload)
            self.playid = r.cookies.get('GLBID')
            if self.playid:
                self.debug('successfully authenticated')
                self.plugin.set_setting('playid', self.playid)
            else:
                self.debug('wrong username or password')
                self.notify_error(32001)
        elif self.playid:
            self.debug('already authenticated with id %s' % self.playid)
        else:
            self.debug('no username set to authenticate')

        return self.playid

        # wait redirection
        # get string from urlString JS var
        # upon request of urlString, get Location response header, this is a callback
        # request the callback, and get the set cookie directives (2) containing Globo session id
        # request http://globosatplay.globo.com/-/gplay/authorize/
        # sample response:
        # {
        #     "user_id":"",
        #     "ueid":"",
        #     "token":"",
        #     "nome":"",
        #     "autorizador":{
        #         "nome":"GVT",
        #         "slug":"gvt",
        #         "app":"gvt",
        #         "imagem":"https://auth.globosat.tv/media/autorizador/6_2.png"
        #     }
        # }
        # token holds the id of the session
        pass
