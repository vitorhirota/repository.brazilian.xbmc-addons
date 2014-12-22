import sys;
import xbmc;
import xbmcgui;
import xbmcplugin;
import xbmcaddon;
import urllib;
import urllib2;
import urlparse;
import json;
import re;
import base64;
from time import time;
import pickle;

# getting settings strings
settings = xbmcaddon.Addon("plugin.video.sbt-thenoite");
_ = settings.getLocalizedString;
ga = {
	"enabled" : False,
	"UA" : 'UA-18146963-3',
	"appName" : settings.getAddonInfo("name"),
	"appVersion" : settings.getAddonInfo("version"),
	"appId" : settings.getAddonInfo("id")
}

if (settings.getSetting("analytics") == "true"):
	from UniversalAnalytics import Tracker;
	tracker = Tracker.create(ga["UA"]);
	tracker.set("appName", ga["appName"]);
	tracker.set("appVersion", ga["appVersion"]);
	tracker.set("appId", ga["appId"]);
	ga["enabled"] = True;
	if (settings.getSetting("uuid") == ""):
		settings.setSetting("uuid", tracker.params["cid"]);
	else:
		tracker.set("clientId", settings.getSetting("uuid"));

# setting SBT urls
thenoite_urls = {};
# thenoite_urls["menu_api"] = "http://api.sbt.com.br/1.4.5/medias/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,thumbnail,author&idsite=198&idSiteArea=1011&limit=100&orderBy=ordem&sort=asc";
# thenoite_urls["media_api"] = "http://api.sbt.com.br/1.4.5/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,thumbnail,publishdate,secondurl&program=400&limit=300&orderBy=publishdate&category=$authorId&sort=desc";
thenoite_urls["menu_api"] = "http://api.sbt.com.br/1.5.0/medias/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,description,thumbnail,author,opcional&idsite=211&idSiteArea=1068&idPlaylist=3435&limit=100&orderby=ordem&sort=ASC";
thenoite_urls["media_api"] = "http://api.sbt.com.br/1.5.0/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,idcategory,idprogram,program,thumbnail,publishdatestring,secondurl,playerkey,total&program=400&category=$authorId&limit=100&orderBy=publishdate&sort=desc";
thenoite_urls["video_url"] = 'http://fast.player.liquidplatform.com/pApiv2/embed/25ce5b8513c18a9eae99a8af601d0943/$videoId';

myCache = {};
if (settings.getSetting("cache") != ""):
	myCache = pickle.loads(settings.getSetting("cache"));

thenoite_authors_slug = {
	"4526" : "naintegra",
	"4529" : "entrevistas",
	"4527" : "melhoresmomentos",
	"4769" : "roommates",
	"4670" : "musical",
	"4521" : "omestremandou",
	"4597" : "recordesincriveis",
	"4620" : "desenhosdodanilo",
	"4519" : "leiteshow",
	"4517" : "ohomemdoqi200",
	"4518" : "rodadadanoite",
	"4520" : "cyberbullying",
	"4528" : "chamadas"
};

base_url = sys.argv[0];
addon_handle = int(sys.argv[1]);
args = urlparse.parse_qs(sys.argv[2][1:]);

def invertDates(date):
	date = date.split("/");
	date.reverse();
	return "/".join(date);

def fetchUrl(url):
	# if url timestamp is less than 24-hour, return cached data
	if (myCache.has_key(url) and time() - myCache[url]["timestamp"] < 1 * 24 * 3600):
		return myCache[url]["data"];
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
			myCache[url] = {
				"timestamp" : time(),
				"data" : data
			};
			settings.setSetting("cache", pickle.dumps(myCache));
		except urllib2.URLError:
			# ignore the timestamp if there is an error on the API
			if (myCache.has_key(url)): 
				return myCache[url]["data"];
			else:
				# Internet error
				data = "";
	return data;

def makeUrl(query = {}):
	return base_url + "?" + urllib.urlencode(query);

def parseMediaInfo(html):
	match = re.compile("window.mediaJson = (.+?);").findall(html);
	if len(match) > 0:
		return json.loads(match[0]);
		
	match = re.compile("window.mediaToken = (.+?);").findall(html);
	if len(match) > 0:
		# getting max-width from body tag
		maxWidth = re.compile("<body .*max-width:(.*);.*>").findall(html);
		# xbmc.log("["+_(30006)+"]: Found maxWidth "+str(maxWidth), 0);
		if len(maxWidth) > 0:
			# xbmc.log("["+_(30006)+"]: Found token "+match[0], 0);
			maxWidth = maxWidth[0].strip().replace("px", "");
			# xbmc.log("["+_(30006)+"]: max-width "+maxWidth, 0);
			maxWidth = int((int(maxWidth) ^ 345) - 1E4) + 1;
			# discard = match[0][0:maxWidth]; #keeping this for debug purposes
			# xbmc.log("["+_(30006)+"]: Will discard "+discard, 0);
			
			encodedToken = match[0][maxWidth:-maxWidth];
			# xbmc.log("["+_(30006)+"]: Encoded token "+encodedToken, 0);
			
			if(len(encodedToken) % 4 == 2):
				encodedToken = encodedToken + "==";
			elif(len(encodedToken) % 4 == 3):
				encodedToken = encodedToken + "=";
				
			return json.loads(base64.b64decode(encodedToken));

	return None;

def clearCacheFor(url):
	myCache.pop(url, None);
	settings.setSetting("cache", pickle.dumps(myCache));

mode = args.get("mode", None);

if mode is None:
	# settings.setSetting("welcome", "");
	if (settings.getSetting("welcome") == ""): 
		welcome = xbmcgui.Dialog();
		opt = welcome.yesno(_(30009), _(30010), None, None, _(30011), _(30012));
		if (opt == True):
			settings.setSetting("analytics", "true");
		else:
			settings.setSetting("analytics", "false");
		settings.setSetting("welcome", "True");
		
		try:
			Tracker
		except NameError:
			from UniversalAnalytics import Tracker;
			tracker = Tracker.create(ga["UA"]);
			tracker.set("appName", ga["appName"]);
			tracker.set("appVersion", ga["appVersion"]);
			tracker.set("appId", ga["appId"]);
			if (settings.getSetting("uuid") == ""):
				settings.setSetting("uuid", tracker.params["cid"]);
			else:
				tracker.set("clientId", settings.getSetting("uuid"));
			
		
		tracker.send("event", "Usage", "install", screenName="Welcome")
	elif (ga["enabled"]):
		tracker.send("screenview", screenName="Main Menu")

	xbmcplugin.setContent(addon_handle, 'tvshows');
	
	index = fetchUrl(thenoite_urls["menu_api"]);
	menu = json.loads(index);
	
	# try to recover from sbt api error
	saved = False;
	if ("error" in menu):
		xbmc.log("["+_(30006)+"]: "+str(menu["error"]), 0);
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Main Menu");
			
		if (myCache.has_key(thenoite_urls["menu_api"])):
			menu = json.loads(myCache[thenoite_urls["menu_api"]]["data"]);
			if ("error" in menu):
				clearCacheFor(thenoite_urls["menu_api"]);
			else:
				saved = True;
	
	if ("error" in menu and saved == False):
		# do nothing
		toaster = xbmcgui.Dialog();
		try:
			toaster.notification(_(30006), _(30008), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30008));
		pass
	else:
		# displaying each video category from The Noite website
		for menuItem in menu["medias"]:
			url = makeUrl({"mode" : "listitems", "author" : menuItem["author"], "title" : menuItem["title"].encode('utf8')});
		
			li = xbmcgui.ListItem(menuItem["title"], iconImage=menuItem["thumbnail"]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);

	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "listitems"):
	xbmcplugin.setContent(addon_handle, 'episodes');
	
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Second Menu - "+args.get("title")[0]);
	
	authorId = args.get("author")[0];
	url = thenoite_urls["media_api"].replace("$authorId", authorId);
	index = fetchUrl(url);
	videos = json.loads(index);

	# trying to recover from sbt api error
	saved = False;
	if ("error" in videos):
		xbmc.log("["+_(30006)+"]: "+str(videos["error"]), 0);
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Second Menu - "+args.get("title")[0]);
	
		if (myCache.has_key(url)):
			videos = json.loads(myCache[url]["data"]);
			if ("error" in videos):
				clearCacheFor(url);
			else:
				saved = True;
	
	if ("error" in videos and saved == False):
		# do nothing
		toaster = xbmcgui.Dialog();
		try:
			toaster.notification(_(30006), _(30007), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30007));
		pass
	elif ((authorId in thenoite_authors_slug) and thenoite_authors_slug[authorId] == "naintegra"):
		# grouping urls by episodes
		episodes = {};
		for video in videos["videos"]:
			episode = re.compile("The Noite \(?(.+?)\)? ").findall(video["title"]);
			part = re.compile("parte \(?(.+?)\)?", re.IGNORECASE).findall(video["title"]);
			
			if (len(part) == 0):
				part = [0];
			
			video["index"] = int(part[0]);
			if (episode[0] in episodes):
				inserted = False;
				for index, item in enumerate(episodes[episode[0]]):
					if (int(part[0]) < item["index"]):
						inserted = True;
						episodes[episode[0]].insert(index, video);
						break;
						
				if (not(inserted)):
					episodes[episode[0]].append(video);
				
			else:
				episodes[episode[0]] = [video];
	
		# listing each episode part
		for episode in sorted(episodes, key=invertDates, reverse=True):
			video_ids = [];
			for video in episodes[episode]:
				video_ids.append(video["id"]);
		
			whole_url = makeUrl({"mode" : "episodeurl", "play_episode" : json.dumps(video_ids)});
		
			for video in episodes[episode]:
				url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
			
				li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
				li.addContextMenuItems([(_(30001), 'XBMC.RunPlugin('+whole_url+')')]);
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
		
	else:
		for video in videos["videos"]:
			url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
	
			li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
					
		
	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "videourl"):
	iframe = fetchUrl(thenoite_urls["video_url"].replace("$videoId", args.get("play_video")[0]));
	video = parseMediaInfo(iframe);
	
	if (ga["enabled"]):
		tracker.send("event", "Usage", "Play Video", "unique", screenName="Play Screen");
	
	# Sambatech url never gave an error, so we are skipping error recovery for this part
	
	if (video):
		# finding best video thumbnail, optimal is 480 x 360 by default
		video_thumb = None;
		for thumbnail in video["thumbnailList"]:
			if (thumbnail["qualifierName"] == "THUMBNAIL"):
				if (thumbnail["width"] == 480 and thumbnail["height"] == 360):
					video_thumb = thumbnail;
					break;
				elif (video_thumb == None):
					video_thumb = thumbnail;
				elif(video_thumb["width"] <= thumbnail["width"] and video_thumb["height"] <= thumbnail["height"]):
					video_thumb = thumbnail;
					
		userQuality = settings.getSetting("video.quality");
		# xbmc.log("["+_(30006)+"]: Will look for video at quality "+userQuality, 0);
		for deliveryRules in video["deliveryRules"]:
			if (deliveryRules["rule"]["ruleName"] == "r1"):
				listItem = None;
				defaultListItem = None;
				for output in deliveryRules["outputList"]:
					# xbmc.log("["+_(30006)+"]: Video quality "+output["labelText"], 0);
					if (output["labelText"] == userQuality):
						# xbmc.log("["+_(30006)+"]: Match for user quality", 0);
						listItem = xbmcgui.ListItem(video["title"]);
						listItem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
						if (video_thumb != None): # setting thubmnail and icon image, if any
							listItem.setIconImage(video_thumb["url"]);
							listItem.setThumbnailImage(video_thumb["url"]);
						break;
					if (output["labelText"] == "480p"):
						# xbmc.log("["+_(30006)+"]: Match for default quality", 0);
						defaultListItem = xbmcgui.ListItem(video["title"]);
						defaultListItem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
						if (video_thumb != None): # setting thubmnail and icon image, if any
							defaultListItem.setIconImage(video_thumb["url"]);
							defaultListItem.setThumbnailImage(video_thumb["url"]);
				if (listItem != None):
					# xbmc.log("["+_(30006)+"]: Playing user video quality", 0);
					xbmc.Player().play(output["url"], listItem);
				elif(defaultListItem != None):
					# xbmc.log("["+_(30006)+"]: Playing default video quality", 0);
					xbmc.Player().play(output["url"], defaultListItem);
				break;
	else:
		xbmc.log("["+_(30006)+"]: Unable to find video for ID "+args.get("play_video")[0], 0);
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Play Screen");
		
		# do nothing
		toaster = xbmcgui.Dialog();
		try:
			toaster.notification(_(30006), _(30008), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30008));
		pass
			
elif (mode[0] == "episodeurl"):
	# Displaying progress dialog
	pDialog = xbmcgui.DialogProgress();
	pDialog.create(_(30002), _(30003)); # pDialog.create("Fetching videos", "Loading episode parts...")

	if (ga["enabled"]):
		tracker.send("event", "Usage", "Play Video", "episode", screenName="Play Screen");

	videos_ids = json.loads(args.get("play_episode")[0]);
	xbmcPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO);
	xbmcPlaylist.clear();
	
	pDialogCount = 0;
	pDialogLength = len(videos_ids);
	for video_id in videos_ids:
		pDialogCount = pDialogCount + 1;
		pDialog.update(int(90*pDialogCount/float(pDialogLength)), _(30004).format(str(pDialogCount),str(pDialogLength)));
		
		iframe = fetchUrl(thenoite_urls["video_url"].replace("$videoId", video_id));
		video = parseMediaInfo(iframe);
		
		if (video):
			# finding best video thumbnail, optimal is 480 x 360 by default
			video_thumb = None;
			for thumbnail in video["thumbnailList"]:
				if (thumbnail["qualifierName"] == "THUMBNAIL"):
					if (thumbnail["width"] == 480 and thumbnail["height"] == 360):
						video_thumb = thumbnail;
						break;
					elif (video_thumb == None):
						video_thumb = thumbnail;
					elif(video_thumb["width"] <= thumbnail["width"] and video_thumb["height"] <= thumbnail["height"]):
						video_thumb = thumbnail;
		
			userQuality = settings.getSetting("video.quality");
			for deliveryRules in video["deliveryRules"]:
				if (deliveryRules["rule"]["ruleName"] == "r1"):
					listItem = None;
					defaultListItem = None;
					for output in deliveryRules["outputList"]:
						if (output["labelText"] == userQuality):
							listItem = xbmcgui.ListItem(video["title"]);
							listItem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
							if (video_thumb != None): # setting thubmnail and icon image, if any
								listItem.setIconImage(video_thumb["url"]);
								listItem.setThumbnailImage(video_thumb["url"]);
							break;
						if (output["labelText"] == "480p"):
							defaultListItem = xbmcgui.ListItem(video["title"]);
							defaultListItem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
							if (video_thumb != None): # setting thubmnail and icon image, if any
								defaultListItem.setIconImage(video_thumb["url"]);
								defaultListItem.setThumbnailImage(video_thumb["url"]);
					
					if (listItem != None):
						xbmcPlaylist.add(output["url"], listItem);
					elif(defaultListItem != None):
						xbmcPlaylist.add(output["url"], defaultListItem);
					break;
		else:
			xbmc.log("["+_(30006)+"]: Unable to find video for ID "+args.get("play_video")[0], 0);
		
			# taking note from the amount of errors the SBT API may throw
			if (ga["enabled"]):
				tracker.send("event", "Usage", "error", screenName="Play Screen");
		
			# do nothing
			toaster = xbmcgui.Dialog();
			try:
				toaster.notification(_(30006), _(30008), xbmcgui.NOTIFICATION_WARNING, 3000);
			except AttributeError:
				toaster.ok(_(30006), _(30008));
			pass
					
	# Closing progress dialog
	pDialog.update(100, _(30005));
	pDialog.close();
	xbmc.Player().play(xbmcPlaylist);