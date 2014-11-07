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

# getting settings strings
settings = xbmcaddon.Addon("plugin.video.sbt-thenoite");
_ = settings.getLocalizedString;

# setting SBT urls
thenoite_urls = {};
thenoite_urls["menu_api"] = "http://api.sbt.com.br/1.4.5/medias/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,thumbnail,author&idsite=198&idSiteArea=1011&limit=100&orderBy=ordem&sort=asc";
thenoite_urls["media_api"] = "http://api.sbt.com.br/1.4.5/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,thumbnail,publishdate,secondurl&program=400&limit=100&orderBy=publishdate&category=$authorId&sort=desc";
thenoite_urls["video_url"] = 'http://fast.player.liquidplatform.com/pApiv2/embed/25ce5b8513c18a9eae99a8af601d0943/$videoId';

thenoite_authors_slug = {};
thenoite_authors_slug["4526"] = "naintegra";

base_url = sys.argv[0];
addon_handle = int(sys.argv[1]);
args = urlparse.parse_qs(sys.argv[2][1:]);

def invertDates(date):
	date = date.split("/");
	date.reverse();
	return "/".join(date);

def fetchUrl(url):
	req = urllib2.Request(url);
	response = urllib2.urlopen(req);
	data = response.read();
	response.close();
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

mode = args.get("mode", None);

if mode is None:
	xbmcplugin.setContent(addon_handle, 'tvshows');
	
	index = fetchUrl(thenoite_urls["menu_api"]);
	menu = json.loads(index);
	
	if ("error" in menu):
		xbmc.log("["+_(30006)+"]: "+str(menu["error"]), 0);
		
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
			url = makeUrl({"mode" : "listitems", "author" : menuItem["author"]});
		
			li = xbmcgui.ListItem(menuItem["title"], iconImage=menuItem["thumbnail"]);
			li.setProperty('fanart_image', 'special://home/addons/plugin.video.sbt-thenoite/fanart.jpg');
			xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True);

	xbmcplugin.endOfDirectory(addon_handle);
elif (mode[0] == "listitems"):
	xbmcplugin.setContent(addon_handle, 'episodes');
	
	authorId = args.get("author")[0];
	index = fetchUrl(thenoite_urls["media_api"].replace("$authorId", authorId));
	videos = json.loads(index);
	
	if ("error" in videos):
		xbmc.log("["+_(30006)+"]: "+str(videos["error"]), 0);
		
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
		
		for deliveryRules in video["deliveryRules"]:
			if (deliveryRules["rule"]["ruleName"] == "r1"):
				for output in deliveryRules["outputList"]:
					if (output["labelText"] == "480p"):
						listitem = xbmcgui.ListItem(video["title"]);
						listitem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
						if (video_thumb != None): # setting thubmnail and icon image, if any
							listitem.setIconImage(video_thumb["url"]);
							listitem.setThumbnailImage(video_thumb["url"]);
							
						xbmc.Player().play(output["url"], listitem);
						break;
				break;
	else:
		xbmc.log("["+_(30006)+"]: Unable to find video for ID "+args.get("play_video")[0], 0);
		
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
		
			for deliveryRules in video["deliveryRules"]:
				if (deliveryRules["rule"]["ruleName"] == "r1"):
					for output in deliveryRules["outputList"]:
						if (output["labelText"] == "480p"):
							listitem = xbmcgui.ListItem(video["title"]);
							listitem.setInfo("video", {"Title" : video["title"], "Plot" : video["description"]});
							if (video_thumb != None): # setting thubmnail and icon image, if any
								listitem.setIconImage(video_thumb["url"]);
								listitem.setThumbnailImage(video_thumb["url"]);
							
							xbmcPlaylist.add(output["url"], listitem);
							break;
					break;
		else:
			xbmc.log("["+_(30006)+"]: Unable to find video for ID "+args.get("play_video")[0], 0);
		
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