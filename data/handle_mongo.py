from pymongo import MongoClient
#mongo数据基座
mongo_source_link = "mongodb://root:Pk775401681@mongoreplicad4c8f2eaf98e0.mongodb.volces.com:3717,mongoreplicad4c8f2eaf98e1.mongodb.volces.com:3717/?authSource=admin&replicaSet=rs-mongo-replica-d4c8f2eaf98e&retryWrites=true"

def connect_mongo(database, collection,mongo_link):
    import pymongo

    client = pymongo.MongoClient(
        mongo_link)
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    db = client[database]
    coll = db[collection]
    return client,db,coll

def mongo_update(collection,query,item):
    collection.update_one(query,{'$set': item, '$currentDate': {'update_date': True}},upsert=True)


def mongo_update_image(conn):
        
    # client, db, conn = connect_mongo('vehicle', 'model_version_repository',mongo_source_link)
    conn.update_many( {'model': { '$regex': '极越' } }, { '$set': { 'model_guide': "chek/model/app_project_image/JiYue.png" } } )
    conn.update_many( {'model': { '$regex': '小米' } }, { '$set': { 'model_guide': "chek/model/app_project_image/XiaoMi.jpg" } } )
    conn.update_many( {'model': { '$regex': '腾势' } }, { '$set': { 'model_guide': "chek/model/app_project_image/DenZaZ9.png" } } )
    conn.update_many( {'model': { '$regex': '理想' } }, { '$set': { 'model_guide': "chek/model/app_project_image/LiXiang.jpg" } } )
    conn.update_many( {'model': { '$regex': '领克' } }, { '$set': { 'model_guide': "chek/model/app_project_image/Linke.png" } } )
    conn.update_many( {'model': { '$regex': '蔚来' } }, { '$set': { 'model_guide': "chek/model/app_project_image/NioEs8.png" } } )
    conn.update_many( {'model': { '$regex': '阿维塔' } }, { '$set': { 'model_guide': "chek/model/app_project_image/avatar11.png" } } )
    conn.update_many( {'model': { '$regex': '秦新能源' } }, { '$set': { 'model_guide': "chek/model/app_project_image/BYDqin.png" } } )
    conn.update_many( {'model': { '$regex': '比亚迪' } }, { '$set': { 'model_guide': "chek/model/app_project_image/BYDqin.png" } } )
    conn.update_many( {'model': { '$regex': '问界' } }, { '$set': { 'model_guide': "chek/model/app_project_image/wenjie.png" } } )
    conn.update_many( {'model': { '$regex': '智界' } }, { '$set': { 'model_guide': "chek/model/app_project_image/wenjie.png" } } )
    conn.update_many( {'model': { '$regex': '享界' } }, { '$set': { 'model_guide': "chek/model/app_project_image/wenjie.png" } } )
    conn.update_many( {'model': { '$regex': '极氪' } }, { '$set': { 'model_guide': "chek/model/app_project_image/zeeker.png" } } )
    conn.update_many( {'model': { '$regex': '极氪' } }, { '$set': { 'model_guide': "chek/model/app_project_image/zeeker.png" } } )
    conn.update_many( {'model': { '$regex': '蓝山' } }, { '$set': { 'model_guide': "chek/model/app_project_image/weipai_lanshan.png" } } )
    conn.update_many( {'model': { '$regex': '智己' } }, { '$set': { 'model_guide': "chek/model/app_project_image/IM.jpg" } } )
    conn.update_many( {'model': { '$regex': '智界' } }, { '$set': { 'model_guide': "chek/model/app_project_image/zhijie.jpg" } } )
    conn.update_many( {'model': { '$regex': 'Model' } }, { '$set': { 'model_guide': "chek/model/app_project_image/Tesla_model3.png" } } )
    conn.update_many( {'model': { '$regex': 'Model X' } }, { '$set': { 'model_guide': "chek/model/app_project_image/Tesla_modelxp.png" } } )
    conn.update_many( {'model': { '$regex': '小鹏' } }, { '$set': { 'model_guide': "chek/model/app_project_image/Xiaopeng.png" } } )
    conn.update_many( {'model': { '$regex': '岚图' } }, { '$set': { 'model_guide': "chek/model/app_project_image/LanTu_Zhuiguang.png" } } )
    conn.update_many( {'model': { '$regex': '昊铂' } }, { '$set': { 'model_guide': "chek/model/app_project_image/HYPer.png" } } )
    conn.update_many( {'model': { '$regex': '通用模型' } }, { '$set': { 'model_guide': "chek/model/app_project_image/XiaoMi.jpg" } } )
    conn.update_many( {'model': { '$regex': '东风日产' } }, { '$set': { 'model_guide': "chek/model/app_project_image/NissanN7.png" } } )
    conn.update_many( {'model': { '$regex': '路特斯' } }, { '$set': { 'model_guide': "chek/model/app_project_image/EMEYA.png" } } )
    # model_config_version

    conn.update_many( {'model': { '$regex': '极越' } }, { '$set': { 'screen_type': "中控屏" } } )
    conn.update_many( {'model': { '$regex': '小米' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '腾势' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '理想' } }, { '$set': { 'screen_type': "中控屏" } } )
    conn.update_many( {'model': { '$regex': '领克' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '蔚来' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '阿维塔' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '问界' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '智界' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '享界' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '极氪' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '秦新能源' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '比亚迪' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '蓝山' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '智己' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '智界' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': 'Model' } }, { '$set': { 'screen_type': "中控屏" } } )
    conn.update_many( {'model': { '$regex': 'Model X' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '小鹏' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '岚图' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '昊铂' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '通用模型' } }, { '$set': { 'screen_type': "仪表屏" } } )
    conn.update_many( {'model': { '$regex': '东风日产' } }, { '$set': { 'screen_type': "通用模型" } } )
    conn.update_many( {'model': { '$regex': '路特斯' } }, { '$set': { 'screen_type': "通用模型" } } )
    #


from bson import ObjectId

if __name__ == '__main__':
    # client, db, coll = connect_mongo('vehicle', 'model_version_repository', mongo_source_link)
    # # result = coll.delete_many({"model": "蔚来ES8"})
    # rest_list = list(coll.find({},{'_id':1,'model_tos_link':1}))
    # for _ in rest_list:
    #     print(_)
    #     model_tos_link = _.get('model_tos_link')
    #     _id = _.get('_id')
    #     if 'chek/model/model/' in model_tos_link:
    #         model_tos_link= model_tos_link.replace('chek/model/model/','chek/model/')
    #         print(model_tos_link)
    #         coll.update_one({'_id':ObjectId(_id)},{'$set':{'model_tos_link':model_tos_link}})


    client, db, coll = connect_mongo('vehicle', 'hot_brand_vehicle', mongo_source_link)
    rest_list = list(coll.find({'model':'极越01'}, {'_id': 1,'model':1}))
    print(rest_list)
    for _ in rest_list:
        _id = _.get('_id')

        coll.update_one({'_id':ObjectId(_id)},{'$set':{'software_config_version':[{'publish_code':'V2.0.0','update_data':'2024年8月30日'}]}})
