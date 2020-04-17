# 选择用单独的程序运行, 是因为每次PK开始或结束都需要初始化一次任务调度器。
import pickle
import logging
import logging.config

from . import setting
from . import project_factory
from .module import Project

logger = logging.getLogger('QQBot')


def _get_pk_amount(project_list: list) -> dict:
    """获取各个pk项目的金额.
    ### Args:
    ``project_list``: 需要获取信息的项目列表.\n
    ### Result:
    ``amount_dict``: 各个pk项目的总金额.\n
    """
    amount_dict = dict()
    for info in project_list:
        project = Project(info['platform'], info['pro_id'])
        project = project_factory(project)
        project.refresh_detail()
        amount_dict[info['idol']] = round(project.amount, 2)
        if 'multiply' in info:
            amount_dict[info['idol']] *= info['multiply']
            amount_dict[info['idol']] = round(amount_dict[info['idol']], 2)
    return amount_dict


def _build_simple_pk_message(amount_dict: dict) -> str:
    """根据集资信息构建普通模式下PK播报的信息.
    ### Args:
    ``amount_dict``: 项目的集资信息.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    message = ''
    prev_amount = -1
    sorted_list = sorted(amount_dict.items(), key=lambda d: d[1], reverse=True)
    for info in sorted_list:
        message += f'\n  {info[0]}:{info[1]}'
        if prev_amount >= 0:
            message += f' ↑{round(prev_amount - info[1], 2)}'
        prev_amount = info[1]
    return message


def _get_pk_message_simple(project_list: list) -> str:
    """根据项目列表构建普通模式下PK播报的信息.
    ### Args:
    ``project_list``: PK的项目列表.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    amount_dict = _get_pk_amount(project_list)
    return _build_simple_pk_message(amount_dict)


def _get_pk_message_group_simple(group_list: list) -> str:
    """根据分组列表构建普通模式下PK播报的信息.
    ### Args:
    ``group_list``: PK的分组列表.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    group_message = dict()
    group_amount = dict()
    for group in group_list:
        amount_dict = _get_pk_amount(group['projects'])
        total_amount = 0
        for idol in amount_dict.keys():
            total_amount += amount_dict[idol]
        group_message[group["title"]] = _build_simple_pk_message(amount_dict)
        group_amount[group["title"]] = round(total_amount, 2)
    group_list = sorted(group_amount.items(), key=lambda d: d[1], reverse=True)
    prev_amount = -1
    message = ''
    for info in group_list:
        message += f'\n {info[0]}:{info[1]}'
        if prev_amount >= 0:
            message += f' ↑{round(prev_amount - info[1], 2)}'
        message += group_message[info[0]]
        prev_amount = info[1]
    return message


def _build_increase_pk_message(amount_dict: dict,
                               increase_dict: dict) -> str:
    """根据集资信息构建增量模式下PK播报的信息.
    ### Args:
    ``amount_dict``: 项目的集资信息.\n
    ``increase_dict``: 项目的增量信息.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    message = ''
    prev_amount = -1
    sorted_list = sorted(increase_dict.items(),
                         key=lambda d: d[1], reverse=True)
    for info in sorted_list:
        message += f'\n  {info[0]}:{amount_dict[info[0]]}'
        if prev_amount >= 0:
            message += f' ↑{round(prev_amount - info[1], 2)}'
        message += f'\n   涨幅:{info[1]}'
        prev_amount = info[1]
    return message


def _get_pk_message_increase(cache_dict: dict,
                             project_list: list) -> str:
    """根据项目列表构建增量模式下PK播报的信息.
    ### Args:
    ``cache_dict``: 增量计算的基础.\n
    ``project_list``: PK的项目列表.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    amount_dict = _get_pk_amount(project_list)
    increase_dict = dict()
    for idol in amount_dict.keys():
        increase_dict[idol] = amount_dict[idol] - cache_dict[idol]
        increase_dict[idol] = round(increase_dict[idol], 2)
    return _build_increase_pk_message(amount_dict, increase_dict)


def _get_pk_message_group_increase(cache_dict: dict,
                                   group_list: list) -> str:
    group_message = dict()
    group_amount = dict()
    for group in group_list:
        amount_dict = _get_pk_amount(group['projects'])
        increase_dict = dict()
        for idol in amount_dict.keys():
            increase_dict[idol] = amount_dict[idol] - cache_dict[idol]
            increase_dict[idol] = round(increase_dict[idol], 2)
        total_amount = 0
        for idol in amount_dict.keys():
            total_amount += increase_dict[idol]
        group_message[group["title"]] = _build_increase_pk_message(
            amount_dict,
            increase_dict
        )
        group_amount[group["title"]] = round(total_amount, 2)
    group_list = sorted(group_amount.items(), key=lambda d: d[1], reverse=True)
    prev_amount = -1
    message = ''
    for info in group_list:
        message += f'\n {info[0]}(涨幅):{info[1]}'
        if prev_amount >= 0:
            message += f' ↑{round(prev_amount - info[1], 2)}'
        message += group_message[info[0]]
        prev_amount = info[1]
    return message


def get_pk_message(pk_data: dict):
    """构建PK播报的信息.
    ### Args:
    ``pk_data``: PK的配置信息.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    message = ''
    if pk_data['battle_config']['type'] == 'simple':
        if pk_data['is_group_battle']:
            message = _get_pk_message_group_simple(pk_data['pk_groups'])
        else:
            message = _get_pk_message_simple(pk_data['projects'])
    elif pk_data['battle_config']['type'] == 'increase':
        cache_file_name = (f'{setting.read_config("pk","cache_folder")}'
                           f'/{pk_data["title"]}.pkcache')
        with open(cache_file_name, 'rb') as f:
            cache_dict = pickle.load(f)
        if pk_data['is_group_battle']:
            message = _get_pk_message_group_increase(cache_dict,
                                                     pk_data['pk_groups'])
        else:
            message = _get_pk_message_increase(cache_dict, pk_data['projects'])
    message = pk_data['title'] + ':' + message
    return message


def cache_pk_amount(pk_data: dict):
    """缓存记录PK的数据, 用于增量PK时计算差距.
    ### Args:
    ``title``: PK项目的标题.\n
    ``project_list``: 需要缓存的全部项目列表.\n
    """
    cache_file_name = (f"{setting.read_config('pk','cache_folder')}"
                       f'/{pk_data["title"]}.pkcache')
    amount_dict = dict()
    project_list = list()
    if pk_data['battle_config']['type'] == 'simple':
        project_list = pk_data['projects']
    elif pk_data['battle_config']['type'] == 'increase':
        for group in pk_data['pk_groups']:
            project_list.extend(group['projects'])
    # 对每个Project单独刷新信息
    for info in project_list:
        project = Project(info['platform'], info['pro_id'])
        project = project_factory(project)
        project.refresh_detail()
        amount_dict[info['idol']] = round(project.amount, 2)
    with open(cache_file_name, 'wb') as f:
        pickle.dump(amount_dict, f)
