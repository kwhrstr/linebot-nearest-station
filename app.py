import os
import sys
from flask import Flask, request, abort, send_file

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, LocationMessage, MessageImagemapAction, ImagemapArea, ImagemapSendMessage, BaseSize, LocationSendMessage
)

from PIL import Image
import requests
from io import BytesIO, StringIO
import urllib.parse
import urllib.request

import xml.etree.ElementTree as ET
import json




app = Flask(__name__)

# 環境変数からchannel_secret・channel_access_tokenを取得
channel_secret = os.environ['LINE_CHANNEL_SECRET']
channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

near_station_name = "東京駅"
near_station_address = "日本、〒100-0005 東京都千代田区丸の内１丁目"
near_station_geo_lat = 35.65910807942215
near_station_geo_lon = 139.70372892916203
near_station_number = 0

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@app.route("/imagemap/<path:url>/<size>")
def imagemap(url, size):
    map_image_url = urllib.parse.unquote(url)
    response = requests.get(map_image_url)
    img = Image.open(BytesIO(response.content))
    img_resize = img.resize((int(size), int(size)))
    byte_io = BytesIO()
    img_resize.save(byte_io, 'PNG')
    byte_io.seek(0)
    return send_file(byte_io, mimetype='image/png')


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global near_station_name
    global near_station_address
    global near_station_geo_lat
    global near_station_geo_lon
    global near_station_number

    if event.type == "message":
        if (event.message.text == "帰るよー！") or (event.message.text == "帰るよ！") or (event.message.text == "帰る！") or (event.message.text == "帰るよ"):
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text='お疲れ様です'+ chr(0x10002D)),
                    TextSendMessage(text='位置情報を送ってもらうと近くの駅を教えますよ'+ chr(0x10008D)),
                    TextSendMessage(text='line://nv/location'),
                ]
            )
        if event.message.text == "ありがとう！":
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="どういたしまして！気をつけて帰ってね" + chr(0x100033)),
                ]
            )
        if event.message.text == "位置情報教えて！":
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="はい！"+ chr(0x100031)),
                    LocationSendMessage(
                        title=near_station_name,
                        address=near_station_address,
                        latitude=near_station_geo_lat,
                        longitude=near_station_geo_lon
                    ),
                    TextSendMessage(text="タップした後右上のボタンからGoogleMapsなどで開けますよ"+ chr(0x100079)),    
                ]
            )
        if event.message.text == "次は？":
            near_station_number += 1
        else:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="まだその言葉は教えてもらってないです"+ chr(0x100029) + chr(0x100098)),   
                ]
            )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    global near_station_name
    global near_station_address
    global near_station_geo_lat
    global near_station_geo_lon
    global near_station_number
    
    lat = event.message.latitude
    lon = event.message.longitude

    zoomlevel = 18
    imagesize = 1040

    # SimpleAPIから最寄駅リストを取得
    near_station_url = 'http://map.simpleapi.net/stationapi?x={}&y={}&output=xml'.format(lon, lat)
    near_station_req = urllib.request.Request(near_station_url)
    with urllib.request.urlopen(near_station_req) as response:
        near_station_XmlData = response.read()
    near_station_root = ET.fromstring(near_station_XmlData)
    near_station_list = near_station_root.findall(".//name")
    near_station_n = len(near_station_list)

    # 最寄駅名から座標を取得
    near_station_geo_url = 'https://maps.googleapis.com/maps/api/place/textsearch/xml?query={}&key={}'.format(urllib.parse.quote_plus(near_station_list[near_station_number].text, encoding='utf-8'), 'AIzaSyDap2dQQx8T0SnMuHQ110Pp5mXDvnldXns');
    near_station_geo_req = urllib.request.Request(near_station_geo_url) #object
    with urllib.request.urlopen(near_station_geo_req) as response:
        near_station_geo_XmlData = response.read() # type(near_station_geo_XmlData) = "bytes"
    near_station_geo_root = ET.fromstring(near_station_geo_XmlData) # type(near_station_geo_root) = "xml.etree.ElementTree.Element"
    
    near_station_name = near_station_geo_root.findtext(".//name")
    near_station_address = near_station_geo_root.findtext(".//formatted_address")
    near_station_geo_lat = near_station_geo_root.findtext(".//lat") # type(near_station_geo_lat) = "str"
    near_station_geo_lon = near_station_geo_root.findtext(".//lng")

    map_image_url = 'https://maps.googleapis.com/maps/api/staticmap?size=520x520&scale=2&maptype=roadmap&key={}'.format('AIzaSyCqPyyXKmQ1Ij290Fja_vxmMo78kViDqSw');
    map_image_url += '&markers=color:{}|label:{}|{},{}'.format('red', '', near_station_geo_lat, near_station_geo_lon)
    map_image_url += '&markers=color:{}|label:{}|{},{}'.format('blue', '', lat, lon)

    #i = 0
    actions = [
        MessageImagemapAction(
            text = "位置情報教えて！",
            area = ImagemapArea(
                x = 0,
                y = 0,
                width = 1040,
                height = 1040
        )
    )]

    line_bot_api.reply_message(
        event.reply_token,
        [
            ImagemapSendMessage(
                base_url = 'https://{}/imagemap/{}'.format(request.host, urllib.parse.quote_plus(map_image_url)),
                alt_text = '地図',
                # (4)
                base_size = BaseSize(height=imagesize, width=imagesize),
                actions = actions,
            ),
            TextSendMessage(text=near_station_list[0].text + 'が一番近いですね！'),
        ]
    )


if __name__ == "__main__":
    app.run()