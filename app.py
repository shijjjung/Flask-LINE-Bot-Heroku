import os
import time
from flask import Flask, abort, request
import pymysql
import re
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
# 發問出席統計按鈕
def echoJoinButtons(data, reply_token):
    line_bot_api.reply_message(  # 回復傳入的訊息文字
        reply_token,
        TemplateSendMessage(
            alt_text='Buttons template',
            template=ButtonsTemplate(
                title='簽到',
                text='各位隊員家人們～出席{data}團練者，請於以下回覆，以利掌握人數，謝謝。'.format(data=data),
                actions=[
                    PostbackTemplateAction(
                        label='我會到',
                        text='我會到',
                        data='A&'+data
                    ),
                    PostbackTemplateAction(
                        label='我會晚到',
                        text='我會晚到',
                        data='B&'+data
                    ),
                ]
            )
        )
    )
def echoMembersJoined(connection, token, reg_col1):
    with connection.cursor() as cursor:
        select_query = """select m_nickname from Registration inner join Member on Registration.reg_name2 = Member.m_id where reg_part = 1 and `reg_col1` = '{datestr}'""".format(datestr=reg_col1)
        cursor.execute(select_query)
        records = cursor.fetchall()
        i = 1
        txt = ""
        for row in records:
            txt = txt + "{i}. {name}\n".format(i=i, name=row[0])
            i = i + 1
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            token,
            TextSendMessage(text=txt)
        )
# 回應參加
def doRegister(profile, event, postdata):
    try:
        sp_sql = """SELECT SP_UPDATEMEMBER('{u_id}','{n}');""".format(u_id = event.source.user_id, n=profile.display_name)
        date =  postdata.split('&')[-1]
        connection=pymysql.connect(host=os.environ.get("MYSQL_HOST"),user=os.environ.get("USER"),password=os.environ.get("PW"),db='message',charset='utf8mb4')
        with connection.cursor() as cursor:
            sql= """
            INSERT INTO `Registration`(`reg_name`,`reg_name2`,`reg_part`,`reg_col1`,`reg_col2`) 
            SELECT '{name}', (select `m_id`from `Member` where `m_uid`='{u_id}' LIMIT 1), 1, '{datestr}','{memo}' from `Member` WHERE not EXISTS 
            (SELECT 1 FROM `Registration` WHERE `reg_col1` = '{datestr}' and `reg_name2` = (select `m_id` from `Member` WHERE 
            `m_uid` = '{u_id}')) AND `m_uid` = '{u_id}' LIMIT 1;""".format(
                name=profile.display_name, 
                datestr=date,
                memo=postdata,
                u_id = event.source.user_id
            )
            cursor.execute(sp_sql)
            cursor.execute(sql)
            connection.commit()
        echoMembersJoined(connection=connection, token=event.reply_token, reg_col1=date)
        echoJoinButtons(date, event.reply_token )
        connection.close()
    except Exception as ex:
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            event.reply_token,
            TextSendMessage(text=str(ex))
        )
def doChangeName(u_id, new_name_string, token):
    try:
        sql = """UPDATE Member set m_nickname='{name}' where m_uid='{u_id}';""".format(name=new_name_string, u_id = u_id)
        connection=pymysql.connect(host=os.environ.get("MYSQL_HOST"),user=os.environ.get("USER"),password=os.environ.get("PW"),db='message',charset='utf8mb4')
        with connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()
        connection.close()
    except Exception as ex:
        line_bot_api.reply_message(  # 回復傳入的訊息文字
            token,
            TextSendMessage(text=str(ex))
        )
@handler.add(PostbackEvent)
def handle_postback(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    if event.postback.data[0:1] == "A" or event.postback.data[0:1] == "B":
        doRegister(profile, event, event.postback.data)
        
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_message = event.message.text
    if get_message.split(' ')[-1]=="團練" and event.source.user_id == 'Uf3ea47edfa9d6c08b8c14786d2fd043a':
        date = get_message.split(' ')[0]
        echoJoinButtons(date, event.reply_token)
        return
    if "改暱稱" in get_message:
        newname = ''.join(get_message.split("改暱稱"))
        new_string = re.sub(r"(?:[\*\.\-\%\#])+",'',newname)
        doChangeName(event.source.user_id, new_string, event.reply_token)
    if "改名" in get_message:
        newname = ''.join(get_message.split("改名"))
        new_string = re.sub(r"(?:[\*\.\-\%\#])+",'',newname)
        doChangeName(event.source.user_id, new_string, event.reply_token)
    # elif get_message in ['不出席','不會到']:
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text='本月簽到次數{0},今年練習一共{1}次，出席率為：{2}'.format(str(3), str(5), str(int((3/5)*100))))
    #     )
    # elif '出席' in get_message:
    #     #簽到完成
    #     profile = line_bot_api.get_profile(event.source.user_id)
    #     line_bot_api.reply_message(  # 回復傳入的訊息文字
    #         event.reply_token,
    #         TextSendMessage(text=profile.display_name)
    #     )
    # Send To Line
    # reply = TextSendMessage(text=f"{get_message}")
    # line_bot_api.reply_message(event.reply_token, reply)