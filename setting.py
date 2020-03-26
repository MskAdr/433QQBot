import os
import json
import configparser

cfg_name = 'setting.conf'
BASE_DIR = os.path.dirname(__file__)
FILE_PATH = os.path.join(BASE_DIR, cfg_name)
cf = configparser.ConfigParser()


def read_config(section: str, option: str) -> str:
    """读取指定的配置值.
    ### Args:
    ``section``: 在conf文件中的段落.\n
    ``option``: 在conf文件中的选项.\n
    ### Result:
    ``result``: 所读取到的配置值.
    """
    with open(FILE_PATH, 'r', encoding='utf-8') as cfgfile:
        cf.read_file(cfgfile)
        result = cf.get(section, option)
    return str(result)


def write_config(section: str, option: str, value: str) -> str:
    """写入指定的配置值.
    ### Args:
    ``section``: 在conf文件中的段落.\n
    ``option``: 在conf文件中的选项.\n
    """
    with open(FILE_PATH, 'r', encoding='utf-8') as cfgfile:
        cf.read_file(cfgfile)
        with open(FILE_PATH, 'w+', encoding='utf-8') as cfgfile2:
            cf.set(section, option, value)
            cf.write(cfgfile2)


def group_id() -> list:
    """返回一个需要发送信息的QQ群的列表."""
    group_id = read_config('QQgroup', 'id')
    array = list(map(int, group_id.split(',')))
    return array


def dev_group_id() -> list:
    """返回一个开发和实验用的QQ群的列表."""
    group_id = read_config('QQgroup', 'dev_id')
    array = list(map(int, group_id.split(',')))
    return array


def welcome() -> str:
    """返回一个字符串, 是QQ群的欢迎词, 并且将conf当中的换行符还原."""
    message = read_config('QQgroup', 'welcome')
    return message.replace('\\n', '\n')


def shutword() -> list:
    """返回一个敏感词列表."""
    shutword = read_config('QQgroup', 'shutword')
    if shutword:
        wordlist = shutword.split(',')
    else:
        wordlist = list()
    return wordlist


def db_link() -> str:
    """返回一个适用于SQLAlchemy的数据库链接."""
    return 'sqlite:///'+read_config('system', 'database')


def pk_datas() -> list:
    """返回一个列表, 里面每一项都是经过JSON解码的PK设置."""
    pk_configs = read_config('pk', 'pk_lists')
    if pk_configs:
        pk_array = list(pk_configs.split(','))
    else:
        pk_array = list()
    pk_datas = list()
    for config in pk_array:
        with open(read_config('pk', 'config_folder') + '/' + config, "r") as f:
            pk_datas.append(json.loads(f.read()))
    return pk_datas
