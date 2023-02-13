from flask import Flask,abort,redirect,Response
from jinja2 import Template
import requests
import os
import json
import sys
app = Flask(__name__)

podcastTpl = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
<channel>
<title>{{basicInfoData['Name']|e}}</title>
<link>https://github.com/zhimiaoli/emby2podcasts</link>
<language>zh-cn</language>
<itunes:subtitle>{{basicInfoData['Name']|e}}</itunes:subtitle>
<itunes:author>{{basicInfoData.get("AlbumArtist","")}}</itunes:author>
<itunes:image href="{{emby_file_server}}/emby/Items/{{basicInfoData["Id"]}}/Images/Primary"/>
<itunes:summary><![CDATA[ {{basicInfoData.get("Overview","")}}]]></itunes:summary>
<description><![CDATA[{{basicInfoData.get("Overview","")}}]]></description>
<itunes:owner>
    <itunes:name>Private Use</itunes:name>
    <itunes:email>me@example.com</itunes:email>
</itunes:owner>
<itunes:explicit>no</itunes:explicit>
{% set count = namespace(value=1) %}
{% for ep in eps %}
<item>
    <title>{{ep.get("IndexNumber",count.value)}}{{"."+ep["Name"]|e}}</title>
    <itunes:summary><![CDATA[ {{ep.get("Overview","")}}]]></itunes:summary>
    <description><![CDATA[ {{ep.get("Overview","")}}]]></description>
    <enclosure url="{{baseURL}}{{'/audio/'+ep['Id']}}.{{ep['Container']}}" type="audio/mpeg"></enclosure>
    <pubDate>Tue, 07 Feb 2023 16:01:07 +0000</pubDate>
    <itunes:author>{{basicInfoData.get("AlbumArtist","Unknow")}}</itunes:author>
    <itunes:duration>{{ep["RunTimeTicks"]/10000000 | int}}</itunes:duration>
    <itunes:explicit>no</itunes:explicit>
    <guid>{{ep["ServerId"]}}-{{ep["Id"]}}</guid>
    {% set count.value = count.value + 1 %}
</item> 
{% endfor %}
</channel>
</rss>
"""

def loadConfig():
    if os.path.exists("config.json"): 
        configfilename = "config.json"
        configData = open(configfilename,"r",encoding="utf-8").read()
        print("using config.json")
        return json.loads(configData)
    elif os.path.exists("/config/config.json"):
        configfilename = "/config/config.json"
        configData = open(configfilename,"r",encoding="utf-8").read()
        print("using /config/config.json")
        return json.loads(configData)
    else:
        sys.exit(0)

config = loadConfig()

@app.route('/')
def hello_world():
    return 'Hello, It works!'


@app.route("/podcast/<id>")
def podcast(id):
    # 生成podcast的播客
    r = requests.session()
    basicInfo = r.get("{emby_api_server}/emby/Users/{user_id}/Items/{id}?api_key={api_key}".format(emby_api_server=config["emby_api_server"],user_id=config["user_id"],id=id,api_key=config["api_key"]))
    eposides = r.get("{emby_api_server}/emby/Items?ParentId={id}&api_key={api_key}&Fields=BasicSyncInfo%2CCanDelete%2CContainer%2CPrimaryImageAspectRatio%2COverview&ImageTypeLimit=1".format(emby_api_server=config["emby_api_server"],api_key=config["api_key"],id=id))
    if basicInfo.status_code == 200 and eposides.status_code == 200:
        basicInfoData = basicInfo.json()
        eposidesList = eposides.json()
        xmlStr = Template(podcastTpl).render(basicInfoData=basicInfoData,eps=eposidesList["Items"],baseURL = config["baseURL"],emby_file_server=config["emby_file_server"])
    else:
        return abort(basicInfo.status_code)
    return Response(xmlStr, mimetype='application/xml')

@app.route("/audio/<audiofile>")
def serverAudio(audiofile):
    audioid,container = audiofile.split(".")
    if container == "mp3" or container == "mp4":
        print("mp3 container, direct stream.")
        return redirect("{emby_file_server}/emby/Audio/{audioid}/stream?api_key={api_key}&static=true".format(api_key=config["api_key"],emby_file_server=config["emby_file_server"],audioid=audioid),302)
    else:
        print("other container, transcoding.")
        return redirect("{emby_file_server}/emby/Audio/{audioid}/stream.mp3?api_key={api_key}".format(api_key=config["api_key"],emby_file_server=config["emby_file_server"],audioid=audioid),302)