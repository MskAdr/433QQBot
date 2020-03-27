import logging
import math
import random
import time
from typing import List

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session

from . import setting
from .modian import ModianProject, find_new_modian_project
from .module import Project, Order, Rank, User, Card, Card_Order, Card_User
from .owhat import OwhatProject
from .taoba import TaobaProject, find_new_taoba_project

logger = logging.getLogger('QQBot')


def project_factory(project: Project) -> Project:
    """工厂函数, 构建相应平台的Project."""
    if project.platform == 1:
        return ModianProject(project.pro_id, project.title,
                             project.start_time, project.end_time,
                             project.amount, project.order_num,
                             project.other_info)
    if project.platform == 2:
        return TaobaProject(project.pro_id, project.title,
                            project.start_time, project.end_time,
                            project.amount, project.order_num)
    if project.platform == 3:
        return OwhatProject(project.pro_id, project.title,
                            project.start_time, project.end_time,
                            project.amount, project.order_num)


def find_new_project(session: Session):
    """根据设定的应援会账户ID, 查找该应援会发布的新项目
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    """
    find_new_modian_project(session)
    find_new_taoba_project(session)


def get_started_project(session: Session) -> List[Project]:
    """根据设定的应援会账户ID, 查找该应援会发布的新项目
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    ### Result:
    ``project_list``: 正在进行的集资项目的列表
    """
    currentTime = int(time.time())
    return session.query(Project).\
        filter(Project.start_time <= currentTime).\
        filter(Project.end_time >= currentTime)


def get_preparing_project(session: Session) -> List[Project]:
    """根据设定的应援会账户ID, 查找该应援会发布的新项目
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    ### Result:
    ``project_list``: 尚未开始的集资项目的列表
    """
    currentTime = int(time.time())
    return session.query(Project).filter(Project.start_time > currentTime)


def find_user(session: Session, platform: int,
              user_id: int, nickname: str = '') -> User:
    """平台查找用户, 暂不支持o-what
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    ``platform``: 待查找的平台.\n
    ``user_id``: 平台上的用户id.\n
    ``nickname``: 需要刷新的昵称, 不填则为不需要刷新.\n
    ### Result:
    ``user``: 查找到的用户.\n
    """
    try:
        if platform == 1:   # 摩点
            result = session.query(User).\
                             filter(User.modian_id == user_id).one()
        if platform == 2:   # 桃叭
            result = session.query(User).\
                             filter(User.taoba_id == user_id).one()
        if result.qq_id is None:
            if nickname and result.nickname != nickname:
                logger.debug('用户%s的昵称变为%s', result.nickname, nickname)
                result.nickname = nickname
                session.flush()
        return result
    except NoResultFound:
        if platform == 1:   # 摩点
            result = User(nickname=nickname, modian_id=user_id)
        if platform == 2:   # 桃叭
            result = User(nickname=nickname, taoba_id=user_id)
        session.add(result)
        session.flush()
        logger.debug('添加用户%s', str(result))
        return result


def draw_card(session: Session, order: Order) -> str:
    """根据给定的订单随机抽取一张卡片.
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    ``order``: 待抽卡的订单.\n
    ### Result:
    ``message``: 抽卡后的反馈信息.\n
    """
    if not hasattr(order, 'nickname'):
        order.nickname = ''
    # 抽取卡牌
    threshold = float(setting.read_config('card', 'threshold'))
    divend = order.amount / threshold
    rand = abs(random.normalvariate(0, math.sqrt(divend)))
    if divend > 25:
        rand += math.log2(divend/25)
    if 1 < rand <= 2.5:
        rand = 1
    elif 2.5 < rand <= 5:
        rand = 2
    elif rand > 5:
        rand = 3
    rarity = int(rand)
    card_query = session.query(Card).filter(Card.rarity == rarity)
    card = card_query[random.randint(0, card_query.count()-1)]
    # 按订单插入记录
    session.add(Card_Order(
        order_id=order.id,
        rarity=rarity,
        type_id=card.type_id
    ))
    # 按用户插入记录
    user = find_user(session, order.platform, order.user_id, order.nickname)
    order.nickname = user.nickname
    session.merge(Card_User(
        user_id=user.id,
        rarity=rarity,
        type_id=card.type_id
    ))
    session.flush()
    # 生成信息
    collected_cards = session.query(Card_User).\
        filter(Card_User.user_id == user.id).\
        filter(Card_User.rarity == rarity).count()
    info_dict = {
        'nickname': order.nickname,
        'rarity': setting.rarity()[card.rarity],
        'name': card.name,
        'context': card.context,
        'user_amount': collected_cards,
        'total_amount': card_query.count(),
        'image': f'[CQ:image,file={card.file_name}]',
    }
    logger.debug('%s抽取到一张%s卡:%s', user.nickname,
                 info_dict['rarity'], card.name)
    pattern = setting.read_config('card', 'pattern')
    return pattern.format(**info_dict)


# TODO:增加单笔订单抽取多张卡牌


def check_new_order(session: Session, force: bool = False) -> List[str]:
    """根据给定的订单随机抽取一张卡片.
    ### Args:
    ``session``: 用于连接数据库的SQLAlchemy线程.\n
    ``force``: 无视项目数字更新与否, 强行检查项目.\n
    ### Result:
    ``message_list``: 处理订单后发送在QQ群里的信息.\n
    """
    project_list = get_started_project(session)
    message_list = list()
    for project in project_list:
        if not project.refresh_detail():
            # 强制刷新, 用于确认遗漏的订单
            if not force:
                logger.info('项目%s未发生更新', project.title)
                continue
        session.flush()
        order_list = project.get_new_orders(session, search_all=force)
        rank_query = session.query(Rank).\
            filter(Rank.platform == project.platform).\
            filter(Rank.pro_id == project.pro_id).order_by(Rank.amount.desc())
        for order in order_list:
            logger.debug('处理订单:%s', str(order))
            # 获取并修正排名信息
            try:
                rank = rank_query.filter(Rank.user_id == order.user_id).one()
                rank.amount += order.amount
                session.flush()
            # 没有找到排名信息
            except NoResultFound:
                rank = Rank(
                    platform=order.platform,
                    pro_id=order.pro_id,
                    user_id=order.user_id,
                    amount=order.amount
                )
                session.add(rank)
            # 生成集资播报信息
            ranking = rank_query.filter(Rank.amount > rank.amount).count()
            if ranking == 0:
                amount_distance = 0
            else:
                amount_distance = rank_query[ranking-1]
            support_num = rank_query.count()
            time_dist = float(project.end_time) - time.time()
            if time_dist >= 86400:
                time_to_end = f'{int(time_dist / 86400)}天'
            elif time_dist > 0:
                time_to_end = f'{round((time_dist / 3600), 2)}小时'
            else:
                time_to_end = '已经结束'
            average_amount = round(project.amount/support_num, 2)
            info_dict = {                                   # 可以提供的信息
                'title': project.title,                     # 项目标题
                'nickname': order.nickname,                 # 集资用户的昵称
                'amount': order.amount,                     # 该笔订单的金额
                'user_amount': rank.amount,                 # 该用户在当前项目的集资总数
                'ranking': ranking + 1,                     # 排名
                'amount_distance': amount_distance,         # 和前一名的金额差距
                'total_amount': project.amount,             # 项目总的集资额
                'supporter_num': support_num,               # 项目当前支持的人数
                'average_amount': average_amount,           # 每人平均支持的金额
                'time_to_end': time_to_end,                 # 格式化的结束时间
                'link': project.link()                      # 项目的链接
            }
            pattern = setting.read_config('fund', 'pattern')
            message = pattern.format(**info_dict)
            if order.amount < float(setting.read_config('card', 'threshold')):
                message += '\n你提供的能量尚不足以推开物资库的大门, 再努把力吧！'
                message_list.append(message)
                continue
            message_list.append(message)
            message_list.append(draw_card(session, order))
    return message_list
