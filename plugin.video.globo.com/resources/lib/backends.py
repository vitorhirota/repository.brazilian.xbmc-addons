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
import json
import re
import requests
import urlparse
import util
try:
    import HTMLParser
except:
    import html.parser as HTMLParser

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

    def _authenticate(self, provider_id):
        raise Exception('Not implemented.')

    def _save_credentials(self):
        self.plugin.set_setting('%s_credentials' % self.SETT_PREFIX,
                                pickle.dumps(self.credentials))

    def is_authenticated(self, provider_id):
        authProvider = False
        for key in self.credentials.keys():
            authProvider = authProvider or ((provider_id in key if provider_id is not None else key == 'GLBID') and self.credentials[key] is not None)
        return authProvider

    def authenticate(self, provider_id):
        if not self.is_authenticated(provider_id) and (self.username and self.password):
            self.debug('username/password set. trying to authenticate')
            self.credentials = util.merge_dicts(self.credentials, self._authenticate(provider_id))
            if self.is_authenticated(provider_id):
                self.debug('successfully authenticated')
                self._save_credentials()
            else:
                self.debug('wrong username or password')
                self.notify(32001)
        elif self.is_authenticated(provider_id):
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
    ENDPOINT_URL = 'https://login.globo.com/api/authentication'
    SETT_PREFIX = 'globo'

    def _authenticate(self, provider_id):
        payload = {
            'captcha':'',
            'payload': {
                'email': self.username,
                'password': self.password,
                'serviceId': 4654
            }
        }
        response = requests.post(self.ENDPOINT_URL,
                                 data=json.dumps(payload),
                                 headers={ 'content-type': 'application/json; charset=UTF-8',
                                           'accept': 'application/json, text/javascript',
                                           'referer': 'https://login.globo.com/login/4654?url=https://globoplay.globo.com/&tam=WIDGET',
                                           'origin': 'https://login.globo.com' },
                                 verify=False)
        return { 'GLBID': response.cookies.get('GLBID') }


class GlobosatBackends(Backends):
    AUTH_TOKEN_URL = 'http://security.video.globo.com/providers/WMPTOKEN_%s/tokens/%s/session?callback=setAuthenticationToken_%s&expires=%s'
    OAUTH_URL = 'http://globosatplay.globo.com/-/auth/gplay/'
    PROVIDER_ID = None
    SETT_PREFIX = 'play'

    def __init__(self,plugin):
        super(GlobosatBackends, self).__init__(plugin)
        self.session = requests.Session()

    def _authenticate(self, provider_id):
        # get a client_id token
        # https://auth.globosat.tv/oauth/authorize/?redirect_uri=http://globosatplay.globo.com/-/auth/gplay/?callback&response_type=code
        r1 = self.session.get(self.OAUTH_URL)
        # get backend url
        r2 = self.session.post(r1.url + '&duid=None', data={'config': self.PROVIDER_ID})
        url, qs = r2.url.split('?', 1)
        # provider authentication
        try:
            r3 = self._provider_auth(url, urlparse.parse_qs(qs))
        except Exception as e:
            self.error(str(e))
            return {}
        # set profile
        urlp, qp = r3.url.split('?', 1)
        try:
            accesstoken = re.findall('<form id="bogus-form" action="/perfis/selecionar/\?access_token=(.*)" method="POST">', r3.text)[0]
            post_data = {
                '_method': 'PUT',
                'duid': 'None',
                'perfil_id': re.findall('<div data-id="(\d+)" class="[\w ]+avatar', r3.text)[0]
            }
            r4 = self.session.post(urlp + '?access_token=' + accesstoken, data=post_data)
            # build credentials
            credentials = dict(r4.cookies)
            token = credentials[credentials['b64globosatplay']]
        except:
            raise Exception('There was a problem in the authetication process.')
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(days=7)
        r5 = self.session.get(self.AUTH_TOKEN_URL % (provider_id,
                                                 token,
                                                 calendar.timegm(now.timetuple()),
                                                 expiration.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        return dict(r5.cookies)

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
        self.session.post(url + '&id=tve&option=credential')
        # authenticate
        post_data = {
            'option': 'credential',
            'urlRedirect': url,
            'Ecom_User_ID': self.username,
            'Ecom_Password': self.password,
        }
        r1 = self.session.post(url, data=post_data)
        r2 = self.session.get(url)
        try:
            html_parser = HTMLParser.HTMLParser()
            #headers = {'Content-Type': 'application/x-www-form-urlencoded' }
            redirurl = re.findall(r'<form method=\"POST\" enctype=\"application/x-www-form-urlencoded\" action=\"(.*)\">', r2.text)[0]
            argsre = dict([(match.group(1), html_parser.unescape(match.group(2))) for match in re.finditer(r'<input type=\"hidden\" name=\"(\w+)\" value=\"([^\"]+)\"/>', r2.text)])
            return self.session.post(redirurl, data=argsre)#, headers=headers)
        except:
            raise Exception('Invalid user name or password.')

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
            return self.session.get(match.group(1).replace("\u0026","&"))

        raise Exception('Invalid user name or password.')

class vivo(GlobosatBackends):
    PROVIDER_ID = 147

    def _provider_auth(self, url, qs):
        cpf = self.username
        if len(cpf) == 11:
            cpf = "%s.%s.%s-%s" % ( cpf[0:3], cpf[3:6], cpf[6:9], cpf[9:11] )
        qs.update({
            'user_Doc': cpf,
            'password': self.password,
            'password_fake': None,
        })
        req = self.session.post(url, data=qs)
        nova_url = re.findall('var urlString = \'(.*)\';', req.text)[0]
        ret_req = self.session.get(nova_url)
        return ret_req

class claro(GlobosatBackends):
    PROVIDER_ID = 123

    def _provider_auth(self, url, qs):
        qs.update({
            'cpf': self.username,
            'senha': self.password,
        })
        req = self.session.post(url, data=qs)
        ipt_values_regex = r'%s=["\'](.*)["\'] '
        try:
            action = re.findall(ipt_values_regex % 'action', req.text)[0]
            value = re.findall(ipt_values_regex[:-1] % 'value', req.text)[0]
        except IndexError:
            raise Exception('Invalid user name or password.')
        return req

class globosat_guest(GlobosatBackends):
    PROVIDER_ID = 50

    def _provider_auth(self, url, qs):
        qs.update({
            'login': self.username,
            'senha': self.password,
        })
        req = self.session.post(url, data=qs)
        ipt_values_regex = r'%s=["\'](.*)["\'] '
        try:
            action = re.findall(ipt_values_regex % 'action', req.text)[0]
            value = re.findall(ipt_values_regex[:-1] % 'value', req.text)[0]
        except IndexError:
            raise Exception('Invalid user name or password.')
        return req
