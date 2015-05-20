import sys;
import xbmc;
import xbmcgui;
import xbmcplugin;
import xbmcaddon;
import xbmcvfs;
import urllib;
import urlparse;
import json;
import re;
import base64;
import pickle;
import random;
from http import network;
import settings;

# getting addon strings
addon = settings.Settings("plugin.video.sbtvideos");
_ = addon.getLocalizedString;
ga = {
	"enabled" : False,
	"UA" : 'UA-18146963-3',
	"appName" : addon.getAddonInfo("name"),
	"appVersion" : addon.getAddonInfo("version"),
	"appId" : addon.getAddonInfo("id")
}
randomButtonEnabled = False if (addon.getSetting("randomButtonEnabled") == "false") else True;
playFullEpisodesByDefault = False if (addon.getSetting("playFullEpisodesByDefault") == "false") else True;

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
urls = {};
urls["sbtvideos"] = "http://www.sbt.com.br/sbtvideos/";
urls["playlist"] = "http://api.sbt.com.br/1.5.0/playlists/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id&idsite=211&idSiteArea=1068&limit=1&description=$programId";
urls["menu"] = "http://api.sbt.com.br/1.5.0/medias/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,description,thumbnail,author,opcional&idsite=211&idSiteArea=1068&idPlaylist=$playlistId&limit=100&orderby=ordem&sort=ASC";
urls["media"] = "http://api.sbt.com.br/1.5.0/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,idcategory,idprogram,program,thumbnail,publishdatestring,secondurl,playerkey,total&program=$programId&category=$authorId&limit=100&orderBy=publishdate&sort=desc&page=$page";
urls["video"] = "http://fast.player.liquidplatform.com/pApiv2/embed/25ce5b8513c18a9eae99a8af601d0943/$videoId";

# Unblock Brazil URL
unblockBrazilHome = "http://brazilunblock.info/";
unblockBrazilUrl = unblockBrazilHome+"browse.php?u=$videoUrl";

group_by_episodes = {
	"4526" : "naintegra"
};

base_url = sys.argv[0];
addon_handle = int(sys.argv[1]);
args = urlparse.parse_qs(sys.argv[2][1:]);

def log(msg):
	msg = "["+_(30006)+"]: "+msg;
	msg = msg.encode("utf-8");
	xbmc.log(msg, 0);

def logError(msg):
	msg = "Error: "+str(msg);
	log(msg);
	# do nothing
	toaster = xbmcgui.Dialog();
	try:
		toaster.notification(_(30006), _(30101), xbmcgui.NOTIFICATION_WARNING, 3000);
	except AttributeError:
		toaster.ok(_(30006), _(30101));
	pass
	
def invertDates(date):
	date = date.split("/");
	date.reverse();
	return "/".join(date);

def makeUrl(query = {}):
	return base_url + "?" + urllib.urlencode(query);

def parseMediaInfo(html):
	match = re.compile("window.mediaJson = (.+?);").findall(html);
	if len(match) > 0:
		log("found media json: "+match[0]);
		return json.loads(match[0]);
		
	match = re.compile("window.mediaToken = (.+?);").findall(html);
	if len(match) > 0:
		log("found media token: "+match[0]);
		# getting max-width from body tag
		maxWidth = re.compile("<body .*max-width:(.*);.*>").findall(html);
		log("Found maxWidth "+str(maxWidth));
		if len(maxWidth) > 0:
			# xbmc.log("["+_(30006)+"]: Found token "+match[0], 0);
			maxWidth = maxWidth[0].strip().replace("px", "");
			# xbmc.log("["+_(30006)+"]: max-width "+maxWidth, 0);
			maxWidth = int((int(maxWidth) ^ 345) - 1E4) + 1;
			discard = match[0][0:maxWidth]; #keeping this for debug purposes
			log("Will discard "+discard);
			
			encodedToken = match[0][maxWidth:-maxWidth];
			log("Encoded token "+encodedToken);
			
			if(len(encodedToken) % 4 == 2):
				encodedToken = encodedToken + "==";
			elif(len(encodedToken) % 4 == 3):
				encodedToken = encodedToken + "=";
				
			return json.loads(base64.b64decode(encodedToken));

	return None;

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
		if (deliveryRules["rule"]["ruleName"] == "r1" or 
			deliveryRules["rule"]["ruleName"] == "default"):
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
				if (addon.getSetting("useUnblockBrazil") == "true"):
					header = {
						"Host" : "brazilunblock.info"
					};
					ret["url"] = unblockBrazilUrl.replace("$videoUrl", urllib.quote(videoUrl))+"|"+urllib.urlencode(header);
				else:
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
		
		iframe = network.fetchUrl(urls["video"].replace("$videoId", video_id));
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
					
	# Closing progress dialog
	pDialog.update(100, _(30005));
	pDialog.close();
	if (addon.getSetting("useUnblockBrazil") == "true"):
		# first we cheat XMBC into saving the correct cookie from Unblock Brazil website
		xbmc.Player().play(unblockBrazilHome);
		# then we pass the redirected video url for XBMC
	
	xbmc.Player().play(xbmcPlaylist);
	xbmc.executebuiltin("Container.Refresh");
	
def playVideo(video_id):
	log("video url: "+urls["video"].replace("$videoId", video_id));
	iframe = network.fetchUrl(urls["video"].replace("$videoId", video_id));
	video = parseMediaInfo(iframe);
	
	if (ga["enabled"]):
		tracker.send("event", "Usage", "Play Video", "unique", screenName="Play Screen");
	
	# Sambatech url never gave an error, so we are skipping error recovery for this part
	log("video: "+json.dumps(video));
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
			if (addon.getSetting("useUnblockBrazil") == "true"):
				# first we cheat XMBC into saving the correct cookie from Unblock Brazil website
				xbmc.Player().play(unblockBrazilHome);
				# then we pass the redirected video url for XBMC
		
			xbmc.Player().play(xbmcVideo["url"], xbmcVideo["listitem"]);
	
	xbmc.executebuiltin("Container.Refresh");
#
# starting main thread run
#
mode = args.get("mode", None);

if mode is None:
	from bs4 import BeautifulSoup;
	# addon.setSetting("welcome", "");
	# addon.setSetting("0.1.2", "");
	if (addon.getSetting("welcome") == ""): 
		welcome = xbmcgui.Dialog();
		opt = welcome.yesno(_(30301), _(30302), _(30303), None, _(30305), _(30306));
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
	elif (addon.getSetting("0.1.2") == ""):
		dialog = xbmcgui.Dialog();
		dialog.ok(_(30307), _(30308), _(30309), _(30310));
		addon.setSetting("0.1.2", "True");
		
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Main Menu")

	xbmcplugin.setContent(addon_handle, 'tvshows');
	
	# displaying each tv show category from SBT Videos Website
	index = network.fetchUrl(urls["sbtvideos"]);
	soup = BeautifulSoup(index);
	topmenu = soup.find(id="ContentTopMenu");
	if (topmenu):
		for li in topmenu.find_all("li"):
			if "boxSearch" not in li.get("class"):
				url = makeUrl({"mode" : "listprogram", "rel" : li.get("rel"), "title" : li.get_text().strip().encode("utf8")});
				li = xbmcgui.ListItem(li.get_text().strip(), iconImage="special://home/addons/plugin.video.sbtvideos/default-image.jpg");
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');
				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);

	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "listprogram"):
	from bs4 import BeautifulSoup;
	xbmcplugin.setContent(addon_handle, 'tvshows');
	rel = args.get("rel")[0];
	categoryTitle = args.get("title", [""])[0];
	
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Category Menu - "+categoryTitle);
	
	# displaying each tv show from selected category
	index = network.fetchUrl(urls["sbtvideos"]);
	soup = BeautifulSoup(index);
	categorybox = soup.find(id=rel);
	if (categorybox):
		for li in categorybox.find_all("li"):
			if li.get("title") > 0:
				programId = re.compile("programa/(\d*)/").search(li.a.get("href"));
				if (programId):
					url = makeUrl({"mode" : "programmenu", "programId" : programId.group(1).encode("utf8"), "title" : li.a.get_text().strip().encode("utf8")});
					programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId.group(1)+"/";
					if (xbmcvfs.exists(programImgFolder)):
						li = xbmcgui.ListItem(li.a.get_text().strip(), iconImage=programImgFolder+"thumb.jpg");
						li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
					else:
						li = xbmcgui.ListItem(li.a.get_text().strip(), iconImage="special://home/addons/plugin.video.sbtvideos/default-image.jpg");
						li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');
						
					xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
				else:
					logError("Couldn't find program id for "+li.a.get("href"));
	
	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "programmenu"):
	programId = args.get("programId")[0];
	programTitle = args.get("title", [""])[0];
	
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Program Menu - "+programTitle);

	# saving the initial video per page to reset pagination when it changes
	addon.setSetting("saved.video.perpage", addon.getSetting("video.perpage"));
		
	index = network.fetchUrl(urls["playlist"].replace("$programId", str(programId)));
	obj = json.loads(index);	
	# log("programId: "+programId);
	if "playlists" in obj:
		xbmcplugin.setContent(addon_handle, 'tvshows');
		
		playlistId = str(obj["playlists"][0]["id"]);
		# log("playlistId: "+playlistId);
		index = network.fetchUrl(urls["menu"].replace("$playlistId", playlistId));
		menu = json.loads(index);
	
		# try to recover from sbt api error
		saved = False;
		if "error" in menu:
			index = network.cache.getData(urls["menu"].replace("$playlistId", playlistId));
			if (index):
				menu = json.loads(index);
				if "error" in menu:
					network.cache.delKey(urls["menu"].replace("$playlistId", playlistId));
				else:
					saved = True;
	
		if ("error" in menu and saved == False):
			logError(menu["error"]);
		else:
			# displaying each video category from the selected program
			for menuItem in menu["medias"]:
				url = makeUrl({"mode" : "listitems", "author" : menuItem["author"], "programId" : programId, "title" : menuItem["title"].encode('utf8'), "thumb" : menuItem["thumbnail"]});
				li = xbmcgui.ListItem(menuItem["title"], iconImage=menuItem["thumbnail"]);
				programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
				if (xbmcvfs.exists(programImgFolder)):
					li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
				else:
					li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');
				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);

		xbmcplugin.endOfDirectory(addon_handle);
	else:
		mode[0] = "listitems";

# the states are separated in here because there is a case where the user goes to 'programmenu'
# and then immediately to 'listitems'
if mode is None:
	pass
elif (mode[0] == "listitems"):
	xbmcplugin.setContent(addon_handle, 'episodes');
	
	programId = args.get("programId")[0];
	authorId = args.get("author", [""])[0];
	if (authorId != "" and int(authorId) == 0):
		authorId = "";
	currentPage = args.get("page", ["0"])[0]
	currentSubPage = int(args.get("sub-page", ["0"])[0]);
	videosPerSubPage = int(addon.getSetting("video.perpage") or "100");
	categoryTitle = args.get("title", [_(30007)])[0];
	categoryThumb = args.get("thumb", ["DefaultFolder.png"])[0];
	
	# if user changed videos per page, reset pagination
	if (addon.getSetting("video.perpage") != addon.getSetting("saved.video.perpage")):
		addon.setSetting("saved.video.perpage", addon.getSetting("video.perpage"));
		currentPage = "0";
		currentSubPage = 0;
	
	url = urls["media"].replace("$programId", programId).replace("$authorId", authorId).replace("$page", currentPage);
	
	if (ga["enabled"]):
		tracker.send("screenview", screenName="Second Menu - "+categoryTitle+" - Page "+currentPage);
	
	index = network.fetchUrl(url);
	videos = json.loads(index);

	# trying to recover from sbt api error
	saved = False;
	if ("error" in videos):
		log(str(videos["error"]));
		
		# taking note from the amount of errors the SBT API may throw
		if (ga["enabled"]):
			tracker.send("event", "Usage", "error", screenName="Second Menu - "+categoryTitle);
	
		index = network.cache.getData(url)
		if (index):
			videos = json.loads(index);
			if ("error" in videos):
				network.cache.delKey(url);
			else:
				saved = True;
	
	if (int(currentPage) > 0 or currentSubPage > 0):
		if (currentSubPage > 0):
			# decrement sub page
			url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage-1});
		else:
			prevCurrentSubPage = 100 / videosPerSubPage - 1;
			# decrement current page
			url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : (int(currentPage)-1), "updating" : "true", "sub-page" : prevCurrentSubPage});
	
		li = xbmcgui.ListItem(_(30202), iconImage=categoryThumb);
		programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
		if (xbmcvfs.exists(programImgFolder)):
			li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
		else:
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
	else:
		url = makeUrl({"mode" : "refresh-listing", "url" : url});
	
		li = xbmcgui.ListItem(_(30204), iconImage=categoryThumb);
		programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
		if (xbmcvfs.exists(programImgFolder)):
			li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
		else:
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
		
	if ("error" in videos and saved == False):
		logError(str(videos["error"]));
	elif (authorId in group_by_episodes):
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
				
				if (len(episode) == 0):
					if ("publishdatestring" in video and video["publishdatestring"].strip() != ""):
						#get the day from the publish date string
						from datetime import datetime, timedelta;
						import time;
						publishdate = datetime(*(time.strptime(video["publishdatestring"], "%Y-%m-%dT%H:%M:%S")[0:6]));
						publishdate = publishdate - timedelta(1);
						episode = [publishdate.strftime("%d/%m/%y")];
					else:
						# invent a random date
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
	
			programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
			if (xbmcvfs.exists(programImgFolder)):
				li = xbmcgui.ListItem(_(30203), iconImage=programImgFolder+'question-mark.jpg');
				li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
			else:
				li = xbmcgui.ListItem(_(30203), iconImage='special://home/addons/plugin.video.sbtvideos/question-mark.jpg');
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');
			
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
	
		# listing each episode part
		for episode in sorted(episodes, key=invertDates, reverse=True):
			video_ids = [];
			for video in episodes[episode]:
				video_ids.append(video["id"]);
		
			whole_url = makeUrl({"mode" : "episodeurl", "play_episode" : json.dumps(video_ids)});
		
			for video in episodes[episode]:
				li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
				programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
				if (xbmcvfs.exists(programImgFolder)):
					li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
				else:
					li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');
					
				contextMenu = [];
				if (addon.getWatched(video["id"])):
					li.setInfo("video", {"playcount" : 1});
					updateSeenUrl = makeUrl({"mode" : "mark-unseen", "video_id" : video["id"]});
					contextMenu.append((_(30009), 'XBMC.RunPlugin('+updateSeenUrl+')'));
				else:
					updateSeenUrl = makeUrl({"mode" : "mark-seen", "video_id" : video["id"]});
					contextMenu.append((_(30008), 'XBMC.RunPlugin('+updateSeenUrl+')'));
				
				url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
				if (playFullEpisodesByDefault):
					contextMenu.append((_(30010), 'XBMC.RunPlugin('+url+')'));
					url = whole_url;
				else:
					contextMenu.append((_(30001), 'XBMC.RunPlugin('+whole_url+')'));
				
				li.addContextMenuItems(contextMenu);
				xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
				
		#add a Next Page button at the end
		if (videoCount == videosPerSubPage):
			if ((currentSubPage+1)*videosPerSubPage == 100):
				# increment currentPage
				url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : (int(currentPage)+1), "updating" : "true"});
			else:
				# increment currentSubPage
				url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage+1});
		
			li = xbmcgui.ListItem(_(30201), iconImage=categoryThumb);
			programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
			if (xbmcvfs.exists(programImgFolder)):
				li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
			else:
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);
		
	else:
		if (randomButtonEnabled):
			addon.setSetting("random.dump", pickle.dumps(videos["videos"]));
			url = url = makeUrl({"mode" : "randomitem", "option" : "video", "title" : categoryTitle, "page" : currentPage});
	
			programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
			if (xbmcvfs.exists(programImgFolder)):
				li = xbmcgui.ListItem(_(30203), iconImage=programImgFolder+'question-mark.jpg');
				li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
			else:
				li = xbmcgui.ListItem(_(30203), iconImage='special://home/addons/plugin.video.sbtvideos/question-mark.jpg');
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li);
	
		videoCount = 0;
		for video in videos["videos"][currentSubPage*videosPerSubPage:]:
			url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
	
			li = xbmcgui.ListItem(video["title"], iconImage=video["thumbnail"]);
			programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
			if (xbmcvfs.exists(programImgFolder)):
				li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
			else:
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

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
				url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : (int(currentPage)+1), "updating" : "true"});
			else:
				# increment currentSubPage
				url = makeUrl({"mode" : "listitems", "programId" : programId, "author" : authorId, "title" : categoryTitle, "thumb" : categoryThumb, "page" : currentPage, "updating" : "true", "sub-page" : currentSubPage+1});
		
			li = xbmcgui.ListItem(_(30201), iconImage=categoryThumb);
			programImgFolder = "special://home/addons/plugin.video.sbtvideos/program/"+programId+"/";
			if (xbmcvfs.exists(programImgFolder)):
				li.setProperty('fanart_image', programImgFolder+'fanart.jpg');
			else:
				li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbtvideos/fanart.jpg');

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
	currentPage = args.get("page", ["0"])[0];
	title = args.get("title", [_(30007)])[0];
	
	if (ga["enabled"]):
		tracker.send("event", "Randonizer", title, screenName="Second Menu - "+title+" - Page "+currentPage);
	
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
		network.cache.delKey(url);
	xbmc.executebuiltin("Container.Refresh");
