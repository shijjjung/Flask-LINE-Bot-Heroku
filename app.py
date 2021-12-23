import os
import time
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
    if event.postback.data[0:1] == "A" or event.postback.data[0:1] == "B":
        try:
            date = event.postback.data.split('&')[-1]
            connection=pymysql.connect(host=os.environ.get("MYSQL_HOST"),user=os.environ.get("USER"),password=os.environ.get("PW"),db='message',charset='utf8mb4')
            with connection.cursor() as cursor:
                sql= """INSERT INTO `Registration`
                ( `reg_name`, `reg_name2`, `reg_part`, `reg_col1`, `reg_col2`) 
                VALUES ('{name}', '{name2}', 1, '{datestr}', '{memo}')""".format(
                    name=profile.display_name, 
                    name2=profile.display_name,
                    datestr=date,
                    memo=event.postback.data
                )
                cursor.execute(sql)
                connection.commit()
            with connection.cursor() as cursor:
                select_query = """select `reg_name2` from Registration where reg_part = 1 and `reg_col1` = '{datestr}'.format(datestr=date)"""
                cursor.execute(select_query)
                records = cursor.fetchall()
                i = 1
                txt = ""
                for row in records:
                   txt = txt + "{i}. {name}\n".format(i=i, name=row[0])
                   i = i + 1
                line_bot_api.reply_message(  # 回復傳入的訊息文字
                    event.reply_token,
                    TextSendMessage(text=txt)
                )
            line_bot_api.reply_message(  # 回復傳入的訊息文字
                event.reply_token,
                TemplateSendMessage(
                    alt_text='Buttons template',
                    template=ButtonsTemplate(
                        title='簽到',
                        text='各位隊員家人們～出席{date}團練者，請於以下回覆，以利掌握人數，謝謝。'.format(date=date),
                        actions=[
                            PostbackTemplateAction(
                                label='我會到',
                                text='我會到',
                                data='A&'+date
                            ),
                            PostbackTemplateAction(
                                label='我會晚到',
                                text='我會晚到',
                                data='B&'+date
                            ),
                        ]
                    )
                )
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
    if get_message.split(' ')[-1]=="團練":
        date = get_message.split(' ')[0]
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            event.reply_token,
            TemplateSendMessage(
                alt_text='Buttons template',
                template=ButtonsTemplate(
                    title='簽到',
                    text='各位隊員家人們～出席{date}團練者，請於以下回覆，以利掌握人數，謝謝。'.format(date=date),
                    actions=[
                        PostbackTemplateAction(
                            label='我會到',
                            text='我會到',
                            data='A&'+date
                        ),
                        PostbackTemplateAction(
                            label='我會晚到',
                            text='我會晚到',
                            data='B&'+date
                        ),
                    ]
                )
            )
        )
        return 
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