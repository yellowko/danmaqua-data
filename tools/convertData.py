from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests
import json
import sys

version = 2

data = dict({
    "version": version,
    "_description": "订阅界面中将推荐的虚拟主播数据",
    "data": []
})

cataData = dict({
    "version": version,
    "data": []
})

vtubers = dict()

def add_cata(res:dict,group:str,vtb:dict):
    if( (res != None) and ("result" in res["data"])):
        for data in cataData["data"]:
            if(data["name"] == group):
                data["count"] += 1
                vtubers[group]["data"].append(dict({
                    "uid": vtb["uid"],
                    "room": vtb["room"],
                    "name": vtb["name"],
                    "group": group,
                    "description": vtb["reason"],
                    "face": vtb["face"]
                }))
                return
        cataData["data"].append(dict({
            "name": group,
            "title": group,
            "icon": "https:" + res["data"]["result"][0]["upic"],
            "count": 1
        }))
        vtubers[group] = dict({
            "version": version,
            "name": group,
            "title": group,
            "data":[]
        })     
    else:   #搜不到
        for data in cataData["data"]:
            if(data["name"] == "unclassified"):
                data["count"] += 1
                vtubers["unclassified"]["data"].append(dict({
                    "uid": vtb["uid"],
                    "room": vtb["room"],
                    "name": vtb["name"],
                    "group": "unclassified",
                    "description": vtb["reason"],
                    "face": vtb["face"]
                }))
                return
        cataData["data"].append(dict({
            "name": "unclassified",
            "title": "个人势或者未统计到所属团体的VTBs",
            "icon": "https://i1.hdslb.com/bfs/face/1efe4203415ba8d0411fd168096ad890d69de61d.jpg",
            "count": 1
        }))
        vtubers["unclassified"] = dict({
            "version": version,
            "name": "unclassified",
            "title": "unclassified",
            "data":[]
        })

# w_rid验证
mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    # print(mixin_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys():
    '获取最新的 img_key 和 sub_key'
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav')
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

try:
    img_key, sub_key = getWbiKeys()
except Exception as e:
    print("\n客户端连接失败，请检查自己的网络连接情况，如果有代理请关闭\n")
    print(e.args)
    sys.exit()
# print(img_key)
# print(sub_key)
# img_key = "9a16e2304d794393b733badf79f09804"
# sub_key = "69c7f4b06e3f44449a54ad06ca05676c"


# 解析 https://vdb.vtbs.moe/json/list.json 数据

response = json.loads(requests.get(url="https://vdb.vtbs.moe/json/list.json").text)
# response = json.loads(open('../raw//list.json','r',encoding='utf8').read())

# 获取 platform为bilibili 平台的
bilibili_req=requests.get(url="https://bilibili.com",headers={"User-Agent": "Mozilla/5.0","Accept":"text/html"})

try:
    for i in range(0,len(response["vtbs"])-1):
        vtb = response["vtbs"][i]
        for account in vtb["accounts"]:
            if account["platform"] == "bilibili":
                signed_params = encWbi(
                    params={
                        'mid': account["id"]
                    },
                    img_key=img_key,
                    sub_key=sub_key
                )
                query = urllib.parse.urlencode(signed_params)
                res = json.loads(requests.get(url="https://api.bilibili.com/x/space/wbi/acc/info?" + query,headers={"User-Agent": "Mozilla/5.0","Accept":"text/html"}).text)
                if(res["code"] == 0 and res["data"]["live_room"] != None):
                    vtbData = dict({
                        "name": res["data"]["name"],
                        "uid": res["data"]["mid"],
                        "room": res["data"]["live_room"]["roomid"] ,
                        "face": res["data"]["face"],
                        "top": res["data"]["top_photo"],
                        "reason": res["data"]["sign"],
                        "recommender": "vtbmoe"
                    })
                    if("group_name" in vtb):
                        signed_params = encWbi(
                            params = {
                                "search_type" : "bili_user",
                                "keyword": vtb["group_name"],
                            },
                            img_key = img_key,
                            sub_key = sub_key
                        )
                        query = urllib.parse.urlencode(signed_params)
                        res1 = json.loads(requests.get(url="https://api.bilibili.com/x/web-interface/wbi/search/type?" + query,headers={"User-Agent": "Mozilla/5.0","Accept":"text/html"},cookies=bilibili_req.cookies).text)
                        if (res1["code"] != 0):
                            print("\n组织:" + vtb["group_name"] + "无法搜索，错误代码:" + str(res1["code"]) + "\n")
                            continue
                        add_cata(res1,vtb["group_name"],vtbData)
                    else:
                        add_cata(None,"unclassified",vtbData)
                    data["data"].append(vtbData)
                else:
                    if(res["code"] != 0):
                        print("\nUID:" + account["id"] + "无法获取，错误代码:" + str(res["code"]) + "\n")
                    else:
                        print("\nUID:" + account["id"] + "没有直播间\n")
                print("\r已完成 %.2f %%" %(100*i/len(response["vtbs"])),end='')
except Exception as e:
    print("\n程序出错，错误位置" + i + "/" + str(len(response["vtbs"])-1) +"\n")
    print(e.args)
            
with open(r'../room/recommendation.json', mode='w', encoding='utf-8') as f_obj:
    f_obj.write(json.dumps(data, indent=4, ensure_ascii=False))

with open(r'../room/vtubers_catalog.json', mode='w', encoding='utf-8') as f_obj:
    f_obj.write(json.dumps(cataData, indent=4, ensure_ascii=False))

for group in vtubers:
    with open(r"../room/vtubers/" + vtubers[group]["name"] +".json", mode='w', encoding='utf-8') as f_obj:
        f_obj.write(json.dumps(vtubers[group], indent=4, ensure_ascii=False))

print('Done')
# 寻找是否有 group_name

# 以 id 获取最新 description 和 face



# print(signed_params)
# print(query)