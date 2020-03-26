import os
import configparser

cfg_name = '../setting.conf'
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


def rarity() -> list:
    """返回卡牌稀有度的名称."""
    rarity = read_config('card', 'rarity')
    rarity_list = rarity.split(',')
    return rarity_list
