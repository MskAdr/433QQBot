import json
import logging
import requests
import time
from typing import List

from .module import Project, Rank

logger = logging.getLogger('QQBot')


def send_request(cmd_s: str, cmd_m: str, data: str) -> dict:
    """向o-what网站发送请求报文.
    ### Args:
    ``cmd_s``: 指令参数s.\n
    ``cmd_m``: 指令参数m.\n
    ``data``: 数据内容\n
    ### Result:
    ``result``: o-what网站返回的数据报文.\n
    """
    headers = {
        'host': 'm.owhat.cn',
        'content-type': 'application/x-www-form-urlencoded'
    }
    # TODO: 增加登录以后的功能
    params = {
        'cmd_s': cmd_s,
        'cmd_m': cmd_m,
        'v': ' 1.4.3L',
        'client': ('{"platform":"mobile", "version":"1.4.3L", '
                   '"deviceid":"xyz", "channel":"owhat"}'),
        'data': data
    }
    url = f"https://m.owhat.cn/api?requesttimestap={int(time.time()*1000)}"
    result = requests.post(url, params, json=True, headers=headers).json()
    if result['result'] != 'success':
        logger.error("拉取数据失败,返回报文:%s 发送命令:%s",
                     json.dumps(result), json.dumps(params))
    return result


class OwhatProject(Project):
    """用来处理O-what项目的一个类.
    ### Args:
    ``pro_id``: 项目在平台上的id.\n
    ``title``: 项目的标题.\n
    ``start_time``: 项目的开始时间, 用10位Unix时间戳表示.\n
    ``end_time``: 项目的结束时间, 用10位Unix时间戳表示.\n
    ``amount``: 项目当前筹集到的总金额.\n
    ``order_num``: 项目当前的订单数量.\n
    ### Attributes:
    ``refresh_detail``: 刷新项目的信息.\n
    ``get_ranks``: 获取项目当前集资排名列表.\n
    ``get_orders``: 获取项目当前全部订单列表.(当前暂未实现, 也没有实现的计划)\n
    ``get_new_orders``: 获取项目当前最新订单列表.(当前暂未实现, 也没有实现的计划)\n
    """
    def __init__(self, pro_id: int, title: str = '', starttime: int = 0,
                 endtime: int = 0, amount: float = 0.0, order_num: int = 0):
        self.platform = 3
        self.pro_id = pro_id
        self.title = title
        self.start_time = starttime
        self.end_time = endtime
        self.amount = amount
        self.order_num = order_num
        self.other_info = ''

    def link(self) -> str:
        """返回项目的集资链接."""
        return f'https://m.owhat.cn/shop/shopdetail.html?id={self.pro_id}'

    def refresh_detail(self) -> bool:
        """从网络上刷新项目的基本信息.
        ### Result:
        ``result``: 相对于原来的数据, 集资金额是否发生了改变.
        这个数据可以用来判断属否需要刷新订单.\n
        """
        data = f'{{"goodsid":"{self.pro_id}"}}'
        response = send_request('shop.goods', 'findgoodsbyid', data)
        if response['result'] != 'success':
            return
        self.start_time = int(int(response['data']['salestartat'])/1000)
        self.end_time = int(int(response['data']['saleendat'])/1000)
        self.order_num = int(response['data']['paystock'])
        self.title = response['data']['title']
        ori_amount = self.amount
        if self.start_time > int(time.time()):
            self.amount = 0.0
        else:
            # supportdetail可能不支持所有项目, 暂时先通过抓取商品销售情况判断销售总额
            ori_amount = self.amount
            data = f'{{"fk_goods_id":"{self.pro_id}"}}'
            response = send_request('shop.price', 'findPricesAndStock', data)
            goods_list = response['data']['prices']
            self.amount = 0.0
            for good in goods_list:
                self.amount += float(good['price']) * float(good['salestock'])
            self.amount = round(self.amount, 2)
        logger.debug("项目数据更新成功:%s", str(self))
        return self.amount != ori_amount

    def get_ranks(self) -> List[Rank]:
        """获取项目当前集资排名列表.
        ### Result
        ``rank_list``: 一个内部为``Rank``内容的list, 按照金额从高到低排列.
        """
        data = f'{{"goodsid":"{self.pro_id}","pagenum":1,"pagesize":20}}'
        response = send_request('shop.goods', 'findrankingbygoodsid', data)
        if response['result'] != 'success':
            return
        rank_list = list()
        cleared = False
        pages = 1
        while not cleared:
            for record in response['data']['rankinglist']:
                rank_list.append(Rank(
                    platform=3,
                    pro_id=self.pro_id,
                    user_id=int(record['userid']),
                    amount=float(record['amount'])
                ))
            if len(response['data']['rankinglist']) == 20:
                pages += 1
                data = (f'{{"goodsid":"{self.pro_id}",'
                        f'"pagenum":{pages},"pagesize":20}}')
                response = send_request('shop.goods',
                                        'findrankingbygoodsid', data)
            else:
                cleared = True
        logger.debug('项目%s排名数据拉取成功, 共得到%d条排名数据', self.title, len(rank_list))
        return rank_list
