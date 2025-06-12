# from handle_database.utils.common_process import connect_mysql,connect_postgressql,connect_mongo,random_uuid
# from handle_database.utils.config import *
# import json
# from handle_database.utils.model import *
# from data_clean import *
mongo_source_link = "mongodb://root:Pk775401681@mongoreplicad4c8f2eaf98e0.mongodb.volces.com:3717,mongoreplicad4c8f2eaf98e1.mongodb.volces.com:3717/?authSource=admin&replicaSet=rs-mongo-replica-d4c8f2eaf98e&retryWrites=true"
def connect_mysql(args):
    import pymysql
    db = pymysql.connect(**args)
    cur = db.cursor()
    return db,cur

def connect_mongo(database, collection,mongo_link):
    import pymongo

    client = pymongo.MongoClient(
        mongo_link)
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    db = client[database]
    coll = db[collection]
    return coll

mysql_app_project = {
    'host': '62.234.57.136',
    'port': 3306,
    'user': 'root',
    'password': 'Qwer4321@',
    'database': 'app_project',
    'charset': 'utf8'
}
conn = connect_mongo('vehicle', 'hot_brand_vehicle', mongo_source_link)

# data = list(conn.find({},{'_id':1,'model':1,'hardware_config_version':1,'software_config_version':1,'brand':1}))
# conn_update = connect_mongo('vehicle', 'model_config_app', mongo_source_link)

# def create_database():

#     conn,cur = connect_mysql(mysql_app_project)
#     cur.execute('DROP TABLE IF EXISTS model_config')
#     sql = """
#          CREATE TABLE IF NOT EXISTS  model_config(
#              id VARCHAR(255) PRIMARY KEY,
#              brand VARCHAR(255),
#              model VARCHAR(255),
#              hardware_config_version VARCHAR(255),
#              software_config_version VARCHAR(2000)
#          );
#          """
#     cur.execute(sql)
#     conn.commit()

# def update_data(query,item,conn):

#     conn.update_one(query,
#                                  {'$set': item
#                                   },
#                                  upsert=True)
# create_database()
# conn_mysql,cur_mysql = connect_mysql(mysql_app_project)
# # delete_mysql = "DELETE FROM model_config;"
# # delete_mysql = 'TRUNCATE TABLE model_config;'
# # drop_mysql = 'DROP TABLE model_config;'
# # cur_mysql.execute(drop_mysql)
# # conn_mysql.commit()
# model_dict = {}
# for _ in data:
#     item = {}
#     # update_data(_, _, conn_update)

#     brand = _.get('brand')
#     model = _.get('model')
#     hardware_config_version = _.get('hardware_config_version')
#     software_config_version = _.get('software_config_version')
#     list_software_config_version = []
#     if software_config_version:
#         for i in software_config_version:
#             if '年' not in i.get('publish_code') and '月' not in i.get('publish_code')  and '版本' not in i.get('publish_code') :
#                 list_software_config_version.append(i.get('publish_code'))
#     if model:
#         item['model'] = model
#     if hardware_config_version:
#         item['hardware_config_version'] = hardware_config_version
#     if list_software_config_version:
#         item['software_config_version'] = '|'.join(list_software_config_version)

#     if  item.get('software_config_version') and hardware_config_version:
#         sql = f"""
#         INSERT INTO model_config (id,model, hardware_config_version, software_config_version,brand)
#     VALUES ('{str(_.get('_id'))}','{model}', '{hardware_config_version}','{item.get('software_config_version')}','{brand}')
#         """
#     elif hardware_config_version:
#         sql = f"""
#                INSERT INTO model_config (id,model, hardware_config_version,brand)
#            VALUES ('{str(_.get('_id'))}','{model}', '{hardware_config_version}','{brand}')
#                """
#     else:
#         sql = f"""
#                 INSERT INTO model_config (id,model,brand)
#             VALUES ('{str(_.get('_id'))}','{model}','{brand}')
#                 """
#     print(sql)

#     cur_mysql.execute(sql)
#     conn_mysql.commit()


    # if model:
    #     if model not in model_dict.keys():
    #         model_dict[model] = []
    #     if hardware_config_version:
    #         if hardware_config_version not in model_dict[model]:
    #             item = {}
    #             item[hardware_config_version] = []
    #             if software_config_version:
    #                 for i in software_config_version:
    #                     item[hardware_config_version].append(i.get('publish_code'))

                # model_dict[model].append(item)



# model_list = []
# for k,v in model_dict.items():
#     item = {}
#     item['model'] = k
#     item['config'] = v
#     # update_data(item, item, conn_update)
#     model_list.append(item)
# for _ in model_list:
#     print(_)
from datetime import datetime
# 添加创建时间字段
update_result = conn.update_many(
    {"created_date": {"$exists": False}},
    {"$set": {"created_date": datetime.now()}}
)

print(f"成功更新 {update_result.modified_count} 个文档的 created_date 字段")

# 添加更新时间字段
update_result = conn.update_many(
    {"updated_date": {"$exists": False}},
    {"$set": {"updated_date": datetime.now()}}
)

print(f"成功更新 {update_result.modified_count} 个文档的 updated_date 字段")

# 关闭连接
# client.close()