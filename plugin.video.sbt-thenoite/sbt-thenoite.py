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
import time;
import pickle;
import random;
import settings;

# getting settings strings
addon = settings.Settings("plugin.video.sbt-thenoite");
_ = addon.getLocalizedString;
ga = {
	"enabled" : False,
	"UA" : 'UA-18146963-3',
	"appName" : addon.getAddonInfo("name"),
	"appVersion" : addon.getAddonInfo("version"),
	"appId" : addon.getAddonInfo("id")
}
randomButtonEnabled = False if (addon.getSetting("randomButtonEnabled") == "false") else True;

if (addon.getSetting("analytics") == "true"):
	from UniversalAnalytics import Tracker;
	tracker = Tracker.create(ga["UA"]);
	tracker.set("appName", ga["appName"]);
	tracker.set("appVersion", ga["appVersion"]);
	tracker.set("appId", ga["appId"]);
	ga["enabled"] = True;
	if (addon.getSetting("uuid") == ""):
		addon.setSetting("uuid", tracker.params["cid"]);
	else:
		tracker.set("clientId", addon.getSetting("uuid"));

# setting SBT urls
thenoite_urls = {};
thenoite_urls["menu_api"] = "http://api.sbt.com.br/1.5.0/medias/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,description,thumbnail,author,opcional&idsite=211&idSiteArea=1068&idPlaylist=3435&limit=100&orderby=ordem&sort=ASC";
thenoite_urls["media_api"] = "http://api.sbt.com.br/1.5.0/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,idcategory,idprogram,program,thumbnail,publishdatestring,secondurl,playerkey,total&program=400&category=$authorId&limit=100&orderBy=publishdate&sort=desc&page=$page";
thenoite_urls["video_url"] = 'http://fast.player.liquidplatform.com/pApiv2/embed/25ce5b8513c18a9eae99a8af601d0943/$videoId';

myCache = {};
if (addon.getSetting("cache") != ""):
	myCache = pickle.loads(addon.getSetting("cache"));

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

def log(msg):
	msg = "["+_(30006)+"]: "+msg;
	msg = msg.encode("utf-8");
	xbmc.log(msg, 0);

def invertDates(date):
	date = date.split("/");
	date.reverse();
	return "/".join(date);

def fetchUrl(url):
	# if url timestamp is less than 24-hour, return cached data
	if (myCache.has_key(url) and time.time() - myCache[url]["timestamp"] < 1 * 24 * 3600):
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
				"timestamp" : time.time(),
				"data" : data
			};
			addon.setSetting("cache", pickle.dumps(myCache));
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
	addon.setSetting("cache", pickle.dumps(myCache));
	
def getVideoThumbnail(video):
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
	
	return video_thumb;

def getXbmcVideoFromVideo(video, video_thumb):
	ret = None;
	userQuality = addon.getSetting("video.quality");
	for deliveryRules in video["deliveryRules"]:
		if (deliveryRules["rule"]["ruleName"] == "r1"):
			listItem = None;
			videoUrl = "";
			for output in deliveryRules["outputList"]:
				if (output["labelText"] == userQuality):
					videoUrl = output["url"];
					listItem = xbmcgui.ListItem(video.get("title", _(30007)));
					listItem.setInfo("video", {"Title" : video.get("title", _(30007)), "Plot" : video.get("description", "")});
					if (video_thumb != None): # setting thubmnail and icon image, if any
						listItem.setIconImage(video_thumb["url"]);
						listItem.setThumbnailImage(video_thumb["url"]);
					break;
				elif (output["labelText"] == "480p"):
					videoUrl = output["url"];
					listItem = xbmcgui.ListItem(video.get("title", "Untitled"));
					listItem.setInfo("video", {"Title" : video.get("title", _(30007)), "Plot" : video.get("description", "")});
					if (video_thumb != None): # setting thubmnail and icon image, if any
						listItem.setIconImage(video_thumb["url"]);
						listItem.setThumbnailImage(video_thumb["url"]);
			if (listItem != None):
				ret = {};
				ret["url"] = videoUrl;
				ret["listitem"] = listItem;
			break;
			
	return ret;

def playVideoList(videos_ids):
	# Displaying progress dialog
	pDialog = xbmcgui.DialogProgress();
	pDialog.create(_(30002), _(30003)); # pDialog.create("Fetching videos", "Loading episode parts...")

	if (ga["enabled"]):
		tracker.send("event", "Usage", "Play Video", "episode", screenName="Play Screen");

	xbmcPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO);
	xbmcPlaylist.clear();
	
	pDialogCount = 0;
	pDialogLength = len(videos_ids);
	for video_id in videos_ids:
		pDialogCount = pDialogCount + 1;
		pDialog.update(int(90*pDialogCount/float(pDialogLength)), _(30004).format(str(pDialogCount),str(pDialogLength)));
		
		iframe = fetchUrl(thenoite_urls["video_url"].replace("$videoId", video_id));
		video = parseMediaInfo(iframe);
		
		if ("error" in video and video["error"] == True):
			xbmc.log("["+_(30006)+"]: Unable to find video for ID "+video_id, 0);
		
			# taking note from the amount of errors the SBT API may throw
			if (ga["enabled"]):
				tracker.send("event", "Usage", "error", screenName="Play Screen");
		
			# do nothing
			toaster = xbmcgui.Dialog();
			try:
				toaster.notification(_(30006), _(30103), xbmcgui.NOTIFICATION_WARNING, 3000);
			except AttributeError:
				toaster.ok(_(30006), _(30103));
			pass
		else:
			addon.setWatched(video_id, True);
			video_thumb = getVideoThumbnail(video);
			xbmcVideo = getXbmcVideoFromVideo(video, video_thumb);
			if (xbmcVideo != None):
				xbmcPlaylist.add(xbmcVideo["url"], xbmcVideo["listitem"]);
					
	xbmc.executebuiltin("Container.Refresh");
	
	# Closing progress dialog
	pDialog.update(100, _(30005));
	pDialog.close();
	xbmc.Player().play(xbmcPlaylist);
	
def playVideo(video_id):
	iframe = fetchUrl(thenoite_urls["video_url"].replace("$videoId", video_id));
	video = parseMediaInfo(iframe);
	
	if (ga["enabled"]):
		tracker.send("event", "Usage", "Play Video", "unique", screenName="Play Screen");
	
	# Sambatech url never gave an error, so we are skipping error recovery for this part
	if ("error" in video and video["error"] == True):
		xbmc.log("["+_(30006)+"]: Unable to find video for ID "+video_id, 0);
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Play Screen");
		
		# do nothing
		toaster = xbmcgui.Dialog();
		try:
			toaster.notification(_(30006), _(30103), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30103));
		pass
	else:
		addon.setWatched(video_id, True);
		video_thumb = getVideoThumbnail(video);
		xbmcVideo = getXbmcVideoFromVideo(video, video_thumb);
		if (xbmcVideo != None):
			xbmc.Player().play(xbmcVideo["url"], xbmcVideo["listitem"]);

	xbmc.executebuiltin("Container.Refresh");
#
# starting main thread run
#
mode = args.get("mode", None);

if mode is None:
	# addon.setSetting("welcome", "");
	# addon.setSetting("0.2.1", "");
	if (addon.getSetting("welcome") == ""): 
		welcome = xbmcgui.Dialog();
		opt = welcome.yesno(_(30301), _(30302), None, None, _(30303), _(30304));
		if (opt == True):
			addon.setSetting("analytics", "true");
		else:
			addon.setSetting("analytics", "false");
		addon.setSetting("welcome", "True");
		
		try:
			Tracker
		except NameError:
			from UniversalAnalytics import Tracker;
			tracker = Tracker.create(ga["UA"]);
			tracker.set("appName", ga["appName"]);
			tracker.set("appVersion", ga["appVersion"]);
			tracker.set("appId", ga["appId"]);
			if (addon.getSetting("uuid") == ""):
				addon.setSetting("uuid", tracker.params["cid"]);
			else:
				tracker.set("clientId", addon.getSetting("uuid"));
			
		
		tracker.send("event", "Usage", "install", screenName="Welcome");
	elif (addon.getSetting("0.2.1") == ""):
		dialog = xbmcgui.Dialog();
		dialog.ok(_(30305), _(30306));
		addon.setSetting("0.2.1", "True");
		
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Main Menu")
		
	# saving the initial video per page to reset pagination when it changes
	addon.setSetting("saved.video.perpage", addon.getSetting("video.perpage"));

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
			toaster.notification(_(30006), _(30102), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30102));
		pass
	else:
		# displaying each video category from The Noite website
		for menuItem in menu["medias"]:
			url = makeUrl({"mode" : "listitems", "author" : menuItem["author"], "title" : menuItem["title"].encode('utf8'), "thumb" : menuItem["thumbnail"]});
		
			li = xbmcgui.ListItem(menuItem["title"], iconImage=menuItem["thumbnail"]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);

	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "listitems"):
	xbmcplugin.setContent(addon_handle, 'episodes');
	
	authorId = args.get("author")[0];
	if (int(authorId) == 0):
		authorId = "";
	
	currentPage = args.get("page", ["0"])[0]
	currentSubPage = int(args.get("sub-page", ["0"])[0]);
	videosPerSubPage = int(addon.getSetting("video.perpage") or "100");
	
	# if user changed videos per page, reset pagination
	if (addon.getSetting("video.perpage") != addon.getSetting("saved.video.perpage")):
		addon.setSetting("saved.video.perpage", addon.getSetting("video.perpage"));
		currentPage = "0";
		currentSubPage = 0;
	
	url = thenoite_urls["media_api"].replace("$authorId", authorId).replace("$page", currentPage);
	
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Second Menu - "+args.get("title")[0]+" - Page "+currentPage);
	
	index = fetchUrl(url);
	videos = json.loads(index);

	# trying to recover from sbt api error
	saved = False;
	if ("error" in videos):
		log(str(videos["error"]));
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Second Menu - "+args.get("title")[0]);
	
		if (myCache.has_key(url)):
			log("Trying to recover from API Error");
			videos = json.loads(myCache[url]["data"]);
			if ("error" in videos):
				log("Error was cached, clearing cache");
				clearCacheFor(url);
			else:
				log("Recovered from error");
				saved = True;
	
	if (int(currentPage) > 0 or currentSubPage > 0):
		if (currentSubPage > 0):
			# decrement sub page
			url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage-1});
		else:
			prevCurrentSubPage = 100 / videosPerSubPage - 1;
			# decrement current page
			url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : (int(currentPage)-1), "updating" : "true", "sub-page" : prevCurrentSubPage});
	
		li = xbmcgui.ListItem(_(30202), iconImage=args.get("thumb")[0]);
		li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
	else:
		url = makeUrl({"mode" : "refresh-listing", "url" : url});
	
		li = xbmcgui.ListItem(_(30204), iconImage=args.get("thumb")[0]);
		li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
		
	if ("error" in videos and saved == False):
		# do nothing
		toaster = xbmcgui.Dialog();
		try:
			toaster.notification(_(30006), _(30101), xbmcgui.NOTIFICATION_WARNING, 3000);
		except AttributeError:
			toaster.ok(_(30006), _(30101));
		pass
	elif ((authorId in thenoite_authors_slug) and thenoite_authors_slug[authorId] == "naintegra"):
		# grouping urls by episodes
		episodes = {};
		videoCount = 0;
		for video in videos["videos"][currentSubPage*videosPerSubPage:]:
			#get the episode number by the secondurl info
			if ("secondurl" in video and video["secondurl"].strip() != ""):
				# correcting typos
				video["secondurl"] = video["secondurl"].replace("//", "/").strip(); 
				episode = [video["secondurl"]];
			else:
				#try to get the episode date from the title
				episode = re.compile("\(?(\d\d\/\d\d\/\d\d)\)?").findall(video["title"]);
				
				if (len(episode) == 0): # invent a random date
					if ("publishdatestring" in video and video["publishdatestring"].strip() != ""):
						#get the day from the publish date string
						from datetime import datetime, timedelta;
						publishdate = datetime(*(time.strptime(video["publishdatestring"], "%Y-%m-%dT%H:%M:%S")[0:6]));
						publishdate = publishdate - timedelta(1);
						episode = [publishdate.strftime("%d/%m/%y")];
					else:
						#random generate date string
						episode = [str(random.randint(50,99)) + "/" + str(random.randint(50,99)) + "/" + str(random.randint(50,99))];
			
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
				
			videoCount = videoCount + 1;
			if (videoCount == videosPerSubPage):
				break;
	
		if (randomButtonEnabled):
			addon.setSetting("random.dump", pickle.dumps(episodes));
			url = url = makeUrl({"mode" : "randomitem", "option" : "episode", "title" : args.get("title")[0], "page" : currentPage});
	
			li = xbmcgui.ListItem(_(30203), iconImage='special://home/addons/plugin.video.sbt-thenoite/question-mark.jpg');
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
	
		# listing each episode part
		for episode in sorted(episodes, key=invertDates, reverse=True):
			video_ids = [];
			for video in episodes[episode]:
				video_ids.append(video["id"]);
		
			whole_url = makeUrl({"mode" : "episodeurl", "play_episode" : json.dumps(video_ids)});
		
			for video in episodes[episode]:
				url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
			
				li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

				contextMenu = [];
				if (addon.getWatched(video["id"])):
					li.setInfo("video", {"playcount" : 1});
					updateSeenUrl = makeUrl({"mode" : "mark-unseen", "video_id" : video["id"]});
					contextMenu.append((_(30009), 'XBMC.RunPlugin('+updateSeenUrl+')'));
				else:
					updateSeenUrl = makeUrl({"mode" : "mark-seen", "video_id" : video["id"]});
					contextMenu.append((_(30008), 'XBMC.RunPlugin('+updateSeenUrl+')'));

				contextMenu.append((_(30001), 'XBMC.RunPlugin('+whole_url+')'));
				li.addContextMenuItems(contextMenu);
				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
		
		#add a Next Page button at the end
		if (videoCount == videosPerSubPage):
			if ((currentSubPage+1)*videosPerSubPage == 100):
				# increment currentPage
				url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : (int(currentPage)+1), "updating" : "true"});
			else:
				# increment currentSubPage
				url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage+1});
	
			li = xbmcgui.ListItem(_(30201), iconImage=args.get("thumb")[0]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
		
	else:
		if (randomButtonEnabled):
			addon.setSetting("random.dump", pickle.dumps(videos["videos"]));
			url = url = makeUrl({"mode" : "randomitem", "option" : "video", "title" : args.get("title")[0], "page" : currentPage});
	
			li = xbmcgui.ListItem(_(30203), iconImage='special://home/addons/plugin.video.sbt-thenoite/question-mark.jpg');
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
	
		videoCount = 0;
		for video in videos["videos"][currentSubPage*videosPerSubPage:]:
			url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
	
			li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');
			if (addon.getWatched(video["id"])):
				li.setInfo("video", {"playcount" : 1});
				updateSeenUrl = makeUrl({"mode" : "mark-unseen", "video_id" : video["id"]});
				li.addContextMenuItems([(_(30009), 'XBMC.RunPlugin('+updateSeenUrl+')')]);
			else:
				updateSeenUrl = makeUrl({"mode" : "mark-seen", "video_id" : video["id"]});
				li.addContextMenuItems([(_(30008), 'XBMC.RunPlugin('+updateSeenUrl+')')]);

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
			videoCount = videoCount + 1;
			if (videoCount == videosPerSubPage):
				break;
			
		#add a Next Page button at the end
		if (videoCount == videosPerSubPage):
			if ((currentSubPage+1)*videosPerSubPage == 100):
				# increment currentPage
				url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : (int(currentPage)+1), "updating" : "true"});
			else:
				# increment currentSubPage
				url = makeUrl({"mode" : "listitems", "author" : args.get("author")[0], "title" : args.get("title")[0], "thumb" : args.get("thumb")[0], "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage+1});
	
			li = xbmcgui.ListItem(_(30201), iconImage=args.get("thumb")[0]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
	
	#if user is using pagination, updateListing is True
	updateListing = False if args.get("updating", ["false"])[0] == "false" else True;
	xbmcplugin.endOfDirectory(addon_handle, True, updateListing);
elif (mode[0] == "videourl"):
	playVideo(args.get("play_video")[0]);
elif (mode[0] == "episodeurl"):
	videos_ids = json.loads(args.get("play_episode")[0]);
	playVideoList(videos_ids);
elif (mode[0] == "randomitem"):
	currentPage = args.get("page", ["0"])[0]
	
	if (ga["enabled"]):
		tracker.send("event", "Randonizer", args.get("title")[0], screenName="Second Menu - "+args.get("title")[0]+" - Page "+currentPage);
	
	option = args.get("option", [""])[0];
	if (option == "episode"):
		episodes = pickle.loads(addon.getSetting("random.dump"));
		randomIndex = random.choice(episodes.keys());
		videos_ids = [];
		for video in episodes[randomIndex]:
			videos_ids.append(video["id"]);
				
		playVideoList(videos_ids);

	elif (option == "video"):
		videos = pickle.loads(addon.getSetting("random.dump"));
		video = random.choice(videos);
		playVideo(video["id"]);
elif (mode[0] == "mark-unseen"):
	videoId = args.get("video_id", [""])[0];
	if (videoId != ""):
		addon.setWatched(videoId, False);
	xbmc.executebuiltin("Container.Refresh");
elif (mode[0] == "mark-seen"):
	videoId = args.get("video_id", [""])[0];
	if (videoId != ""):
		addon.setWatched(videoId, True);
	xbmc.executebuiltin("Container.Refresh");
elif (mode[0] == "refresh-listing"):
	url = args.get("url", [""])[0];
	if (url != ""):
		clearCacheFor(url);
	xbmc.executebuiltin("Container.Refresh");