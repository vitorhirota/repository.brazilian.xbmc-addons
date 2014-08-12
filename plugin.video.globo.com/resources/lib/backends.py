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
import cPickle
import re
import requests
import urlparse
from BeautifulSoup import BeautifulSoup

class Backends(object):
    ENDPOINT_URL = None
    SETT_PREFIX = None

    def __init__(self, plugin):
        self.plugin = plugin
        self.username = self.plugin.get_setting('%s_username' % self.SETT_PREFIX)
        self.password = self.plugin.get_setting('%s_password' % self.SETT_PREFIX)
        try:
            credentials = self.plugin.get_setting('%s_credentials' % self.SETT_PREFIX)
            self.credentials = cPickle.loads(credentials)
        except:
            self.credentials = {}

    def _provider_auth(self):
        raise Exception('Not implemented.')

    def _save_credentials(self):
        self.plugin.set_setting('%s_credentials' % self.SETT_PREFIX,
                                cPickle.dumps(self.credentials, -1))

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
    OAUTH_URL = 'https://auth.globosat.tv/oauth/authorize'
    OAUTH_QS = {
        'redirect_uri': 'http://globosatplay.globo.com/-/auth/gplay/?callback',
        'response_type': 'code',
    }
    PROVIDER_ID = None
    SETT_PREFIX = 'play'

    def _prepare_auth(self):
        # get a client_id token
        # https://auth.globosat.tv/oauth/authorize/?redirect_uri=http://globosatplay.globo.com/-/auth/gplay/?callback&response_type=code
        r1 = requests.get(self.OAUTH_URL, params=self.OAUTH_QS)
        # get backend url
        r2 = requests.post(r1.url, data={'config': self.PROVIDER_ID})
        return r2.url.split('?', 1) + [dict(r2.cookies), ]


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
        r4 = requests.get(r3.url.split('redirect_uri=', 1)[1])
        # save session id
        return dict(r4.cookies)

class netGeral(GlobosatBackends):
        PROVIDER_ID = 64

        def __init__(self,plugin):
            super(netGeral,self).__init__(plugin)
            self.session = requests.Session()

        def _prepare_auth(self):
            # STEP 1 ******************
            URL1 = 'http://globosatplay.globo.com/-/auth/gplay/'
            PARAMS1 = {'callback' :	'http://globosatplay.globo.com/fechar-login/?redirect=false',
                       'target_url' : 'http://globosatplay.globo.com/'}
            self.response = self.session.get(URL1,params=PARAMS1)
            # STEP 2 ***************** is really necessary ? could I use self.response.url direct ?
            u = urlparse.urlparse(self.response.url)
            url2 = u.scheme + '://' + u.hostname + u.path
            params2 = urlparse.parse_qs(u.query)
            POST_DATA2 = post_params = {'config':netGeral.PROVIDER_ID} # 64 = id net
            return self.session.post(url2,params=params2,data=POST_DATA2)


        def _provider_auth(self):
            #
            r2 = self._prepare_auth()
            u = urlparse.urlparse(r2.url)
            params3 = urlparse.parse_qs(u.query)
            params3['_submit.x'] = '115'
            params3['_submit.y'] = '20'
            params3['externalSystemName'] = 'none'
            params3['password'] = self.password
            params3['passwordHint'] = ''
            params3['selectedSecurityType'] = 'public'
            params3['username'] = self.username
            r3 = self.session.post('https://idm.netcombo.com.br/IDM/SamlAuthnServlet',data=params3)
            s = BeautifulSoup(r3.text)
            params4 = {}
            params4[s.input['name']] = s.input['value']
            r4 = self.session.post(s.form['action'],data=params4)
            return r4.cookies
