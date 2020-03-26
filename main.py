import time
import logging
import logging.config

from cqhttp import CQHttp
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import setting
import fund
import fund.pk

logger = logging.getLogger('QQBot')
bot = CQHttp(api_root='http://127.0.0.1:5700/')
sched = BackgroundScheduler()
engine = create_engine(setting.db_link())
# 列表中保存的是已经完成初始化的PK项目
pk_mission_started = list()
# 重复刷屏禁言的准备
repeat_message = dict()
for thisGrpID in setting.group_id():
    properties = ['message', 'user_id', 'times']
    repeat_message[thisGrpID] = {info: '' for info in properties}


# 发送集资信息
def send_raise_message(force=False):
    """发送集资消息
    ### Args:
    ``force``: 是否无视项目更新情况, 强行检索搜索项目.\n
    """
    try:
        session = sessionmaker(bind=engine)()
        logger.info('开始检查集资信息')
        message_list = fund.check_new_order(session, force)
        for message in message_list:
            for grp_id in setting.group_id():
                bot.send_group_msg_async(group_id=grp_id,
                                         message=message,
                                         auto_escape=False)
                time.sleep(0.5)
        session.commit()
    except Exception as e:
        logger.error(str(e), exc_info=True)
    finally:
        session.close()
        logger.info('集资信息检查完成')


def check_new_project():
    """查找并自动向数据库添加新订单"""
    try:
        session = sessionmaker(bind=engine)()
        logger.info('开始检查新项目')
        fund.find_new_project(session)
        session.commit()
    except Exception as e:
        logger.error(str(e), exc_info=True)
    finally:
        session.close()
        logger.info('新项目检查完成')


def send_pk_message(pk_data):
    """发送PK数据信息"""
    message = fund.pk.get_pk_message(pk_data)
    send_groups = setting.group_id() + pk_data['extend_qq_groups']
    for grp_id in send_groups:
        bot.send_group_msg_async(group_id=grp_id,
                                 message=message,
                                 auto_escape=False)


def pk_init():
    """PK项目初始化"""
    for pk_data in setting.pk_datas():
        if pk_data['title'] in pk_mission_started:
            continue
        if pk_data['battle_config']['type'] == 'increase':
            if time.mktime(time.strptime(pk_data['start_time'],
                                         '%Y-%m-%d %H:%M:%S')) > time.time():
                # 如果还没开始, 先保存零状态
                fund.pk.cache_pk_amount(pk_data)
            # 获取增量的时间节点
            time_list = pk_data['battle_config']['time_spot']
            for time_spot in time_list:
                sched.add_job(fund.pk.cache_pk_amount,
                              'date',
                              run_date=time_spot,
                              args=[pk_data])
        pk_interval = int(setting.read_config('pk', 'interval'))
        logger.info('对%s项目的PK播报将于%s启动,每%d秒钟一次',
                    pk_data['title'], pk_data['start_time'], pk_interval)
        sched.add_job(send_pk_message,
                      'interval',
                      seconds=pk_interval,
                      start_date=pk_data['start_time'],
                      end_date=pk_data['end_time'],
                      args=[pk_data])
        pk_mission_started.append(pk_data['title'])


@bot.on_message()
def handle_msg(context):
    """关键字响应\n
    目前设定了PK, 集资, 补档, 以及关键字撤回和重复刷屏禁言.
    """
    if (context['user_id'] != context['self_id']
            and context['message_type'] == 'group'):
        check_group_list = setting.group_id() + setting.dev_group_id()
        for pk_data in setting.pk_datas():
            if time.mktime(time.strptime(pk_data['end_time'],
                                         '%Y-%m-%d %H:%M:%S')) < time.time():
                continue
            if (context['group_id'] in pk_data['extend_qq_groups']
                    or context['group_id'] in check_group_list):
                if (context['message'] in ['PK', 'pk', 'Pk']
                        or context['message'] in pk_data['key_word']):
                    message = fund.pk.get_pk_message(pk_data)
                    bot.send(context, message)
        if (context['group_id'] in setting.group_id()
                or context['group_id'] in setting.dev_group_id()):
            if context['message'] == '集资':
                session = sessionmaker(bind=engine)()
                message = ''
                project_list = fund.get_started_project(session)
                if project_list.count() > 0:
                    for project in project_list:
                        message += f'{project.title}(准备中):{project.link()}\n'
                project_list = fund.get_prepared_project(session)
                if project_list.count() > 0:
                    for project in project_list:
                        message += f'{project.title}(准备中):{project.link()}\n'
                if message == '':
                    message = '暂时没有集资项目'
                session.close()
                bot.send(context, message.rstrip('\n'))
            if context['message'] == '补档':
                f = open('Links.txt', 'r', -1, 'utf-8')
                ori_message = f.read()
                message_list = ori_message.split('$')
                for message in message_list:
                    bot.send(context, message)
        # 敏感词撤回与重复刷屏禁言
        if context['group_id'] in setting.group_id():
            for word in setting.shutword():
                if word in context['message']:
                    bot.delete_msg(message_id=context['message_id'])
                    logger.info('成员%s的消息%s因为含有敏感词%s被撤回',
                                context['user_id'], context['message'], word)
            prev_message = repeat_message[context['group_id']]['message']
            prev_user = repeat_message[context['group_id']]['user_id']
            if (context['message'] == prev_message
                    and context['user_id'] == prev_user):
                repeat_message[context['group_id']]['time'] += 1
                logger.debug('成员%s重复发言第%d次', context['user_id'],
                             repeat_message[context['group_id']]['time'])
            else:
                repeat_message[context['group_id']]['time'] = 0
            repeat_message[context['group_id']]['message'] = context['message']
            repeat_message[context['group_id']]['user_id'] = context['user_id']
            if repeat_message[context['group_id']]['time'] >= 4:
                bot.set_group_ban(group_id=context['group_id'],
                                  user_id=context['user_id'],
                                  duration=60 * 60)
                logger.info('成员%s因为重复发言刷屏被禁言一小时', context['user_id'])


@bot.on_notice('group_increase')
def handle_group_increase(context):
    """加群发送欢迎消息"""
    if context['group_id'] in setting.group_id():
        welcome = [
            {'type': 'text', 'data': {'text': '欢迎'}},
            {'type': 'at', 'data': {'qq': str(context['user_id'])}},
            {'type': 'text', 'data': {'text': f'加入本群\n{setting.welcome()}'}}
        ]
        bot.send(context, message=welcome, auto_escape=True)


# TODO:加群验证处理
# TODO:好友验证处理
# TODO:卡牌查询处理


if __name__ == '__main__':
    # 配置日志记录器
    logger.setLevel(logging.DEBUG)
    fhandler = logging.FileHandler(setting.read_config('system', 'log'))
    fhandler.setLevel(logging.DEBUG)
    fhandler.setFormatter(
        logging.Formatter(("%(asctime)s - %(name)s - "
                           "%(levelname)s - %(module)s - %(message)s"))
    )
    logging.root.addHandler(fhandler)
    shandler = logging.StreamHandler()
    shandler.setLevel(logging.INFO)
    shandler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logging.root.addHandler(shandler)

    # 集资信息播报
    raise_interval = int(setting.read_config('fund', 'interval'))
    if raise_interval:
        send_raise_message(True)
        sched.add_job(send_raise_message, 'interval', seconds=raise_interval)
    # 项目自动添加
    autofind_interval = int(setting.read_config('fund', 'autofind'))
    if autofind_interval:
        check_new_project()
        sched.add_job(check_new_project, 'interval', seconds=autofind_interval)
    # PK项目自动初始化
    pkcheck_interval = int(setting.read_config('pk', 'interval')) / 2
    if pkcheck_interval:
        sched.add_job(pk_init, 'interval', minutes=pkcheck_interval)
    # 开始任务执行
    sched.start()
    # Docker虚拟网关地址 172.17.0.1
    bot.run(host='172.17.0.1', port=8080)
