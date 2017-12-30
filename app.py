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
    MessageEvent, TextMessage, TextSendMessage, LocationMessage, MessageImagemapAction, ImagemapArea, ImagemapSendMessage, BaseSize
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

    if event.type == "message":
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text='お疲れ様です'+ chr(0x10002D)),
                TextSendMessage(text='位置情報を送ってもらうと近くの駅を教えますよ'+ chr(0x10008D)),
                TextSendMessage(text='line://nv/location'),
            ]
        )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
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
    near_station_geo_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json?query={}&key={}'.format(near_station_list[0].text, 'AIzaSyDap2dQQx8T0SnMuHQ110Pp5mXDvnldXns');
    near_station_geo_req = urllib.request.Request(near_station_geo_url) #object
    #with urllib.request.urlopen(near_station_geo_req) as response:
    #    near_station_geo_read = response.read()
    #near_location_root = ET.fromstring(near_location_XmlData)
    #near_location_lat = near_location_root.findtext(".//lat")
    #near_location_lon = near_location_root.findtext(".//lng")

    map_image_url = 'https://maps.googleapis.com/maps/api/staticmap?center={},{}&zoom={}&size=520x520&scale=2&maptype=roadmap&key={}'.format(lat, lon, zoomlevel, 'AIzaSyCqPyyXKmQ1Ij290Fja_vxmMo78kViDqSw');
    map_image_url += '&markers=color:{}|label:{}|{},{}'.format('blue', '', lat, lon)

    # 現在地と最寄駅の座標を地図に表示

    # (3)
    #i = 0
    actions = [
        MessageImagemapAction(
            text = str(near_station_geo_req),
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
                actions = actions
            )
        ]
    )


if __name__ == "__main__":
    app.run()