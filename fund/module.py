import json

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import Session

Base = declarative_base()


class Project(Base):
    """用来表示集资项目的一个类.
    ### Args:
    ``platform``: 集资平台, 用一个id来表示, 1是摩点, 2指桃叭, 3指owhat.\n
    ``pro_id``: 项目在集资平台上的id.\n
    ``title``: 项目的标题.\n
    ``start_time``: 项目的开始时间, 用10位Unix时间戳表示.\n
    ``end_time``: 项目的结束时间, 用10位Unix时间戳表示.\n
    ``amount``: 项目当前筹集到的总金额.\n
    ``order_num``: 项目当前的订单数量.\n
    ``other_info``: 其他因为平台不同而需要追加的数据, 用JSON格式的字符串保留在数据库内.\n
    ### Attributes:
    ``refresh_detail``: 刷新项目的信息.\n
    ``get_ranks``: 获取项目当前集资排名列表.\n
    ``get_orders``: 获取项目当前全部订单列表.\n
    ``get_new_orders``: 获取项目当前最新订单列表.\n
    """
    __tablename__ = 'Project'
    platform = Column(Integer, nullable=False, primary_key=True)
    pro_id = Column(Integer, nullable=False, primary_key=True)
    title = Column(String(200), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    order_num = Column(Integer, nullable=False)
    other_info = Column(String(4000))
    __mapper_args__ = {
      'polymorphic_on': platform,
      'polymorphic_identity': 0
    }

    def __init__(self, platform: int, pro_id: int, title: str = '',
                 start_time: int = 0, end_time: int = 0, amount: int = 0,
                 order_num: int = 0, other_info: str = ''):
        self.platform = platform
        self.pro_id = pro_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.amount = amount
        self.order_num = order_num
        self.other_info = other_info

    def __repr__(self):
        """返回JSON格式的字符串"""
        profiles = {
            "pro_id": self.pro_id,
            "platform": self.platform,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "amount": self.amount,
            "order_num": self.order_num,
        }
        if self.other_info != '':
            profiles["other_info"] = json.loads(self.other_info)
        return json.dumps(profiles, ensure_ascii=False)

    def refresh_detail(self) -> bool:
        """从网络上刷新项目的基本信息.
        ### Result:
        ``result``: 相对于原来的数据, 集资金额是否发生了改变.
        这个数据可以用来判断属否需要刷新订单.\n
        """
        pass

    def get_ranks(self) -> list:
        """获取项目当前集资排名列表.
        ### Result:
        ``rank_list``: 一个内部为``Rank``内容的list, 按照金额从高到低排列.
        """
        pass

    def get_orders(self) -> list:
        """获取项目当前全部订单列表.
        ### Result:
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.\n
        """
        pass

    def get_new_orders(self, session: Session,
                       search_all: bool = False) -> list:
        """获取项目当前最新订单列表.
        ### Args:
        ``session``:用于连接数据库的SQLAlchemy线程.\n
        ``search_all``:是否需要全部检索整个订单列表来对比, 这项设置在桃叭当中暂时不起作用.\n
        ### Result:
        ``order_list``: 一个内部为``Order``内容的list, 包括这个项目的全部订单.
        """
        pass


class Order(Base):
    """用来记录排名的一个类
    ### Args:
    ``id``: 数据库自增数据, 可以不用手动设置.\n
    ``platform``: 集资平台, 用一个id来表示, 1是摩点, 2指桃叭, 3指owhat.\n
    ``pro_id``: 项目在集资平台上的id.\n
    ``user_id``: 在这里存储的是用户在平台上的用户id, 和数据库中的用户id不同, 请注意差别.\n
    ``nickname``: 用户的昵称, 这个数据并不会被记录在数据库当中, 如果之后想要查询用户的昵称, 应该通过数据库.\n
    ``amount``: 这个用户在该笔订单当中的集资金额.\n
    ``signature``: SHA1算法的签名, 用于快速区分不同的订单, 根据平台不同用于签名的元数据也不同.\n
    """
    __tablename__ = 'Order'
    id = Column(Integer, autoincrement=True, primary_key=True)
    platform = Column(Integer, ForeignKey('Project.platform'), nullable=False)
    pro_id = Column(Integer, ForeignKey('Project.pro_id'), nullable=False)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    signature = Column(String(40), nullable=False)

    def __init__(self, platform: int, pro_id: int, user_id: int,
                 nickname: int, amount: int, signature: int):
        self.platform = platform
        self.pro_id = pro_id
        self.user_id = user_id
        self.nickname = nickname
        self.amount = amount
        self.signature = signature

    def __repr__(self):
        """返回JSON格式的字符串"""
        profiles = {
            "pro_id": self.pro_id,
            "platform": self.platform,
            "user_id": self.user_id,
            "amount": self.amount,
            "signature": self.signature
        }
        if hasattr(self, 'nickname'):
            profiles['nickname'] = self.nickname
        return json.dumps(profiles, ensure_ascii=False)


class Rank(Base):
    """用来记录排名的一个类
    ### Args:
    ``platform``: 集资平台, 用一个id来表示, 1是摩点, 2指桃叭, 3指owhat.\n
    ``pro_id``: 项目在集资平台上的id.\n
    ``user_id``: 在这里存储的是用户在平台上的用户id, 和数据库中的用户id不同, 请注意差别.\n
    ``amount``: 这个用户在当前项目当中总的集资金额.\n
    """
    __tablename__ = 'Rank'
    platform = Column(Integer, ForeignKey('Project.platform'),
                      primary_key=True, nullable=False)
    pro_id = Column(Integer, ForeignKey('Project.pro_id'),
                    primary_key=True, nullable=False)
    # 集资平台的用户ID, 不是数据库当中的用户ID
    user_id = Column(Integer, primary_key=True, nullable=False)
    amount = Column(Float, nullable=False)

    def __init__(self, platform: int, pro_id: int,
                 user_id: int, amount: float):
        self.platform = platform
        self.pro_id = pro_id
        self.user_id = user_id
        self.amount = amount

    def __repr__(self):
        """返回JSON格式的字符串"""
        profiles = {
            "pro_id": self.pro_id,
            "platform": self.platform,
            "user_id": self.user_id,
            "amount": self.amount
        }
        return json.dumps(profiles, ensure_ascii=False)


class User(Base):
    """用来记录用户的一个类
    ### Args:
    ``id``: 数据库自增数据, 可以不用手动设置.\n
    ``platform``: 集资平台, 用一个id来表示, 1是摩点, 2指桃叭, 3指owhat.\n
    ``pro_id``: 项目在集资平台上的id.\n
    ``user_id``: 在这里存储的是用户在平台上的用户id, 和数据库中的用户id不同, 请注意差别.\n
    ``amount``: 这个用户在当前项目当中总的集资金额.\n
    """
    __tablename__ = 'User'
    id = Column(Integer, autoincrement=True, primary_key=True)
    nickname = Column(String(100))
    qq_id = Column(String(50))
    modian_id = Column(Integer)
    taoba_id = Column(Integer)
    owhat_id = Column(Integer)

    def __init__(self, nickname: str = '', qq_id: str = '', modian_id: int = 0,
                 taoba_id: str = 0, owhat_id: str = 0):
        self.nickname = nickname
        self.qq_id = qq_id
        self.modian_id = modian_id
        self.taoba_id = taoba_id
        self.owhat_id = owhat_id

    def __repr__(self):
        """返回JSON格式的字符串"""
        profiles = {
            "id": self.id,
            "nickname": self.nickname,
            "qq_id": self.qq_id,
            "modian_id": self.modian_id,
            "taoba_id": self.taoba_id
        }
        return json.dumps(profiles, ensure_ascii=False)


class Card(Base):
    """用来记录卡牌的一个类
    ### Args:
    ``rarity``: 卡牌的稀有度.\n
    ``type_id``: 卡牌在当前稀有度当中的id.\n
    ``name``: 卡牌的名称.\n
    ``context``: 卡牌的说明.\n
    ``file_name``: 卡牌文件的存储位置.\n
    """
    __tablename__ = 'Card'
    rarity = Column(Integer, nullable=False, primary_key=True)
    type_id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String(50))
    context = Column(String(200))
    file_name = Column(String(200))

    def __init__(self, rarity, type_id, name='', context='', file_name=''):
        self.rarity = rarity
        self.type_id = type_id
        self.name = name
        self.context = context
        self.file_name = file_name


class Card_User(Base):
    """用来记录用户持有卡牌的一个类
    ### Args:
    ``user_id``: 用户的id.\n
    ``rarity``: 卡牌的稀有度.\n
    ``type_id``: 卡牌在当前稀有度当中的id.\n
    """
    __tablename__ = 'Card_User'
    user_id = Column(Integer, ForeignKey('User.id'),
                     nullable=False, primary_key=True)
    rarity = Column(Integer, ForeignKey('Card.rarity'),
                    nullable=False, primary_key=True)
    type_id = Column(Integer, ForeignKey('Card.type_id'),
                     nullable=False, primary_key=True)

    def __init__(self, user_id, rarity, type_id):
        self.user_id = user_id
        self.rarity = rarity
        self.type_id = type_id


class Card_Order(Base):
    """用来记录卡牌和订单关系的一个类
    ### Args:
    ``order_id``: 订单的id.\n
    ``rarity``: 卡牌的稀有度.\n
    ``type_id``: 卡牌在当前稀有度当中的id.\n
    """
    __tablename__ = 'Card_Order'
    order_id = Column(Integer, ForeignKey('Order.id'),
                      nullable=False, primary_key=True)
    rarity = Column(Integer, ForeignKey('Card.rarity'),
                    nullable=False, primary_key=True)
    type_id = Column(Integer, ForeignKey('Card.type_id'),
                     nullable=False, primary_key=True)

    def __init__(self, order_id, rarity, type_id):
        self.order_id = order_id
        self.rarity = rarity
        self.type_id = type_id
