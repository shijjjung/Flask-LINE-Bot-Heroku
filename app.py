import os
from datetime import datetime

from flask import Flask, abort, request
import pymysql

# https://github.com/line/line-bot-sdk-python
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError,LineBotApiError
from linebot.models import (
    MessageEvent,
    TextSendMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    MessageTemplateAction,
    TextMessage,
    PostbackTemplateAction,
    PostbackEvent
)
app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

@app.route("/", methods=["GET", "POST"])
def callback():

    if request.method == "GET":
        return "Hello Heroku"
    if request.method == "POST":
        signature = request.headers["X-Line-Signature"]
        body = request.get_data(as_text=True)

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)

        return "OK"


@handler.add(PostbackEvent)
def handle_postback(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    if event.postback.data == "A":
        try:
            connection=pymysql.connect(host=os.environ.get("MYSQL_HOST"),user=os.environ.get("USER"),password=os.environ.get("PW"),db='message',charset='utf8mb4')
            with connection.cursor() as cursor:
                sql= """INSERT INTO `Registration`
                (`reg_id`, `reg_name`, `reg_name2`, `reg_part`, `reg_col1`) 
                VALUES (1, 'ShihTingHuang', '黃詩婷', 1, '2021/12/20')"""
                cursor.execute(sql)
                connection.commit()
            line_bot_api.reply_message(  # 回復傳入的訊息文字
                event.reply_token,
                TextSendMessage(text="%s已簽到成功"%(profile.display_name))
            )
            connection.close()
        except Exception as ex:
            line_bot_api.reply_message(  # 回復傳入的訊息文字
                event.reply_token,
                TextSendMessage(text=str(ex))
            )
    
            

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_message = event.message.text
    if "簽" in get_message:
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            event.reply_token,
            TemplateSendMessage(
                alt_text='Buttons template',
                template=ButtonsTemplate(
                    title='簽到',
                    text='各位隊員家人們～出席今日團練者，請於以下回覆，以利掌握人數，謝謝。',
                    actions=[
                        PostbackTemplateAction(
                            label='我會到',
                            text='我會到',
                            data='A'
                        ),
                    ]
                )
            )
        )
    elif get_message in ['不出席','不會到']:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='本月簽到次數{0},今年練習一共{1}次，出席率為：{2}'.format(str(3), str(5), str(int((3/5)*100))))
        )
    elif '出席' in get_message:
        #簽到完成
        profile = line_bot_api.get_profile(event.source.user_id)
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            event.reply_token,
            TextSendMessage(text=profile.display_name)
        )
    # Send To Line
    # reply = TextSendMessage(text=f"{get_message}")
    # line_bot_api.reply_message(event.reply_token, reply)