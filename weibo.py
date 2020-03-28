import logging
import re
import requests
import setting

logger = logging.getLogger('QQBot')


def get_message() -> list:
    """获取最新的微博内容"""
    container_id = f'107603{setting.read_config("weibo","id")}'
    url = ('https://m.weibo.cn/api/container/getIndex?'
           f'containerid={container_id}')
    header = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/13.0.5 Safari/605.1.15'
        )
    }
    response = requests.get(url, headers=header).json()
    message_list = list()
    max_id = 0
    for card in response['data']['cards']:
        try:
            card_id = int(card['mblog']['id'])
        except KeyError:
            card_id = 0
            continue
        if card_id <= int(setting.read_config("weibo", "last_weibo")):
            continue
        elif card_id > max_id:
            max_id = card_id
        text = re.compile(r'<[^>]+>', re.S).sub('', card['mblog']['text'])
        logger.info("发现一条新微博, ID:%d", card_id)
        # 首先查看是否转发
        if card['mblog'].get('retweeted_status') is None:
            # 原创微博
            start_text = (
                f'{setting.read_config("system", "nickname")}'
                f"刚刚发了一条微博: {text}\n"
            )
            message = [
                {
                    'type': 'text',
                    'data': {'text': start_text}
                },
            ]
            if card['mblog'].get('pics'):
                message.append({
                    'type': 'image',
                    'data': {'file': card['mblog']['pics'][0]['url']}
                })
                message.append({
                    'type': 'text',
                    'data': {'text': f"一共有{len(card['mblog']['pics'])}张图哦\n"}
                })
            message.append({
                    'type': 'text',
                    'data': {'text': f"传送门: {card['scheme']}"}
            })
        else:
            raw_text = re.compile(r'<[^>]+>', re.S)\
                         .sub('', card['mblog']['retweeted_status']['text'])
            message = (
                f'{setting.read_config("system", "nickname")}'
                f"刚刚转发了一条微博: {text}\n原微博: {raw_text}"
                f"传送门: {card['scheme']}"
            )
        message_list.append(message)
    setting.write_config("weibo", "last_weibo", str(max_id))
    return message_list
