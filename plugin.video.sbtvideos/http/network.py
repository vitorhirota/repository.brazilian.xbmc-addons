import xbmc;
import xbmcgui;
import xbmcplugin;
import xbmcaddon;
import urllib2;
from time import time;
import pickle;

class Cache:
	cacheData = {};
	settings = xbmcaddon.Addon("plugin.video.sbtvideos");
	
	def __init__(self):
		if (self.settings.getSetting("cache") != ""):
			self.cacheData = pickle.loads(self.settings.getSetting("cache"));

	def valid(self, key):
		return (self.cacheData.has_key(key) and time() - self.cacheData[key]["timestamp"] < 1 * 24 * 3600);
		
	def getData(self, key):
		if self.cacheData.has_key(key):
			return self.cacheData[key].get("data", None);
		return None;
		
	def setData(self, key, data):
		self.cacheData[key] = {
			"timestamp" : time(),
			"data" : data
		};
		self.settings.setSetting("cache", pickle.dumps(self.cacheData));
	
	def delKey(self, key):
		self.cacheData.pop(key, None);
		self.settings.setSetting("cache", pickle.dumps(self.cacheData));

cache = Cache();
		
def fetchUrl(url):
	# if url timestamp is less than 24-hour, return cached data
	if (cache.valid(url)):
		return cache.getData(url);
	else:
		header = {
			"User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:34.0) Gecko/20100101 Firefox/34.0",
			"Accept" : "application/json, text/javascript, */*; q=0.01",
			"Origin" : "http://www.sbt.com.br",
			"Referer" : "http://www.sbt.com.br/sbtvideos/programa/400/The-Noite-com-Danilo-Gentili/"
		};
		req = urllib2.Request(url, None, header);
		try:
			response = urllib2.urlopen(req);
			data = response.read();
			response.close();
			cache.setData(url, data);
		except urllib2.URLError:
			# ignore the timestamp if there is an error on the API
			if (myCache.has_key(url)): 
				return myCache[url]["data"];
			else:
				# Internet error
				data = "";
	return data;
	