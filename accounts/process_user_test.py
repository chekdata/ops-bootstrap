mysql_vehicle = {
    # 'host': '62.234.57.136',
          'host': '101.126.6.116',
    'port': 3306,
    'user': 'root',
    'password': 'Qwer4321@',
    'database': 'app_project',
    'charset': 'utf8'
}
mysql_vehicle_1 = {
    # 'host': '62.234.57.136',
          'host': '101.126.6.116',
    'port': 3306,
    'user': 'root',
    'password': 'Qwer4321@',
    'database': 'core_user',
    'charset': 'utf8'
}

mysql_vehicle_2 = {
    'host': '62.234.57.136',
        #   'host': '101.126.6.116',
    'port': 3306,
    'user': 'root',
    'password': 'Qwer4321@',
    'database': 'core_user',
    'charset': 'utf8'
}
def connect_mysql(args):
    import pymysql
    db = pymysql.connect(**args)
    cur = db.cursor()
    return db,cur

conn,cur = connect_mysql(mysql_vehicle)
conn1,cur1 = connect_mysql(mysql_vehicle_1)
conn2,cur2 = connect_mysql(mysql_vehicle_2)
def update_data(conn,cursor,_id):
    sql =f"""
    UPDATE `game_info`
    SET `label_stop` = '暂停使用'
    WHERE `id` = {_id};
    """
    print(sql)
    cursor.execute(sql)
    # Commit the changes to the database
    conn.commit()
# sql = """
# CREATE TABLE SMS_verify_login (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     phone VARCHAR(15) NULL,
#     code INT NULL,
#     created_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
# );
# """
# cur.execute(sql)
# conn.commit()
sql = "SELECT * FROM accounts_user"

# create_table_query = """
# CREATE TABLE IF NOT EXISTS accounts_core_user (
#     id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
#     app_id VARCHAR(50) NULL,
#     mini_id VARCHAR(50) NULL,
#     saas_id VARCHAR(50) NULL,
#     app_phone VARCHAR(15) NULL,
#     saas_phone VARCHAR(15) NULL,
#     mini_phone VARCHAR(15) NULL
# )
# """
# cur1.execute(create_table_query)
# print("数据表 core_user 创建成功")

# 提交事务
conn1.commit()
# 执行 SQL 语句
cur.execute(sql)
# 获取所有查询结果
results = cur.fetchall()
import uuid

# for _ in results:
#     uuid_obj = _[1]  # 直接获取 UUID 对象
#     print(type(uuid_obj))  # 输出: <class 'uuid.UUID'>
#     print(uuid_obj)        # 无连字符: 550e8400e29b41d4a7164466554400
#     ori_uuid_obj = uuid_obj
#     print(str(uuid_obj))   # 无连字符
#     # print(uuid_obj.hex)    # 无连字符的十六进制表示
#     # print(uuid_obj.urn)    # 带连字符的标准格式: uuid:550e8400-e29b-41d4-a716-446655440000
#     uuid_obj = uuid.UUID(uuid_obj)
#     print(uuid_obj.urn)

#     update_sql = "UPDATE accounts_core_user SET app_id = %s WHERE app_id = %s"
#     cur1.execute(update_sql, (uuid_obj, ori_uuid_obj))
#     conn1.commit()
import pandas as pd
res_liist = []
for _ in results:
    name = _[0]
    id = _[1]
    phone = _[4]
    # print(name,str(id),phone)
    # 生成一个随机的 UUID
    random_uuid = uuid.uuid4()
    # print("随机生成的 UUID:", random_uuid)
    id = uuid.UUID(id)
    res_liist.append({'id':id,'phone':phone,'name':name})
    print(phone,id,name)
pd.DataFrame(res_liist).to_csv('test.csv')
    # 检查 app_phone 是否已存在
    # check_query = "SELECT id, app_id, app_phone FROM accounts_core_user WHERE app_id = %s LIMIT 1"
    # cur1.execute(check_query, (str(id),))
    # result1 = cur1.fetchone()
    # cur2.execute(check_query, (str(id),))
    # result2 = cur2.fetchone()


    # # 如果不存在，则插入新记录
    # if result1 and not result2:
    #     if phone:
    #         existing_id = result1[0]       # id 字段（第一列）
    #         existing_app_id = result1[1]   # app_id 字段（第二列）
    #         existing_app_phone = result1[2]  
    #         print(existing_id,existing_app_id,existing_app_phone)
    #         # print(name,id,phone)
    #         uuid_obj = uuid.UUID(existing_id)
    #         insert_query = """
    #         INSERT INTO accounts_core_user (id, app_id, app_phone)
    #         VALUES (%s, %s, %s)
    #         """
    #         # # 执行插入操作
    #         cur2.execute(insert_query, (uuid_obj, existing_app_id, existing_app_phone))

    #         # # 提交事务
    #         conn2.commit()
    
