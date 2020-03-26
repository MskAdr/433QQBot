import hashlib
import json
import logging
import time
from typing import Tuple, List

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm.session import Session

from . import setting
from .module import Project, Order


logger = logging.getLogger('QQBot')


class ModianProject(Project):
    """用来表示集资项目的一个类.
    ### Args:
    ``pro_id``: 项目在平台上的id.\n
    ``title``: 项目的标题.\n
    ``start_time``: 项目的开始时间, 用10位Unix时间戳表示.\n
    ``end_time``: 项目的结束时间, 用10位Unix时间戳表示.\n
    ``amount``: 项目当前筹集到的总金额.\n
    ``order_num``: 项目当前的订单数量.\n
    ``other_info``: ``moxi_pid``和``pro_class``两项, 用JSON字符串存储.\n
    ### Attributes:
    ``refresh_detail``: 刷新项目的信息.\n
    ``get_ranks``: 获取项目当前集资排名列表.(当前暂未实现)\n
    ``get_orders``: 获取项目当前全部订单列表.\n
    ``get_new_orders``: 获取项目当前最新订单列表.\n
    """
    __mapper_args__ = {
        'polymorphic_identity': 1
    }

    def __init__(self, pro_id: int, title: str = '', starttime: int = 0,
                 endtime: int = 0, amount: int = 0.0, order_num: int = 0,
                 other_info: str = ''):
        self.platform = 1
        self.pro_id = pro_id
        self.title = title
        self.start_time = starttime
        self.end_time = endtime
        self.amount = amount
        self.order_num = order_num
        self.other_info = other_info

    def link(self) -> str:
        """返回项目的集资链接."""
        return f'https://zhongchou.modian.com/item/{self.pro_id}.html'

    def refresh_detail(self) -> bool:
        """从网络上刷新项目的基本信息.
        ### Result:
        ``result``: 相对于原来的数据, 集资金额是否发生了改变.
        这个数据可以用来判断属否需要刷新订单.\n
        """
        url = ('https://zhongchou.modian.com/realtime/get_simple_product'
               f'?jsonpcallback=jQuery1_1&ids={self.pro_id}&if_all=1&_=2')
        header = {
            'Accept': ('text/javascript, application/javascript, '
                       'application/ecmascript, '
                       'application/x-ecmascript, */*; q=0.01'),
            'Host': 'zhongchou.modian.com',
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) '
                           'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                           'Version/13.0.5 Safari/605.1.15'),
        }
        response = requests.get(url, headers=header).text
        response = response[41: -3]
        profile = json.loads(response)
        backer_money = str(profile['backer_money'])
        backer_money = backer_money.replace(',', '')
        start_time = time.strptime(profile['start_time'], '%Y-%m-%d %H:%M:%S')
        end_time = time.strptime(profile['end_time'], '%Y-%m-%d %H:%M:%S')
        other_info = json.dumps({
            'moxi_pid': int(profile['moxi_post_id']),
            'pro_class': int(profile['pro_class'])
        }, ensure_ascii=False)
        # 更新数据
        self.title = profile['name']
        self.start_time = int(time.mktime(start_time))
        self.end_time = int(time.mktime(end_time))
        ori_amount = self.amount
        self.amount = float(backer_money)
        self.order_num = int(profile['comment_count'])
        self.other_info = other_info
        logger.debug("项目数据更新成功:%s", str(self))
        return self.amount != ori_amount

    def _get_order(self, page: int = 1) -> Tuple[List[Order], bool]:
        """从网络上抓取某一页的订单.
        ### Args:
        ``page``: 页码.\n
        ### Result:
        ``order_list``: 抓获到的订单列表.\n
        ``last_page``: 该页是否是最后一页.\n
        """
        other_info = json.loads(self.other_info)
        moxi_pid = other_info['moxi_pid']
        pro_class = other_info['pro_class']
        url = ('https://zhongchou.modian.com/comment/ajax_comments'
               '?jsonpcallback=jQuery1_1&'
               f'post_id={moxi_pid}&pro_class={pro_class}'
               f'&page={page}&page_size=10&_=2')
        header = {
            'Accept': ('text/javascript, application/javascript, '
                       'application/ecmascript, '
                       'application/x-ecmascript, */*; q=0.01'),
            'Host': 'zhongchou.modian.com',
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) '
                           'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                           'Version/13.0.5 Safari/605.1.15'),
        }
        response = requests.get(url, headers=header).text
        response = response[40: -2]
        OrderHTML = json.loads(response)['html']
        # 获取HTML数据，准备通过BeautifulSoup处理
        soup = BeautifulSoup(OrderHTML, 'lxml')
        ori_comment = soup.find(lambda tag: tag.name == 'ul'
                                and tag.get('class') == ['comment-lists'])
        order_list = list()
        if ori_comment is None:
            return order_list
        comment_list = ori_comment.find_all(name='li', class_='comment-list')
        for comment in comment_list:
            comment_rid = comment['data-reply-id']
            comment_detail = comment.find(name='div', class_='comment-txt')
            # 判断该评论是否是集资记录
            if comment_detail.find(name='i',
                                   class_='iconfont icon-payment') is None:
                amount_str = '0.0'
            # 获取集资金额
            else:
                amount_str = str(comment_detail.get_text())
                amount_str = amount_str.replace('\n', '')
                amount_str = amount_str.replace(' ', '')
                amount_str = amount_str.replace('支持了', '')
                amount_str = amount_str.replace('元', '')
            # 获取用户信息
            user_detail = comment.find(name='p',
                                       class_='nickname').find(name='a')
            user_id = str(user_detail['href'])[35:]
            # 匿名用户
            if user_detail['href'] == 'javascript:;':
                user_id = '0'
            nickname = str(user_detail.get_text())
            # 计算签名
            signature = hashlib.sha1()
            signature.update(bytes(str(comment_rid), encoding='utf-8'))
            # 插入列表
            order_list.append(
                Order(
                    platform=1,
                    pro_id=self.pro_id,
                    user_id=int(user_id),
                    nickname=nickname,
                    amount=float(amount_str),
                    signature=str(signature.hexdigest())
                )
            )
        logger.debug('项目%s评论数据拉取成功，在第%d页共得到%d条评论数据',
                     self.title, page, len(order_list))
        last_page = True
        if len(order_list) == 10:
            last_page = False
        return order_list, last_page

    def get_orders(self) -> List[Order]:
        """获取项目当前全部订单列表.
        ### Result
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.
        """
        order_list = list()
        cleared = False
        page = 1
        while not cleared:
            order_page, cleared = self._get_order(page)
            order_list.extend(order_page)
            page += 1
        logger.debug('项目%s订单数据拉取成功，共得到%d条订单数据', self.title, len(order_list))
        return order_list

    def get_new_orders(self, session: Session,
                       search_all: bool = False) -> List[Order]:
        """获取项目当前最新订单列表.
        ### Args:
        ``session``:用于连接数据库的SQLAlchemy线程.\n
        ``search_all``:是否需要全部检索整个订单列表来对比.\n
        ### Result:
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.\n
        """
        # 根据项目ID顺序查找有没有新订单
        order_list = list()
        cleared = False
        page = 1
        while not cleared:
            order_page, cleared = self._get_order(page)
            page += 1
            for thisOrder in order_page:
                if session.query(Order).\
                           filter(Order.signature == thisOrder.signature).\
                           filter(Order.pro_id == self.pro_id).\
                           filter(Order.platform == self.platform).\
                           count() == 0:
                    session.add(thisOrder)
                    session.flush()
                    order_list.append(thisOrder)
                elif not search_all:
                    logger.info('发现项目%s的%d条新的订单数据', self.title,
                                len(order_list))
                    return order_list
        logger.info('发现项目%s的%d条新的订单数据', self.title, len(order_list))
        return order_list


def find_new_modian_project(session: Session):
    """根据设定的应援会账户ID，查找该应援会发布的新项目
    ### Args:
    ``session``:用于连接数据库的SQLAlchemy线程.\n
    """
    header = {
        'Accept': ('text/html,application/xhtml+xml,application/xml;'
                   'q=0.9,image/webp,image/apng,*/*;'
                   'q=0.8,application/signed-exchange;v=b3'),
        'Host': 'me.modian.com',
        'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) '
                       'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                       'Version/13.0.5 Safari/605.1.15'),
    }
    url = ('https://me.modian.com/user?type=index'
           f'&id={setting.read_config("modian","userid")}')
    response_html = requests.get(url, headers=header).text
    soup = BeautifulSoup(response_html, 'lxml')
    soup_pro_list = soup.find_all(name='h4', class_='prottl')
    for soup_profile in soup_pro_list:
        link = soup_profile.find(name='a')['href']
        pro_id = int(link[34:-5])
        if session.query(Project).\
                filter(Project.platform == 1).\
                filter(Project.pro_id == pro_id).count() == 0:
            new_project = ModianProject(pro_id)
            new_project.refresh_detail()
            session.add(new_project)
            logger.info("发现新项目:%s", new_project.title)
            logger.debug(str(new_project))
