# -*- coding: utf-8 -*-
import re
import pymongo
import cfscrape
import json
import pytz
import json_tools
import datetime
from auth import protected
from login import login
from sanic import Sanic
from sanic import response
from sanic.response import json as sanic_json
from sanic_jinja2 import SanicJinja2
from python_paginate.css.semantic import Semantic
from python_paginate.web.sanic_paginate import Pagination

app = Sanic(__name__)

#update pagination settings
settings = dict(PREV_LABEL='<i class="left chevron icon"></i>',
                NEXT_LABEL='<i class="right chevron icon"></i>',
                PER_PAGE=10,  # default is 10
                )
                
app.config.update(settings)


app.config.SECRET = "Hostlocasgfddasdasdasgerher"

app.blueprint(login)

jinja = SanicJinja2(app, autoescape=True)

# customize default pagination
if 'PREV_LABEL' in app.config:
    Semantic._prev_label = app.config.PREV_LABEL

if 'NEXT_LABEL' in app.config:
    Semantic._next_label = app.config.NEXT_LABEL

Pagination._css = Semantic()  # for cache

Pagination._per_page = app.config.PER_PAGE


# 新建数据库链接
# 线上数据库(只读权限)
# mongo_client = pymongo.MongoClient("mongodb://hostloc:hostloc123@virmach-shard-00-00.3elqu.mongodb.net:27017,virmach-shard-00-01.3elqu.mongodb.net:27017,virmach-shard-00-02.3elqu.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-zq6s5l-shard-0&authSource=admin&retryWrites=true&w=majority")

# 测试数据库(读写权限)
mongo_client = pymongo.MongoClient("mongodb://u4fdhdfn2eoxb9r8wwnz:5bwrws3cyjAxv8YR7RjT@bboxdt6j4eek9wg-mongodb.services.clever-cloud.com:27017/bboxdt6j4eek9wg")


# 判断是否连接成功
# print(mongo_client.server_info())

# 链接数据库，不存在则新建(线上数据库)
#mongo_db = mongo_client['virmach']

# 链接数据库，不存在则新建(测试数据库)
mongo_db = mongo_client['bboxdt6j4eek9wg']

# 链接数据表，不存在则新建
mongo_collection = mongo_db['info']

# 新建scraper实例
scraper = cfscrape.create_scraper()


# 检查数据是否正常
def check_json(input_str):
    try:
        json.loads(input_str)
        return True
    except:
        return False

# 检查数据是否有变化，有变化返回False
def check_update(old_json, new_json):
    if json_tools.diff(old_json,new_json):
        return False
    else:
        return True

# 格式化你想要的数据
def Formatdata(data):
    info = {
        'price' : re.findall(r"\d+\.?\d*",data['price'])[0],
        'cpu' : data['cpu'],
        'ram' : data['ram'],
        'hdd' : data['hdd'],
        'bw' : data['bw'],
        'ips' : data['ips'],
        'virt' : data['virt'],
        'location' : data['location'],
        'win' : data['windows'],
        'message' : data['message'],
        'ended' : data['ended'],
        'url' : 'https://billing.virmach.com/cart.php?a=add&pid=' + str(data['pid']) + '&billingcycle=annually'
    }
    return info
    
# 向数据库中插入数据
def Insert(data):
    # 添加date字段
    data["date"] = datetime.datetime.now(pytz.timezone('PRC')).strftime("%Y-%m-%d %H:%M:%S")
    # 删ended除字段
    del data["ended"]
    # 执行插入
    mongo_collection.insert_one(data)
    
# 查询数据库中的数据
def FindAll():
    list   = []
    curs = mongo_collection.find()
    for cur in curs:
        # 去除_id字段
        del cur["_id"]
        list.append(cur)
    # 返回倒序查询结果
    return list[::-1]


# 从官方地址获取抢购信息
def Getinfo():
    # 不在黑五时期的页面信息
    buyinfo = {'date': 'null', 'price': 'null', 'cpu': 0, 'ram': '0', 'hdd': 0, 'bw': 0, 'ips': 0, 'virt': 'null', 'location': 'null', 'win': 'null', 'message': 'null',"ended":"已结束", 'url': ''}
    old_data = 'Please only have one black friday page open at any given time, and if you are on a third party website ensure that you are not having it refreshed too often in the background'
    web_data = scraper.get("https://billing.virmach.com/modules/addons/blackfriday/new_plan.json").content
    
    # 
    if(web_data != old_data):
        # 有时候会请求不到数据
        if check_json(web_data):
            data_test = json.loads(web_data)
            # 判断是否售罄
            if('ended' in data_test):
                # 拼接自己要的格式数据
                del data_test["ended"]
                data_test["ended"] = "已售罄"
                data_test["url"] = 'https://billing.virmach.com/cart.php?a=add&pid=' + str(data_test['pid']) + '&billingcycle=annually'
                return Formatdata(data_test)
            else:
                # 
                with open("./old.json","r") as f:
                    s = json.load(f)
                    old_json = json.dumps(json.loads(s))
                    # 判断是否有更新
                    if check_update(json.loads(old_json), json.loads(web_data)):
                        buyinfo = json.loads(web_data)
                        buyinfo["url"] = 'https://billing.virmach.com/cart.php?a=add&pid=' + str(buyinfo['pid']) + '&billingcycle=annually'
                        buyinfo["ended"] = "销售中"
                        return Formatdata(buyinfo)
                    else :
                        # 有更新，将新的数据写入文件，方便下次比较
                        buyinfo = json.loads(web_data)
                        try:
                            with open("./old.json","w") as f:
                                s = json.dumps(buyinfo)
                                json.dump(s,f)
                                print(Formatdata(buyinfo))
                        except Exception as e:
                            print(str(e))
                        buyinfo["url"] = 'https://billing.virmach.com/cart.php?a=add&pid=' + str(buyinfo['pid']) + '&billingcycle=annually'
                        buyinfo["ended"] = "销售中"
                        # 插入数据库
                        Insert(buyinfo)
                        return Formatdata(buyinfo)
    else:
        # 活动结束就返回设置的无用数据
        return buyinfo

@app.get('/json')
@protected
async def handler(request):
    # 返回抢购数据
    return sanic_json(Getinfo())

@app.route('/')
async def index(request):
    # 接收分页器数据
    page, per_page, offset = Pagination.get_page_args(request)
    # 获取所有数据 (ps：我太垃圾了，不会条件查询)
    data_all = FindAll()
    #print(Getinfo())
    # 获得数据总数
    total = len(data_all)
    # 按分页器返回的数据进行分片
    data_all_page = [data_all[i:i + per_page] for i in range(0, len(data_all), per_page)]
    # 返回该页数据
    datas = data_all_page[page-1]
    # 配置分页器
    pagination = Pagination(request, total=total, record_name='datas')
    # 返回页面
    return jinja.render('index.html', request, datas=datas,
                        pagination=pagination)

#if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=8080, access_log=False)
app.run(host='0.0.0.0', port=8080, debug=True, access_log=True)
