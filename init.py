import os

from sqlalchemy import create_engine

from fund.module import Base
import pocket48
import setting

# 初始化数据库
print("建立数据库表格...")
engine = create_engine(setting.db_link())
Base.metadata.create_all(engine)
print("完成!")

# 建立PK配置和缓存的文件夹
print("建立PK配置文件和缓存文件...")
if not os.path.exists(setting.read_config('pk', 'cache_folder')):
    os.makedirs(setting.read_config('pk', 'cache_folder'))
if not os.path.exists(setting.read_config('pk', 'config_folder')):
    os.makedirs(setting.read_config('pk', 'config_folder'))

# 口袋48初始化
print("初始化口袋48设置")
pocket48.find_room(setting.read_config('system', 'idolname'))
