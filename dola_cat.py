#!/usr/bin/env python
# @Author   :   QWY
# @QQ       :   1695173542

import re
import time
import itchat
from itchat.content import *
import requests
import json
import sqlite3
from bs4 import BeautifulSoup
import lxml
import os
import configparser


# 调用图灵机器人的api，采用爬虫的原理，根据聊天消息返回回复内容
def tuling(info):
  appkey = "f0a5ab746c7d41c48a733cabff23fb6d"  # 哆啦猫
  url = "http://www.tuling123.com/openapi/api?key=%s&info=%s"%(appkey, info)
  req = requests.get(url)
  content = req.text
  data = json.loads(content)
  answer = data['text']
  return answer

auto_reply = False  # 是否自动回复私聊消息
shield_list = []  # 自动回复私聊消息的屏蔽列表（需要屏蔽的用户名）
download_file = True  # 是否开启文件下载
group_key_word = '哆啦猫'  # 群聊关键字

@itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO])
def download_files(msg):
    global download_file
    if download_file:
        msg['Text'](msg['FileName'])  # 下载文件
        text = '@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName'])
        friend = itchat.search_friends(userName=msg['FromUserName'])
        # 收到非文本消息，下载并入库
        if msg['MsgType'] == 47:
            content = '[动态表情]'
        elif msg['MsgType'] == 3:
            content = '[图片]'
        elif msg['MsgType'] == 34:
            content = '[语音消息]'
        elif msg['MsgType'] == 49:
            content = '[文件]'
        else:
            content = '[未知消息类型]'
        content += text
        conn = sqlite3.connect('wechat.db')
        try:
            create_tb_cmd = '''
                CREATE TABLE IF NOT EXISTS chat_record_single (MsgId varchar not null, FromUserName varchar, NickName varchar, RemarkName varchar, ToUserName varchar, MsgType varchar, Content varchar, Text varchar, FileName varchar, CreateTime timestamp);
                '''
            conn.execute(create_tb_cmd)
            _cmd = "insert into chat_record_single(MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime) values (?,?,?,?,?,?,?,?,?,?)"
            insert_info = [msg['MsgId'], msg['FromUserName'], friend['NickName'], friend['RemarkName'], msg['ToUserName'], msg['MsgType'], content, text, msg['FileName'], msg['CreateTime']]
            conn.execute(_cmd, insert_info)
        except Exception as e:
            print('保存单聊文件操作失败！', e)
            pass

        conn.commit()
        conn.close()


@itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO], isGroupChat=True)
def download_files_group(msg):
    global download_file
    if download_file:
        msg['Text'](msg['FileName'])  # 下载文件
        text = '@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName'])
        # 收到非文本消息，下载并入库
        if msg['MsgType'] == 47:
            content = '[动态表情]'
        elif msg['MsgType'] == 3:
            content = '[图片]'
        elif msg['MsgType'] == 34:
            content = '[语音消息]'
        elif msg['MsgType'] == 49:
            content = '[文件]'
        else:
            content = '[未知消息类型]'
        content += text
        conn = sqlite3.connect('wechat_group.db')
        # 判断数据库是否存在，不存在就创建  MsgType  1 - 收到的文字    3 - 收到的图片   34 - 收到的语音   47 - 收到的表情    49 - 收到的文件  10002 - 撤回
        try:
            create_tb_cmd = '''
                   CREATE TABLE IF NOT EXISTS group_chat_record (MsgId varchar not null, FromUserName varchar, NickName varchar, RemarkName varchar, ToUserName varchar, MsgType varchar, Content varchar, Text varchar, FileName varchar, CreateTime timestamp);
                   '''
            conn.execute(create_tb_cmd)
            # 收到消息，先入库
            _cmd = "insert into group_chat_record(MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime) values (?,?,?,?,?,?,?,?,?,?)"
            insert_info = [msg['MsgId'], msg['FromUserName'], '群聊', msg['ActualNickName'], msg['ToUserName'],
                           msg['MsgType'], content, text, msg['FileName'], msg['CreateTime']]
            conn.execute(_cmd, insert_info)
        except Exception as e:
            print('保存群聊文件操作失败！', e)
            pass

        conn.commit()
        conn.close()


# 群聊撤回的消息处理
@itchat.msg_register(NOTE, isGroupChat=True)
def group_text_note(msg):
    list = []
    # 提取被撤回的消息的原始id
    content = msg['Content']
    soup = BeautifulSoup(content, 'lxml')
    message_id = soup.find('msgid').text
    print('监测到群聊消息撤回！请查看手机助手。')
    conn = sqlite3.connect('wechat_group.db')
    # 判断数据库是否存在，不存在就创建  MsgType  1 - 收到   10002 - 撤回
    try:
        create_tb_cmd = '''
            CREATE TABLE IF NOT EXISTS group_chat_record (MsgId varchar not null, FromUserName varchar, NickName varchar, RemarkName varchar, ToUserName varchar, MsgType varchar, Content varchar, Text varchar, FileName varchar, CreateTime timestamp);
            '''
        conn.execute(create_tb_cmd)
        # 此处NickName为群聊名称，RemarkName为发送消息的用户昵称，Text为下载文件函数，FileName为要下载的文件名
        query_cmd = '''
                   SELECT MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime FROM group_chat_record WHERE MsgId=
                   ''' + "'" + message_id + "'"
        cursor = conn.execute(query_cmd)

        for c in cursor:
            chat_info = dict()
            chat_info['MsgId'] = c[0]
            chat_info['FromUserName'] = c[1]
            chat_info['NickName'] = c[2]
            chat_info['RemarkName'] = c[3]
            chat_info['ToUserName'] = c[4]
            chat_info['MsgType'] = c[5]
            chat_info['Content'] = c[6]
            chat_info['Text'] = c[7]
            chat_info['FileName'] = c[8]
            chat_info['CreateTime'] = c[9]
            list.append(chat_info)

    except Exception as e:
        print('查询失败！', e)
        pass
    conn.commit()
    conn.close()

    if len(list):
        chat = list[0]
        itchat.send(r"【%s】 %s 刚刚撤回了消息！ "
                    r" 撤回内容:%s" % (chat['NickName'], chat['RemarkName'],  chat['Content']),
                    toUserName='filehelper')
        if chat['MsgType'] != '1':
            itchat.send(chat['Text'], toUserName='filehelper')


# 群聊收到的文本消息处理
@itchat.msg_register(TEXT, isGroupChat=True)
def text_reply_group(msg):
    global group_key_word
    conn = sqlite3.connect('wechat_group.db')
    # 判断数据库是否存在，不存在就创建  MsgType  1 - 收到的文字    3 - 收到的图片   34 - 收到的语音   47 - 收到的表情    49 - 收到的文件  10002 - 撤回
    try:
        create_tb_cmd = '''
            CREATE TABLE IF NOT EXISTS group_chat_record (MsgId varchar not null, FromUserName varchar, NickName varchar, RemarkName varchar, ToUserName varchar, MsgType varchar, Content varchar, Text varchar, FileName varchar, CreateTime timestamp);
            '''
        conn.execute(create_tb_cmd)
        # 收到消息，先入库
        content = msg['Content']
        _cmd = "insert into group_chat_record(MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime) values (?,?,?,?,?,?,?,?,?,?)"
        insert_info = [msg['MsgId'], msg['FromUserName'], '群聊', msg['ActualNickName'], msg['ToUserName'], msg['MsgType'], content, content, msg['FileName'], msg['CreateTime']]
        conn.execute(_cmd, insert_info)
    except Exception as e:
        print('保存群聊文本消息失败！', e)
        pass

    conn.commit()
    conn.close()
    # 自动回复，包含指定字符串或者艾特
    if group_key_word in msg['Content']:  # or msg['isAt']
        itchat.send(u'@%s %s' % (msg['ActualNickName'], tuling(msg['Content'])), msg['FromUserName'])


# 单聊收到的消息和撤回的消息处理 [TEXT, PICTURE, MAP, CARD, NOTE, SHARING, RECORDING, ATTACHMENT, VIDEO]
@itchat.msg_register([TEXT, NOTE])
def text_reply(msg):
    global auto_reply
    global shield_list
    global download_file
    global group_key_word
    friend = itchat.search_friends(userName=msg['FromUserName'])
    conn = sqlite3.connect('wechat.db')
    # 判断数据库是否存在，不存在就创建  MsgType  1 - 收到   10002 - 撤回
    try:
        create_tb_cmd = '''
            CREATE TABLE IF NOT EXISTS chat_record_single (MsgId varchar not null, FromUserName varchar, NickName varchar, RemarkName varchar, ToUserName varchar, MsgType varchar, Content varchar, Text varchar, FileName varchar, CreateTime timestamp);
            '''
        conn.execute(create_tb_cmd)
        # 收到消息，如果不是撤回消息，先入库
        if msg['MsgType'] != 10002:
            content = msg['Content']
            _cmd = "insert into chat_record_single(MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime) values (?,?,?,?,?,?,?,?,?,?)"
            insert_info = [msg['MsgId'], msg['FromUserName'], friend['NickName'], friend['RemarkName'], msg['ToUserName'], msg['MsgType'], content, content, msg['FileName'], msg['CreateTime']]
            conn.execute(_cmd, insert_info)
    except Exception as e:
        print('保存单聊文本消息失败！', e)
        pass

    conn.commit()
    conn.close()

    # 判断消息是否是撤回消息，如果是，从数据库查询对应被撤回的消息，通过手机助手发送
    if msg['MsgType'] == 10002:
        list = []
        # 提取被撤回的消息的原始id
        content = msg['Content']
        soup = BeautifulSoup(content, 'lxml')
        message_id = soup.find('msgid').text
        conn = sqlite3.connect('wechat.db')
        try:
            query_cmd = '''
                       SELECT MsgId,FromUserName,NickName,RemarkName,ToUserName,MsgType,Content,Text,FileName,CreateTime FROM chat_record_single WHERE MsgId=
                       ''' + "'" + message_id + "'"
            cursor = conn.execute(query_cmd)

            for c in cursor:
                chat_info = dict()
                chat_info['MsgId'] = c[0]
                chat_info['FromUserName'] = c[1]
                chat_info['NickName'] = c[2]
                chat_info['RemarkName'] = c[3]
                chat_info['ToUserName'] = c[4]
                chat_info['MsgType'] = c[5]
                chat_info['Content'] = c[6]
                chat_info['Text'] = c[7]
                chat_info['FileName'] = c[8]
                chat_info['CreateTime'] = c[9]
                list.append(chat_info)

        except Exception as e:
            print('数据库查询操作失败！', e)
            pass
        conn.commit()
        conn.close()

        print('监测到私聊消息撤回！请查看手机助手。')
        if len(list):
            chat = list[0]
            itchat.send(r"%s -- 刚刚撤回了消息！       "
                    r" 撤回内容:%s" % (chat['NickName'], chat['Content']),
                    toUserName='filehelper')
            if chat['MsgType'] != '1':
                itchat.send(chat['Text'], toUserName='filehelper')

    else:
        # 指定好友，且包含指定字符串
        if msg['FromUserName'] == msg['ToUserName']:
            # 私聊自己，设置指令，开启/关闭私聊自动回复，屏蔽指定人的自动回复
            re_msg = msg['Text']
            if '帮助' in re_msg or 'help' in re_msg:
                print('''    
根据私聊自己可以对哆啦猫设置。具体指令如下：
1.  喵出来    		-   开启私聊的自动回复
2.  喵退下    		-   关闭私聊的自动回复
3.  查看      		-   查看当前[群聊关键字]和屏蔽的私聊好友列表（不自动回复的好友昵称列表）
4.  屏蔽昵称   		-   替换昵称为指定好友昵称（不是好友备注），将该好友加入屏蔽列表，不再自动回复
5.  回复昵称   		-   替换昵称为指定好友昵称（不是好友备注），将该好友从屏蔽列表移除，自动回复
6.  开启下载   		-   开启非文本消息自动下载（默认开启）
7.  关闭下载   		-   关闭非文本消息自动下载（默认开启），关闭后将无法恢复撤回的非文本消息
8.  群聊关键字关键字  	-   将修改群聊关键字为指定关键字，如：群聊关键字喵  将群聊关键字改成 “喵”
9.  帮助      		-   查看已有指令
                ''')
            if '群聊关键字' in re_msg[0:5]:
                key = re_msg[5:]
                if key:
                    group_key_word = key
            if '开启下载' in re_msg:
                download_file = True
                print('已开启非文本消息下载，撤回的非文本消息将通过手机助手恢复')
            if '关闭下载' in re_msg:
                download_file = False
                print('已关闭非文本消息下载，撤回的非文本消息将无法恢复')
            if '查看' in re_msg:
                print('当前群聊关键字：[%s]，当前私聊屏蔽的好友（不自动回复）：%s' % (group_key_word, str(shield_list)))
                itchat.send('当前群聊关键字：[%s]，当前私聊屏蔽的好友（不自动回复）：%s' % (group_key_word, str(shield_list)), toUserName='filehelper')
            if '喵出来' in re_msg:
                if friend['NickName'] not in shield_list:  # 把自己加到屏蔽列表
                    shield_list.append(friend['NickName'])
                print('喵来啦～开始自动回复咯。当前屏蔽的好友（不自动回复）：%s' % str(shield_list))
                auto_reply = True
            if '喵退下' in re_msg:
                itchat.send('喵走了...', toUserName='filehelper')
                print('喵走了...')
                auto_reply = False
            if '屏蔽' in re_msg[0:2]:
                if re_msg[2:] not in shield_list:
                    print('成功屏蔽好友（不自动回复）：%s' % re_msg[2:])
                    shield_list.append(re_msg[2:])
                else:
                    print('好友：%s 已在屏蔽列表' % re_msg[2:])
            if '回复' in re_msg:
                if re_msg[2:] in shield_list:
                    print('成功移除屏蔽好友：%s' % re_msg[2:])
                    shield_list.remove(re_msg[2:])
                else:
                    print('好友：%s 不在屏蔽列表' % re_msg[2:])
        elif auto_reply and friend['NickName'] not in shield_list:
            itchat.send(u'%s %s' % ('【自动回复】', tuling(msg['Text'])), msg['FromUserName'])


if __name__ == '__main__':
    parent_dir = os.getcwd()  # 当前用户目录
    base_dir = '/DolaCat/'
    config_file = parent_dir + base_dir + 'DolaCatConfig.ini'
    file_dir = base_dir + time.strftime('%Y-%m-%d_%H', time.localtime())
    new_path = parent_dir + file_dir
    if not os.path.exists(parent_dir + base_dir):
        os.mkdir(parent_dir + base_dir)
    if not os.path.exists(new_path):
        os.mkdir(new_path)
    # if not os.path.exists(config_file):
    #     os.mkdir(config_file)
    os.chdir(new_path)
    print('哆啦猫文件下载目录：' + new_path)
    # print('哆啦猫配置文件目录：' + config_file)

    # 读取配置文件
    # try:
    #     config = configparser.ConfigParser()
    #     config.read("./DolaCatConfig.ini")
    #     key_word = config.get("dolacat", "key_word")
    # except Exception as e:
    #     print('读取配置文件出错！', e)


itchat.auto_login()
itchat.run()
