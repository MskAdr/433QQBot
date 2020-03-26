import os

from sqlalchemy import create_engine

from fund.module import Base
import setting

engine = create_engine(setting.db_link())
Base.metadata.create_all(engine)

if not os.path.exists(setting.read_config('pk', 'cache_folder')):
    os.makedirs(setting.read_config('pk', 'cache_folder'))
if not os.path.exists(setting.read_config('pk', 'config_folder')):
    os.makedirs(setting.read_config('pk', 'config_folder'))
