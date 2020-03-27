import base64
import hashlib
import json
import logging
import requests
import time
from typing import List
import zlib

from sqlalchemy.orm.session import Session

from . import setting
from .module import Project, Rank, Order

logger = logging.getLogger('QQBot')


def add_xor(original: bytearray) -> bytearray:
    """对数据进行异或处理, 满足桃叭的加密要求.
    ### Args:
    ``original``: 原始数据串.\n
    ### Result:
    ``result``: 结果数据串
    """
    Salt = '%#54$^%&SDF^A*52#@7'
    i = 0
    for ch in original:
        if i % 2 == 0:
            ch = ch ^ ord(Salt[(i//2) % len(Salt)])
        original[i] = ch
        i += 1
    return original


def encode(original: str) -> str:
    """按照桃叭的要求对数据编码.
    ### Args:
    ``original``: 原始字符串.\n
    ### Result:
    ``result``: 结果字符串.\n
    """
    # 开头的数字是原始报文长度
    length = len(original)
    message = str.encode(original)
    # 首先用zlib进行压缩
    compressed = bytearray(zlib.compress(message))
    # 然后异或处理
    xored = add_xor(compressed)
    # 最后将结果转化为base64编码
    result = base64.b64encode(xored).decode('utf-8')
    # 将长度头和base64编码的报文组合起来
    return str(length) + '$' + result


def decode(original: str) -> dict:
    """按照桃叭的要求对数据解码.
    ### Args:
    ``original``: 原始字符串.\n
    ### Result:
    ``result``: 结果字符串.\n
    """
    # 分离报文长度头
    # TODO: 增加报文头长度的验证
    source = original.split('$')[1]
    # base64解码
    xored = bytearray(base64.b64decode(source))
    # 重新进行异或计算, 恢复原始结果
    compressed = add_xor(xored)
    # zlib解压
    result = zlib.decompress(compressed).decode('utf-8')
    # 提取json
    return json.loads(result)


def send_request(url: str, data: str) -> dict:
    """向桃叭网站发送请求报文.
    ### Args:
    ``url``: API网址.\n
    ``data``: API所需要的数据.\n
    ### Result:
    ``result``: 桃叭网站返回的数据报文.\n
    """
    headers = {
        'Content-Type': 'application/json',
        'SIGNATURE': setting.read_config('taoba', 'signature'),
        'Origin': 'https://www.tao-ba.club',
        'Cookie': 'l10n=zh-cn',
        'Accept-Language': 'zh-cn',
        'Host': 'www.tao-ba.club',
        'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) '
                       'AppleWebKit/605.1.15 (KHTML, like Gecko)'
                       ' Version/13.0.5 Safari/605.1.15'),
        'Referer': 'https://www.tao-ba.club/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    data = encode(data)
    response = requests.post(url=url, data=data, headers=headers)
    return decode(response.text)


def get_signature():
    """获取桃叭网站的登录签名."""
    data = json.dumps({
        'account': setting.read_config('taoba', 'username'),
        'pushid': '',
        'loginpw': setting.read_config('taoba', 'password'),
        'device': {
            'platform': 'other',
            'screen': '1680*1050',
            'imei': 'XXX',
            'uuid': 'YYY',
            'version': 'v1.0.0',
            'vendor': 'ZZZ'
        },
        'requestTime': int(time.time() * 1000), 'pf': 'h5'}
    )
    response = send_request('https://www.tao-ba.club/signin/phone', data)
    if response['code'] == 0:
        setting.write_config('taoba', 'signature', response['token'])
    else:
        logger.error('桃叭登录失败, 请检查用户名和密码')


class TaobaProject(Project):
    """用来表示桃叭项目的一个类.
    ### Args:
    ``pro_id``: 项目在平台上的id.\n
    ``title``: 项目的标题.\n
    ``start_time``: 项目的开始时间, 用10位Unix时间戳表示.\n
    ``end_time``: 项目的结束时间, 用10位Unix时间戳表示.\n
    ``amount``: 项目当前筹集到的总金额.\n
    ``order_num``: 项目当前的订单数量.\n
    ### Attributes:
    ``refresh_detail``: 刷新项目除了``pro_id``以外的信息.\n
    ``get_ranks``: 获取项目当前集资排名列表.\n
    ``get_orders``: 获取项目当前全部订单列表.\n
    ``get_new_orders``: 获取项目当前最新订单列表.\n
    """
    __mapper_args__ = {
        'polymorphic_identity': 2
    }

    def __init__(self, pro_id: int, title: str = '', starttime: int = 0,
                 endtime: int = 0, amount: float = 0.0, order_num: int = 0):
        self.platform = 2
        self.pro_id = pro_id
        self.title = title
        self.start_time = starttime
        self.end_time = endtime
        self.amount = amount
        self.order_num = order_num
        self.other_info = ''

    def link(self) -> str:
        """返回项目的集资链接."""
        return f'https://www.tao-ba.club/#/pages/idols/detail?id={self.pro_id}'

    def refresh_detail(self) -> bool:
        """从网络上刷新项目的基本信息.
        ### Result:
        ``result``: 相对于原来的数据, 集资金额是否发生了改变.
        这个数据可以用来判断属否需要刷新订单.\n
        """
        data = json.dumps({
            'id': self.pro_id,
            'requestTime': int(time.time()*1000),
            'pf': 'h5'
        })
        response = send_request('https://www.tao-ba.club/idols/detail', data)
        self.title = response['datas']['title']
        self.start_time = int(response['datas']['start'])
        self.end_time = int(response['datas']['expire'])
        ori_amount = self.amount
        self.amount = float(response['datas']['donation'])
        self.order_num = int(response['datas']['sellstats'])
        logger.debug("项目数据更新成功:%s", str(self))
        return self.amount != ori_amount

    def get_ranks(self) -> List[Rank]:
        """获取项目当前集资排名列表.
        ### Result
        ``rank_list``: 一个内部为``Rank``内容的list, 按照金额从高到低排列.
        """
        data = json.dumps({
            'ismore': False,
            'limit': 15,
            'id': self.pro_id,
            'offset': 0,
            'requestTime': int(time.time()*1000),
            'pf': 'h5'
        })
        response = send_request('https://www.tao-ba.club/idols/join', data)
        rank_list = list()
        cleared = False
        pages = 0
        while not cleared:
            for record in response['list']:
                rank_list.append(Rank(
                    platform=2,
                    pro_id=self.pro_id,
                    user_id=int(record['userid']),
                    amount=float(record['money'])
                ))
            if len(response['list']) == 15:
                pages += 1
                data = json.dumps({
                    'ismore': True,
                    'limit': 15,
                    'id': self.pro_id,
                    'offset': pages*15,
                    'requestTime': int(time.time()*1000),
                    'pf': 'h5'
                })
                response = send_request('https://www.tao-ba.club/idols/join',
                                        data)
            else:
                cleared = True
        logger.debug('项目%s排名数据拉取成功, 共得到%d条排名数据', self.title, len(rank_list))
        return rank_list

    def get_orders(self) -> List[Order]:
        """获取项目当前全部订单列表.
        ### Result
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.
        """
        order_list = list()
        cleared = False
        pages = 0
        while not cleared:
            data = json.dumps({
                'id': self.pro_id,
                'offset': pages * 15,
                'ismore': (pages != 0),
                'limit': 15,
                'requestTime': int(time.time()*1000),
                'pf': 'h5'
            })
            response = send_request(
                'https://www.tao-ba.club/idols/refund/orders',
                data
            )
            if response['code'] == 99999:
                # 请求签名验证失败, 重新获取签名
                logger.warn('请求桃叭签名验证失败, 尝试重新获取签名')
                get_signature()
                response = send_request(
                    'https://www.tao-ba.club/idols/refund/orders',
                    data
                )
                if response['code'] == 99999:
                    logger.error('连续失败, 请检查用户是否有查看权限')
                    return list()
            for order in response['list']:
                signature = hashlib.sha1()
                signature.update(bytes(order['ordersn'], encoding='utf-8'))
                order_list.append(Order(
                    platform=2,
                    pro_id=self.pro_id,
                    user_id=int(order['userid']),
                    nickname=order['nickname'],
                    amount=float(order['amount']),
                    signature=str(signature.hexdigest())
                ))
            if len(response['list']) != 25:
                cleared = True
            pages += 1
        logger.debug('项目%s订单数据拉取成功, 共得到%d条订单数据', self.title, len(order_list))
        return order_list

    def get_new_orders(self, session: Session,
                       search_all: bool = False) -> List[Order]:
        """获取项目当前最新订单列表.
        ### Args:
        ``session``: 用于连接数据库的SQLAlchemy线程.\n
        ``search_all``: 用于决定是否搜索全部订单.
        因为桃叭系统的设置, 这个参数不起作用.\n
        ### Result:
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.\n
        """
        total_order_list = self.get_orders()
        new_order_list = list()
        for order in total_order_list:
            if session.query(Order).\
                       filter(Order.signature == order.signature).\
                       filter(Order.pro_id == self.pro_id).\
                       filter(Order.platform == 2).count() == 0:
                session.add(order)
                session.flush()
                new_order_list.append(order)
        logger.info('发现项目%s的%d条新的订单数据', self.title, len(new_order_list))
        return new_order_list


def find_new_taoba_project(session: Session):
    """根据设定的应援会账户ID, 查找该应援会发布的新项目
    ### Args:
    ``session``:用于连接数据库的SQLAlchemy线程.\n
    """
    pages = 0
    cleared = False
    while not cleared:
        data = json.dumps({
            'limit': 20,
            'offset': pages * 15,
            'ismore': (pages != 0),
            'requestTime': int(time.time()*1000),
            'pf': 'h5'
        })
        response = send_request('https://www.tao-ba.club/idols/mine/main',
                                data)
        if response['code'] == 99999:
            logger.warn('请求桃叭签名验证失败, 尝试重新获取签名')
            get_signature()
            data = json.dumps({
                'limit': 20,
                'offset': pages * 15,
                'ismore': (pages != 0),
                'requestTime': int(time.time()*1000),
                'pf': 'h5'
            })
            response = send_request('https://www.tao-ba.club/idols/mine/main',
                                    data)
            if response['code'] == 99999:
                logger.error('连续失败, 请检查用户是否有查看权限')
                return list()
        for return_project in response['list']:
            if session.query(Project).\
                       filter(Project.pro_id == return_project['id']).\
                       filter(Project.platform == 2).count() == 0:
                new_project = TaobaProject(pro_id=return_project['id'])
                new_project.refresh_detail()
                session.add(new_project)
                logger.info("发现新项目:%s", new_project.title)
                logger.debug(str(new_project))
        if len(response['list']) == 20:
            pages += 1
            data = json.dumps({
                'limit': 20,
                'offset': pages * 15,
                'ismore': (pages != 0),
                'requestTime': int(time.time()*1000),
                'pf': 'h5'
            })
            response = send_request('https://www.tao-ba.club/idols/join', data)
        else:
            cleared = True
