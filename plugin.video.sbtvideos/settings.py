import xbmcaddon;
import pickle;

class Settings(xbmcaddon.Addon):
	videosWatched = {};
	
	def __init__(self, appId):
		super(Settings, self).__init__(appId);
		if (self.getSetting("videos_watched") != ""):
			self.videosWatched = pickle.loads(self.getSetting("videos_watched"));
		
	def getWatched(self, key):
		return self.videosWatched.get(key, False);
		
	def setWatched(self, key, value):
		self.videosWatched[key] = value;
		self.setSetting("videos_watched", pickle.dumps(self.videosWatched));
