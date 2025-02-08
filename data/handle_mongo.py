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
