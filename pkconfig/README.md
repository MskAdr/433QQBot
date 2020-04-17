## PK配置说明
根据PK项目的不同，需要调整不同的PK配置。  
当前支持普通模式（单纯对比金额）和增量模式（规定的时间点后的增量）。  
同时支持单人PK和分组PK。  
下面给出一个增量模式的例子：  
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
    //platform项，1表示摩点平台，2表示桃叭平台，3表示owhat平台
    "projects":[
        {"idol":"苏杉杉", "platform" : 2, "pro_id" : 1464},
        {"idol":"宋昕冉", "platform" : 3, "pro_id" : 90746}
    ]
}
```
下面给出一个分组PK的例子：  
```Javascript
{
    "title":"森林之王争霸赛",
    "key_word":["绝地反击","反击"],
    "extend_qq_groups":[],
    "is_group_battle": true,
    "start_time": "2020-04-15 18:00:00",
    "end_time": "2020-04-15 23:00:00",
    "battle_config":{
        "type":"sample"
    },
    //PK的组别配置
    "pk_groups":[
        {   "title":"未定组别1",
            "projects":[
                {"idol":"孙芮", "platform" : 2, "pro_id" : 2177}
            ]
        },
        {   "title":"未定组别2",
            "projects":[
                {"idol":"苏杉杉", "platform" : 2, "pro_id" : 2180},
                {"idol":"刘令姿", "platform" : 2, "pro_id" : 2182, "multiply" : 1.4}
            ]
        }
    ]
}
```