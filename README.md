433QQBot  
=================================
苏杉杉应援会的QQ机器人，现在主要包括集资播报等功能，微博播报和口袋播报会在随后快速添加到项目中。  
2020年3月由原项目重构而来，主要增加了SQLAlchemy的支持，并且将多平台的集资播报统一化，便于日后扩展。  
苏杉杉应援会：367765646。青春有你专群：1029856946  

## 说明与感谢  
基于Docker和酷QHTTP开发而来，在我接手前的原项目基本上是黄子璇应援会机器人项目的fork，在此特别感谢[chinshin/CQBot_hzx](https://github.com/chinshin/CQBot_hzx)  
目前重构工作尚未完成，由于应援会暂时还不需要，所以暂时还没有完成口袋48和微博的抓取，等待之后补完。  
另外由于微信小经费不再用于集资，所以放弃开发。
因为应援会放弃使用owhat平台，所以开发仅完成了获取排名和项目信息的部分，并没有开发获取订单的部分。如果有需要欢迎提出issue。  

## 更新日志
### 2020年3月26日更新
完全重构，清理了commit记录。现在可以通过模式字符串来自定义订单和抽卡的消息了。  
同时对抽卡算法进行了修正，当前抽卡的算法如下：  
> 首先求订单金额和阈值的商，称为r。  
> 随后生成一个正态分布的随机数，均值为0，方差为r。  
> 接下来对这个随机数求绝对值。  
> 如果r大于等于25，就再加上以2为底，r/25的对数。  
> 然后按照下面的表格分配稀有度。  
> |随机数|0~1|1~2.5|2.5~5|5~∞|
> |-----|---|-----|-----|---|
> |稀有度|0  |1    |2    |3  |
>  
> 最后按照平均分布抽取出一张卡牌，就是最后的结果了。

## 配置方法
### 环境配置
在Linux平台下，首先请安装好Docker，然后下载richardchien的基于Docker的镜像。  
以下内容来自于[Docker说明](https://cqhttp.cc/docs/4.14/#/Docker)
``` bash
$ docker pull richardchien/cqhttp:latest
$ mkdir coolq  # 用于存储 酷Q 的程序文件
$ docker run -ti --rm --name cqhttp-test \
             -v $(pwd)/coolq:/home/user/coolq \  # 将宿主目录挂载到容器内用于持久化 酷Q 的程序文件
             -p 9000:9000 \  # noVNC 端口，用于从浏览器控制 酷Q
             -p 5700:5700 \  # HTTP API 插件开放的端口
             -e COOLQ_ACCOUNT=123456 \ # 要登录的 QQ 账号，可选但建议填
             -e CQHTTP_POST_URL=http://example.com:8080 \  # 事件上报地址
             -e CQHTTP_SERVE_DATA_FILES=yes \  # 允许通过 HTTP 接口访问 酷Q 数据文件
             richardchien/cqhttp:latest
```
随后在主机上安装`python3.8`，将本脚本全部源码传送至相应文件夹，执行`pip3 install -r requirements.txt`安装依赖。  
### 选项和设定
启动之前需要在项目根目录下创建一个基础的setting.conf配置文件  
``` ini
[system]
idolname = 苏杉杉
idolgroup = bej
# 数据库保存位置，当前项目使用SQLite3
database = Database.db
# 日志文件保存位置    
log = log.log

[QQgroup]
# 配置用于播报集资信息等的QQ群
id = 367765646,609913800,1029856946
# 用于测试的QQ群，集资信息不会在里面播报
dev_id = 1025039615
# 新人加群时的欢迎词
welcome = 欢迎聚聚加入苏杉杉的应援群！
# 关键词禁言，用英文逗号分割
shutword = 

[fund]
# 集资播报时间间隔，单位是秒，为0表示不播报
interval = 20
# 自动检测集资项目的时间间隔，单位是秒，为0表示不播报
autofind = 1800
# 播报集资信息的模版，如果有有关其他信息的需求，请自行更改fund/__init__.py
# title: 项目标题
# nickname: 集资用户的昵称
# amount: 该笔订单的金额
# user_amount: 该用户在当前项目的集资总数
# ranking: 排名
# amount_distance: 和前一名的金额差距(第一名的这个数值被设定为0)
# total_amount: 项目总的集资额
# average_amount: 项目平均集资额
# time_to_end: 项目的剩余时间，大于一天的会显示XX天，小于一天的会显示XX.XX小时
# link: 项目的链接
pattern = 感谢{nickname}在项目{title}中集资{amount}元，共{user_amount}元。
    排名第{ranking}，目前与前一名还差{amount_distance}元。
    本项目目前集资{total_amount}元，有{supporter_num}人参加，人均{average_amount}元。
    当前剩余时间：{time_to_end}，神秘地址: {link}
[card]
# 抽卡阈值, 若为0则表示关闭抽卡功能
threshold = 4.33
# 不同稀有度卡牌的名称
rarity = 普通,精良,史诗,传说
# 播报抽卡信息的模版，如果有有关其他信息的需求，请自行更改fund/__init__.py
# nickname: 用户的昵称
# rarity: 卡牌的稀有度
# name: 卡牌的名字
# context: 卡牌的文本
# user_amount: 该用户在当前稀有度下收集到的卡牌数
# total_amount: 当前稀有度总的卡牌数
# image: CQ码格式的图片
pattern = {nickname}抽取到了一张{rarity}卡：{name}。
    {context}
    当前{rarity}卡牌收集进度：{user_amount}/{total_amount}。
    {image}
[modian]
# 应援会的摩点id，用于自动搜索项目
userid = 1094709
[taoba]
# 桃叭的用户名和密码以及token
# 登录之后可以查看每个项目的详细订单信息，并且可以自动搜索添加项目
username = username
password = password
signature = none
[pk]
# PK播报时间间隔，单位是秒
interval = 1800
# PK缓存文件存放文件夹，详细可以看PK配置篇
cache_folder = pkcache
# PK配置文件存放文件夹，详细可以看PK配置篇
config_folder = pkconfig
# PK项目的列表
pk_lists = 2020_03_20.json
```
随后执行`python3 init.py`来创建数据库和相关目录。  
数据库建好之后需要手动添加卡牌信息。  
Linux平台下可以直接执行`sqlite3 Database.db`命令来增加或者修改卡牌数据。  
也可以寻找sqlite3可视化工具来添加卡牌信息。  
如果需要增加PK项目，可以参照以下配置在相应的文件夹当中新建一个PK项目：  
``` Javascript
{
    //PK项目的Title
    "title":"青春有你2-绝地反击",
    //可以在群内触发机器人回复的关键词
    "key_word":["绝地反击","反击"],
    //PK项目如果需要额外在别的群播报，请添加此项
    "extend_qq_groups":[23252440],
    //是不是分组PK，还是个人战，分组PK请选择true
    "is_group_battle":false,
    //PK起止时间
    "start_time": "2020-03-23 19:00:00",
    "end_time": "2020-03-25 19:00:00",
    //PK类型，目前支持单纯的总额(simple)，和固定时间点后的增量(increase)
    //如果选择增量模式，需要配置缓存的时间点
    "battle_config":{
        "type":"increase",
        "time_spot":["2020-03-23 19:00:00","2020-03-24 19:00:00"]
    },
    //PK的组别，就算个人战也应该配置至少一个组别
    //platform项，1表示摩点平台，2表示桃叭平台，3表示owhat平台
    "pk_groups":[
        {   "title":"未定组别",
            "projects":[
                {"idol":"苏杉杉", "platform" : 2, "pro_id" : 1464},
                {"idol":"宋昕冉", "platform" : 3, "pro_id" : 90746}
            ]
        }
    ]
}
```
### 启动
在noVNC设定好酷Q登录的账号后，切换到机器人脚本所在文件夹下，执行`nohup python3 main.py &`命令。  
确定情况无误后用`exit`退出ssh链接，如果直接关闭可能导致进程退出。  