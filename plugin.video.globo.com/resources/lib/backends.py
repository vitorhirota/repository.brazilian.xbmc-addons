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
import datetime
import re
import requests
import urlparse

try:
    import cPickle as pickle
except:
    import pickle

class Backends(object):
    ENDPOINT_URL = None
    SETT_PREFIX = None

    def __init__(self, plugin):
        self.plugin = plugin
        self.username = self.plugin.get_setting('%s_username' % self.SETT_PREFIX)
        self.password = self.plugin.get_setting('%s_password' % self.SETT_PREFIX)
        try:
            credentials = self.plugin.get_setting('%s_credentials' % self.SETT_PREFIX)
            self.credentials = pickle.loads(credentials)
        except:
            self.credentials = {}

    def _provider_auth(self):
        raise Exception('Not implemented.')

    def _save_credentials(self):
        self.plugin.set_setting('%s_credentials' % self.SETT_PREFIX,
                                pickle.dumps(self.credentials, -1))

    def authenticate(self):
        # import pydevd; pydevd.settrace()
        if not any(self.credentials.values()) and (self.username and self.password):
            self.debug('username/password set. trying to authenticate')
            self.credentials = self._provider_auth()
            if any(self.credentials.values()):
                self.debug('successfully authenticated')
                self._save_credentials()
            else:
                self.debug('wrong username or password')
                self.notify(32001)
        elif any(self.credentials.values()):
            self.debug('already authenticated')
        else:
            self.debug('no username set to authenticate')
        self.debug(repr(self.credentials))

        return self.credentials

    def debug(self, msg):
        self.plugin.log.debug('[%s] %s' % (self.__class__.__name__, msg))

    def notify(self, string_id):
        self.plugin.notify('[%s] %s' % (self.__class__.__name__,
                                        self.plugin.get_string(string_id)))


class globo(Backends):
    ENDPOINT_URL = 'https://login.globo.com/login/151?tam=widget'
    SETT_PREFIX = 'globo'

    def _provider_auth(self):
        payload = {
            'botaoacessar': 'acessar',
            'login-passaporte': self.username,
            'senha-passaporte': self.password
        }
        response = requests.post(self.ENDPOINT_URL, data=payload)
        return { 'GLBID': response.cookies.get('GLBID') }


class GlobosatBackends(Backends):
    AUTHORIZE_URL = 'http://globosatplay.globo.com/-/gplay/authorize/'
    AUTH_TOKEN_URL = 'http://security.video.globo.com/providers/WMPTOKEN_%s/tokens/%s/session?callback=setAuthenticationToken_%s&expires=%s'
    OAUTH_URL = 'https://auth.globosat.tv/oauth/authorize'
    OAUTH_QS = {
        'redirect_uri': 'http://globosatplay.globo.com/-/auth/gplay/?callback',
        'response_type': 'code',
    }
    PROVIDER_ID = None
    SETT_PREFIX = 'play'

    def _set_auth_token(self):
        # provider_id is a property from a video playlist. Tt seems, however,
        # the only provider available for now is gplay. Instead of requesting
        # for a given playlist (which requires a valid video_id, this is being
        # harcoded for now.
        provider_id = '52dfc02cdd23810590000f57'
        token = self.credentials[self.credentials['b64gplay']]
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(days=7)
        r = requests.get(self.AUTH_TOKEN_URL % (provider_id, token,
                                                now.strftime('%s'),
                                                expiration.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        self.credentials = dict(r.cookies)

    def _prepare_auth(self):
        # get a client_id token
        # https://auth.globosat.tv/oauth/authorize/?redirect_uri=http://globosatplay.globo.com/-/auth/gplay/?callback&response_type=code
        r1 = requests.get(self.OAUTH_URL, params=self.OAUTH_QS)
        # get backend url
        r2 = requests.post(r1.url, data={'config': self.PROVIDER_ID})
        return r2.url.split('?', 1) + [dict(r2.cookies), ]

    def _save_credentials(self):
        # update credentials to be a proper authentication token
        self._set_auth_token()
        self.plugin.set_setting('%s_credentials' % self.SETT_PREFIX,
                                pickle.dumps(self.credentials, -1))


class gvt(GlobosatBackends):
    PROVIDER_ID = 62

    def _provider_auth(self):
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
        # params = urlparse.parse_qs(r3.url.split('?', 1)[1])
        try:
            r4 = requests.get(r3.url.split('redirect_uri=', 1)[1])
        except IndexError:
            # if invalid user/pass: IndexError: list index out of range
            return {}
        # save session id
        return dict(r4.cookies)

