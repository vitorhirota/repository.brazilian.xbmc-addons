import sys;
import urllib;
import urllib2;
import urlparse;
import json;
import re;

thenoite_urls = {};
thenoite_urls['na_integra'] = 'http://api.sbt.com.br/1.4.5/videos/key=AE8C984EECBA4F7F835C585D5CB6AB4B&fields=id,title,thumbnail,publishdate,secondurl&program=400&limit=100&orderBy=publishdate&category=4526&sort=desc';

video_url = 'http://fast.player.liquidplatform.com/pApiv2/embed/25ce5b8513c18a9eae99a8af601d0943/$videoId';
base_url = sys.argv[0];
addon_handle = int(sys.argv[1]);
args = urlparse.parse_qs(sys.argv[2][1:]);

def fetchUrl(url):
	req = urllib2.Request(url);
	response = urllib2.urlopen(req);
	data = response.read();
	response.close();
	return data;

def makeUrl(query = {}):
	return base_url + "?" + urllib.urlencode(query);
	
def invertDates(date):
	date = date.split("/");
	date.reverse();
	return "/".join(date);

mode = args.get("mode", None);

if mode is None:
	index = fetchUrl(thenoite_urls['na_integra']);
	videos = json.loads(index);
	
	# grouping urls by episodes
	episodes = {};
	for video in videos["videos"]:
		episode = re.compile("The Noite \(?(.+?)\)? ").findall(video["title"]);
		if (episode[0] in episodes):
			episodes[episode[0]].append(video);
		else:
			episodes[episode[0]] = [video];
	
	for episode in sorted(episodes, key=invertDates, reverse=True):
		video_ids = [];
		for video in episodes[episode]:
			video_ids.append(video["id"]);
		
		whole_url = makeUrl({"mode" : "episodeurl", "play_episode" : "["+",".join(video_ids)+"]"});
		
		for video in episodes[episode]:
			url = makeUrl({"mode" : "videourl", "play_video" : video["id"]});
			
			
elif (mode[0] == "videourl"):
	iframe = fetchUrl(args.get("play_video")[0]);
	match = re.compile("window.mediaJson = (.+?);").findall(iframe);
	if match[0]:
		video = json.loads(match[0]);
		
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
							
						# xbmcplugin.addDirectoryItem(handle=addon_handle, url=output["url"], listitem=listitem)
						xbmc.Player().play(output["url"], listitem);
						break;
				break;