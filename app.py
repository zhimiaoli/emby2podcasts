from flask import Flask,abort,redirect,Response
from jinja2 import Template
import requests
import os
import json
import sys
from datetime import datetime,timedelta
app = Flask(__name__)

podcastTpl = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
<channel>
<title>{{basicInfoData['Name']|e}}</title>
<link>https://github.com/zhimiaoli/emby2podcasts</link>
<language>zh-cn</language>
<itunes:subtitle>{{basicInfoData['Name']|e}}</itunes:subtitle>
<itunes:author>{{basicInfoData.get("AlbumArtist","John Doe")}}</itunes:author>
<itunes:image href="{{emby_image_server}}/emby/Items/{{basicInfoData["Id"]}}/Images/Primary"/>
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
    <title>{% if ep.get("ParentIndexNumber","")%}{{ep.get("ParentIndexNumber","")}}-{% endif %}{{ep.get("IndexNumber",count.value)}}{{"."+ep["Name"]|e}}</title>
    <itunes:summary><![CDATA[ {{ep.get("Overview","")}}]]></itunes:summary>
    <description><![CDATA[ {{ep.get("Overview","")}}]]></description>
    <enclosure url="{{baseURL}}{{'/audio/'+ep['Id']}}.{{ep['Container']}}" type="{% if ep["Container"] == "m4a" %}audio/mp4{% else %}video/mpeg{% endif %}"></enclosure>
    <pubDate>{{ep["pubDate"]}} GMT</pubDate>
    <itunes:author>{{basicInfoData.get("AlbumArtist","Unknow")}}</itunes:author>
    <itunes:duration>{{(ep["RunTimeTicks"]/10000000)|int}}</itunes:duration>
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
        epindex = 1
        for ep in eposidesList["Items"]:
            if ep["Container"] == "mp4" and ep["MediaType"] == "Audio":
                ep["Container"] = "m4a"
            pubDate = datetime(2023,2,8,2,23,3) - timedelta(days=epindex)
            #using a fixed date,so no need to refresh the rss file,this is the date I finished a first working version
            #of this simple program. no timezone info was provided.
            ep["pubDate"] = pubDate.strftime("%a, %d %b %Y %H:%M:%S")
            epindex += 1
        xmlStr = Template(podcastTpl).render(basicInfoData=basicInfoData,eps=eposidesList["Items"],baseURL = config["baseURL"],
                                             emby_file_server=config["emby_file_server"],emby_image_server=config["emby_image_server"])
    else:
        return abort(basicInfo.status_code)
    return Response(xmlStr, mimetype='application/xml')

@app.route("/audio/<audiofile>")
def serverAudio(audiofile):
    audioid,container = audiofile.split(".")
    if container == "mp3" or container == "m4a":
        print("mp3 container, direct stream.")
        return redirect("{emby_file_server}/emby/Audio/{audioid}/stream?api_key={api_key}&static=true".format(api_key=config["api_key"],emby_file_server=config["emby_file_server"],audioid=audioid),302)
    if container == "mp4":
        print("mp3 container, direct stream.")
        return redirect("{emby_file_server}/emby/videos/{audioid}/stream.mp4?api_key={api_key}&static=true".format(api_key=config["api_key"],emby_file_server=config["emby_file_server"],audioid=audioid),302)
    else:
        print("other container, transcoding.")
        return redirect("{emby_file_server}/emby/Audio/{audioid}/stream.mp3?api_key={api_key}".format(api_key=config["api_key"],emby_file_server=config["emby_file_server"],audioid=audioid),302)
    
@app.route("/tv/<id>")
def tv(id):
    # 生成podcast的播客
    r = requests.session()
    basicInfo = r.get("{emby_api_server}/emby/Users/{user_id}/Items/{id}?api_key={api_key}".format(emby_api_server=config["emby_api_server"],user_id=config["user_id"],id=id,api_key=config["api_key"]))

    eposides = r.get("{emby_api_server}/emby/Items?ParentId={id}&api_key={api_key}&Recursive=true&IncludeItemTypes=Episode&Fields=BasicSyncInfo%2CContainer".format(emby_api_server=config["emby_api_server"],api_key=config["api_key"],id=id))

    if basicInfo.status_code == 200 and eposides.status_code == 200:
        basicInfoData = basicInfo.json()
        eposidesList = eposides.json()
        epindex = 1
        for ep in eposidesList["Items"]:
            pubDate = datetime(2023,2,8,2,23,3) - timedelta(days=epindex)
            #using a fixed date,so no need to refresh the rss file,this is the date I finished a first working version
            #of this simple program. no timezone info was provided.
            ep["pubDate"] = pubDate.strftime("%a, %d %b %Y %H:%M:%S")
            epindex += 1
        xmlStr = Template(podcastTpl).render(basicInfoData=basicInfoData,
                                             eps=eposidesList["Items"],
                                             baseURL = config["baseURL"],
                                             emby_file_server=config["emby_file_server"],emby_image_server=config["emby_image_server"])
    else:
        return abort(basicInfo.status_code)
    return Response(xmlStr, mimetype='application/xml')