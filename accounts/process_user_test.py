mysql_vehicle = {
    'host': '62.234.57.136',
    'port': 3306,
    'user': 'root',
    'password': 'Qwer4321@',
    'database': 'app_project',
    'charset': 'utf8'
}
mysql_vehicle_1 = {
    'host': '62.234.57.136',
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

create_table_query = """
CREATE TABLE IF NOT EXISTS accounts_core_user (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    app_id VARCHAR(50) NULL,
    mini_id VARCHAR(50) NULL,
    saas_id VARCHAR(50) NULL,
    app_phone VARCHAR(15) NULL,
    saas_phone VARCHAR(15) NULL,
    mini_phone VARCHAR(15) NULL
)
"""
cur1.execute(create_table_query)
print("数据表 core_user 创建成功")

# 提交事务
conn1.commit()
# 执行 SQL 语句
cur.execute(sql)
# 获取所有查询结果
results = cur.fetchall()
import uuid


for _ in results:
    name = _[0]
    id = _[1]
    phone = _[4]
    print(name,id,phone)
    # 生成一个随机的 UUID
    random_uuid = uuid.uuid4()
    print("随机生成的 UUID:", random_uuid)

    insert_query = """
    INSERT INTO accounts_core_user (id, app_id, app_phone)
    VALUES (%s, %s, %s)
    """
    # 执行插入操作
    cur1.execute(insert_query, (random_uuid, id, phone))

    # 提交事务
    conn1.commit()
    
    # sql =f"""
    #  `core_user`
    # SET `label_stop` = '暂停使用'
    # WHERE `id` = {_id};
    # """
    # print(sql)
    # cursor.execute(sql)
    # # Commit the changes to the database
    # conn.commit()