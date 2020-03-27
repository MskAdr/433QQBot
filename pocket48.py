import json
import logging
import time

import requests

import setting

logger = logging.getLogger('QQBot')


def send_request(url: str, data: dict, has_login: bool = False) -> dict:
    """向口袋48服务器发送请求
    ### Args:
    ``url``: API地址.\n
    ``data``: 需要发送的报文.\n
    ### Return:
    ``response``: 读取后的JSON数据.\n
    """
    header = {
        'Host': 'pocketapi.48.cn',
        'accept': '*/*',
        'Accept-Language': 'zh-Hans-CN;q=1',
        'User-Agent': 'PocketFans201807/6.0.10 (iPhone; iOS 13.3; Scale/2.00)',
        'Accept-Encoding': 'gzip, deflate',
        'appInfo': ('{"vendor":"apple","deviceId":"0","appVersion":"6.0.10",'
                    '"appBuild":"200120","osVersion":"13.3.1","osType":"ios",'
                    '"deviceName":"iPhone XS Max","os":"ios"}'),
        'Content-Type': 'application/json;charset=utf-8',
        'Connection': 'keep-alive'
    }
    if has_login:
        header['token'] = setting.read_config('pocket48', 'token')
    response = requests.post(url, data=json.dumps(data),
                             headers=header, verify=False).json()
    return response


def set_token() -> bool:
    """设置口袋48的登录token, 返回是否成功"""
    url = "https://pocketapi.48.cn/user/api/v1/login/app/mobile"
    data = {
        "mobile": setting.read_config('pocket48', 'username'),
        "pwd": setting.read_config('pocket48', 'password')
    }
    response = send_request(url, data)
    if response['status'] == 200:
        token = response['content']['token']
        setting.write_config('pocket48', 'token', token)
        return True
    else:
        logger.error('登录口袋48时出错, 返回消息:%s', response['message'])
        return False


def get_messages() -> list:
    """返回口袋48主页面的信息
    ### Result:
    ``message_list``: 格式化的口袋消息列表.
    """
    # 发送请求获取消息列表
    url = "https://pocketapi.48.cn/im/api/v1/chatroom/msg/list/homeowner"
    data = {
        'ownerId': int(setting.read_config('pocket48', 'ownerid')),
        'roomId': int(setting.read_config('pocket48', 'roomid'))
    }
    response = send_request(url, data, True)
    if response['status'] >= 401000:
        if not set_token():
            logger.error('口袋48授权失败, 请检查用户名和密码')
            return dict()
        response = send_request(url, data, True)
    # 处理消息列表
    message_list = list()
    last_time = int(setting.read_config('pocket48', 'message_time'))
    for data in response['content']['message']:
        message = ''
        if data['msgTime'] < last_time:
            break
        message_time = time.strftime(
            '%Y-%m-%d %H:%M:%S',
            time.localtime(int(data['msgTime']/1000))
        )
        message_ext = json.loads(data['extInfo'])
        if data['msgType'] == 'TEXT':
            # 口袋48好像会出现换行直接打到行首的特殊情况
            message_ext['text'] = message_ext['text'].replace('\r', '\n')
            if message_ext['messageType'] == 'TEXT':
                message = (
                    f'{message_ext["user"]["nickName"]}: '
                    f'{message_ext["text"]}\n'
                    f'{message_time}'
                )
                logger.info('收到一条文字消息: %s', message_ext["text"])
            elif message_ext['messageType'] == 'REPLY':
                message = (
                    f'{message_ext["replyName"]}: '
                    f'{message_ext["replyText"]}\n'
                    f'{message_ext["user"]["nickName"]}: '
                    f'{message_ext["text"]}\n'
                    f'{message_time}'
                )
                logger.info('收到一条回复消息: %s, 原文: %s',
                            message_ext["text"],
                            message_ext["replyText"])
            elif message_ext['messageType'] == 'VOTE':
                message = (
                    f'{message_ext["user"]["nickName"]}发起了投票: '
                    f'{message_ext["text"]}\n'
                    f'{message_time}'
                )
                logger.info('收到一条投票消息: %s', message_ext["text"])
            elif message_ext['messageType'] == 'FLIPCARD':
                message = (
                    f'{message_ext["user"]["nickName"]}: '
                    f'{message_ext["text"]}\n'
                    f'问题内容: {message_ext["question"]}\n'
                    f'{message_time}'
                )
                logger.info('收到一条翻牌消息: %s, 问题: %s',
                            message_ext["text"],
                            message_ext["question"])
            elif message_ext['messageType'] == 'LIVEPUSH':
                idol_nickname = setting.read_config("system", "idolnickname")
                # playStreamPath = response['content']['playStreamPath']
                message = [
                    {
                        'type': 'text',
                        'data': {'text': (
                            f'{idol_nickname}开直播啦: '
                            f'{message_ext["liveTitle"]}\n'
                            '封面: '
                        )}
                    },
                    {
                        'type': 'image',
                        'data': {'file': f'{message_ext["liveCover"]}'}
                    },
                    {
                        'type': 'text',
                        'data': {'text': '快去口袋48观看吧! '}
                    },
                ]
                logger.info('收到一条直播消息,id=%s', str(message_ext["liveId"]))
        elif data['msgType'] == 'IMAGE':
            bodys = json.loads(data['bodys'])
            message = [
                {
                    'type': 'text',
                    'data': {'text': f'{message_ext["user"]["nickName"]}: '}
                },
                {
                    'type': 'image',
                    'data': {'file': f'{bodys["url"]}'}
                },
                {
                    'type': 'text',
                    'data': {'text': f'{message_time}'}
                },
            ]
        elif data['msgType'] == 'AUDIO' or data['msgType'] == 'VIDEO':
            bodys = json.loads(data['bodys'])
            message = [
                {
                    'type': 'text',
                    'data': {'text': f'{message_ext["user"]["nickName"]}: '}
                },
                {
                    'type': 'record',
                    'data': {'file': f'{bodys["url"]}'}
                },
                {
                    'type': 'text',
                    'data': {'text': f'{message_time}'}
                },
            ]
        elif data['msgType'] == 'EXPRESS':
            message = (
                f'{message_ext["user"]["nickName"]}: 发送了表情\n'
                f'{message_time}'
            )
        else:
            logger.error('发现了未知格式的信息: %s', json.dumps(message_ext))
        message_list.append(message)
    logger.info('口袋48信息处理完成, 共收取到%d条信息', len(message_list))
    setting.write_config('pocket48', 'message_time',
                         str(int(time.time()*1000)))
    return message_list


def find_room(name: str):
    """按照名称寻找roomid和ownerid，随后写入到配置文件中"""
    url = 'https://pocketapi.48.cn/im/api/v1/im/search'
    data = {'name': name}
    response = send_request(url, data)
    result = response['content']['data'][0]
    setting.write_config('pocket48', 'roomid', result['targetId'])
    setting.write_config('pocket48', 'ownerid', result['ownerId'])
