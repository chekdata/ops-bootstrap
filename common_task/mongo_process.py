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
    return coll,db,client

def process_update(item):
    coll,db,client= connect_mongo('app_project', 'app_analysis_data', mongo_source_link)

    coll.update_one(item,
                                     {'$set': item
                                      },
                                     upsert=True)
