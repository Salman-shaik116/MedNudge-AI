import pymysql

# Database connection
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='Luke_2021',
    database='signup_db'
)

try:
    with connection.cursor() as cursor:
        # Read and execute SQL
        with open('create_missing_table.sql', 'r') as f:
            sql = f.read()
        cursor.execute(sql)
        connection.commit()
        print("Table 'website_medicalreport' created successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    connection.close()
