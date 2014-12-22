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
import calendar
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

    def _authenticate(self):
        raise Exception('Not implemented.')

    def _save_credentials(self):
        self.plugin.set_setting('%s_credentials' % self.SETT_PREFIX,
                                pickle.dumps(self.credentials))

    def authenticate(self):
        # import pydevd; pydevd.settrace()
        if not any(self.credentials.values()) and (self.username and self.password):
            self.debug('username/password set. trying to authenticate')
            self.credentials = self._authenticate()
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

    def error(self, msg):
        self.plugin.log.error('[%s] %s' % (self.__class__.__name__, msg),
                              exc_info=1)

    def notify(self, string_id):
        self.plugin.notify('[%s] %s' % (self.__class__.__name__,
                                        self.plugin.get_string(string_id)))


class globo(Backends):
    ENDPOINT_URL = 'https://login.globo.com/login/151?tam=widget'
    SETT_PREFIX = 'globo'

    def _authenticate(self):
        payload = {
            'botaoacessar': 'acessar',
            'login-passaporte': self.username,
            'senha-passaporte': self.password
        }
        response = requests.post(self.ENDPOINT_URL, data=payload)
        return { 'GLBID': response.cookies.get('GLBID') }


class GlobosatBackends(Backends):
    AUTH_TOKEN_URL = 'http://security.video.globo.com/providers/WMPTOKEN_%s/tokens/%s/session?callback=setAuthenticationToken_%s&expires=%s'
    OAUTH_URL = 'http://globosatplay.globo.com/-/auth/gplay/'
    PROVIDER_ID = None
    SETT_PREFIX = 'play'

    def __init__(self,plugin):
        super(GlobosatBackends, self).__init__(plugin)
        self.session = requests.Session()

    def _authenticate(self):
        # get a client_id token
        # https://auth.globosat.tv/oauth/authorize/?redirect_uri=http://globosatplay.globo.com/-/auth/gplay/?callback&response_type=code
        r1 = self.session.get(self.OAUTH_URL)
        # get backend url
        r2 = self.session.post(r1.url, data={'config': self.PROVIDER_ID})
        url, qs = r2.url.split('?', 1)
        # provider authentication
        try:
            r3 = self._provider_auth(url, urlparse.parse_qs(qs))
        except Exception as e:
            self.error(str(e))
            return {}
        # set profile
        post_data = {
            '_method': 'PUT',
            'perfil_id': re.findall('<div data-id="(\d+)" class="avatar', r3.text)
        }
        r4 = self.session.post(r3.url, data=post_data)
        # build credentials
        credentials = dict(r4.cookies)
        # provider_id is a property from a video playlist. Tt seems, however,
        # the only provider available for now is gplay. Instead of requesting
        # for a given playlist (which requires a valid video_id, this is being
        # harcoded for now.
        provider_id = '52dfc02cdd23810590000f57'
        token = credentials[credentials['b64globosatplay']]
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(days=7)
        r5 = requests.get(self.AUTH_TOKEN_URL % (provider_id,
                                                 token,
                                                 calendar.timegm(now.timetuple()),
                                                 expiration.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        return dict(r5.cookies)


class gvt(GlobosatBackends):
    PROVIDER_ID = 62

    def _provider_auth(self, url, qs):
        post_data = {
            'code': qs['code'][0],
            'user_Fone': None,
            'user_CpfCnpj': self.username,
            'password': self.password,
            'login': 'Login',
        }
        req = self.session.post(url, data=post_data)
        try:
            return self.session.get(req.url.split('redirect_uri=', 1)[1])
        except IndexError:
            # if invalid user/pass: IndexError: list index out of range
            raise Exception('Invalid user name or password.')


class net(GlobosatBackends):
    PROVIDER_ID = 64

    def _provider_auth(self, url, qs):
        qs.update({
            '_submit.x': '115',
            '_submit.y': '20',
            'externalSystemName': 'none',
            'password': self.password,
            'passwordHint': '',
            'selectedSecurityType': 'public',
            'username': self.username,
        })
        url = 'https://idm.netcombo.com.br/IDM/SamlAuthnServlet'
        req = self.session.post(url, data=qs)
        ipt_values_regex = r'%s=["\'](.*)["\'] '
        try:
            action = re.findall(ipt_values_regex % 'action', req.text)[0]
            value = re.findall(ipt_values_regex[:-1] % 'value', req.text)[0]
            # self.debug('action: %s, value: %s' % (action, value))
        except IndexError:
            raise Exception('Invalid user name or password.')
        return self.session.post(action, data={'SAMLResponse': value})


class tv_oi(GlobosatBackends):
    PROVIDER_ID = 66

    def _provider_auth(self, url, qs):
        url += '?sid=0'
        # prepare auth
        self.session.post(url + '&id=telecineplay&option=credential')
        # authenticate
        post_data = {
            'option': 'credential',
            'urlRedirect': url,
            'Ecom_User_ID': self.username,
            'Ecom_Password': self.password,
        }
        req = self.session.post(url, data=post_data)
        # if login is successful, response is just a js redirect
        if int(req.headers['content-length']) > 1500:
            raise Exception('Invalid user name or password.')
        return self.session.get(url)


class sky(GlobosatBackends):
    PROVIDER_ID = 80

    def _provider_auth(self, url, qs):
        qs.update({
            'login': self.username,
            'senha': self.password,
            'clientId': '',
        })
        url = 'http://www1.skyonline.com.br/Modal/Logar'
        req = self.session.post(url, data=qs)
        match = re.search('^"(http.*)"$', req.text)
        if match:
            return self.session.get(match.group(1))

        raise Exception('Invalid user name or password.')
