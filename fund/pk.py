# 选择用单独的程序运行, 是因为每次PK开始或结束都需要初始化一次任务调度器。
import pickle
import logging
import logging.config
from typing import List, Tuple

from . import setting
from . import project_factory
from .module import Project

logger = logging.getLogger('QQBot')


def get_pk_amount(project_list: List[Project],
                  battle_type: str = 'simple',
                  title: str = '') -> Tuple[dict, List[tuple]]:
    """获取各个pk项目的金额和按照要求排序的结果.
    ### Args:
    ``project_list``: 需要获取信息的项目列表.\n
    ``battle_type``: PK类型.\n
    ``title``: PK标题, 获取cache文件所需要的.\n
    ### Result:
    ``amount_dict``: 各个pk项目的总金额.\n
    ``sort_list``: 按要求排序后的元组列表, 第一项为名字, 第二项为数据.\n
    """
    if battle_type == 'increase':
        cache_file_name = (f'{setting.read_config("pk","cache_folder")}'
                           f'/{title}.pkcache')
        with open(cache_file_name, "rb") as f:
            record_amount_dict = pickle.load(f)
    amount_dict = dict()
    sort_dict = dict()
    for info in project_list:
        project = Project(info['platform'], info['pro_id'])
        project = project_factory(project)
        project.refresh_detail()
        amount_dict[info['idol']] = round(project.amount, 2)
        if battle_type == 'increase':
            record_amount = record_amount_dict[info['idol']]
            sort_dict[info['idol']] = round(project.amount - record_amount, 2)
        else:
            sort_dict[info['idol']] = round(project.amount, 2)
    return amount_dict, sorted(sort_dict.items(),
                               key=lambda d: d[1], reverse=True)


def get_pk_message(pk_data: dict):
    """构建PK播报的信息.
    ### Args:
    ``pk_data``: PK的配置信息.\n
    ### Result:
    ``message``: PK进展的播报信息.\n
    """
    message = pk_data['title'] + ':'
    amount_dict = dict()
    group_amount_dict = dict()
    group_message_dict = dict()
    group_id = 0
    for group in pk_data['pk_groups']:
        group_messsage = ''
        group_amount = 0
        result_dict, sorted_list = get_pk_amount(
            group['projects'],
            pk_data['battle_config']['type'],
            pk_data['title']
        )
        amount_dict.update(result_dict)
        prev_amount = -1.0
        for info in sorted_list:
            group_amount += info[1]
            group_messsage += f'\n  {info[0]}:{result_dict[info[0]]}'
            if pk_data['battle_config']['type'] == 'increase':
                group_messsage += f'\n   涨幅:{info[1]}'
            if prev_amount >= 0:
                group_messsage += f' ↑{round(prev_amount - info[1], 2)}'
            prev_amount = info[1]
        if pk_data['is_group_battle']:
            group_message_dict[group_id] = group_messsage
            group_amount_dict[group_id] = group_amount
            group_id += 1
    if pk_data['is_group_battle']:
        sorted_group_amount_list = sorted(group_amount_dict.items(),
                                          key=lambda d: d[1],
                                          reverse=True)
        prev_amount = -1.0
        for info in sorted_group_amount_list:
            message += f'\n {group["title"]}'
            if pk_data['battle_config']['type'] == 'increase':
                message += '(涨幅)'
            message += f':{info[1]}'
            if prev_amount >= 0:
                message += f' ↑{round(prev_amount - info[1], 2)}'
            message += group_message_dict[info[0]]
    else:
        message += group_messsage
    return message


def cache_pk_amount(pk_data: dict):
    """缓存记录PK的数据, 用于增量PK时计算差距.
    ### Args:
    ``title``: PK项目的标题.\n
    ``project_list``: 需要缓存的全部项目列表.\n
    """
    cache_file_name = (f"{setting.read_config('pk','cache_folder')}"
                       f'/{pk_data.title}.pkcache')
    amount_dict = dict()
    project_list = list()
    for group in pk_data['pk_groups']:
        project_list.extend(group['projects'])
    for info in project_list:
        project = Project(info['platform'], info['pro_id'])
        project.refresh_detail()
        amount_dict[info['idol']] = round(project.amount, 2)
    with open(cache_file_name, 'wb') as f:
        pickle.dump(amount_dict, f)
