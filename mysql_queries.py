def create_encodings_table(mysql):
    query = 'DROP Table IF EXISTS encodings ;' \
            'CREATE TABLE encodings(id bigint(20) NOT NULL AUTO_INCREMENT,' \
            'userID bigint(20) NOT NULL UNIQUE,'
    for i in range(128):
        query += F'encoding{i} decimal(20,19) NOT NULL,'
    query += 'PRIMARY KEY (id), FOREIGN KEY (userID) REFERENCES abonne(id))'

    cursor = mysql.connection.cursor()
    cursor.execute(query)
    return query


def get_user_id(username, mysql):
    if username:
        cursor = mysql.connection.cursor()
        query = F"SELECT id from abonne where username='{username}'"
        cursor.execute(query)
        data = cursor.fetchone()
        return data[0] if data else None
    else:
        return None


def insert_encodings(encoding, username, mysql, user_id=None):
    try:
        user_id = user_id or get_user_id(username, mysql)
        if user_id:
            print(F'[INFO] inserting encoding for {username} with id: {user_id}')
            query = F"REPLACE INTO encodings values(null,{user_id}"
            for value in encoding:
                query += F',{value}'
            query += ')'
            connection = mysql.connection
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            return None
    except Exception as e:
        print(e)
        return e


def get_user_encoding(mysql, username=None, user_id=None):
    if not username and not user_id:
        raise Exception("You must specify either username or user_id")

    user_id = user_id or get_user_id(username, mysql)
    if user_id:
        print(F'[INFO] get_user_encoding for {username} with id: {user_id}')
        query = F"select * from encodings where userID = {user_id}"
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        data = cursor.fetchone()
        encodings = []
        for e in data[2:]:
            encodings.append(float(e))
        return encodings
    raise Exception("didn't found this user")


def calculate_distance_from_mysql(encodings, mysql, distance=0.55):
    try:
        print(F'[INFO] calculating distance in mysql')
        encodings_string = " sqrt("
        for i, encoding in enumerate(encodings):
            encodings_string += F"power({encoding} - encoding{i}, 2)+"
        encodings_string += "0)"

        query = F"select r.userID, r.distance from ( SELECT userID,{encodings_string} as distance from encodings )" \
                F" as r where r.distance < {distance} order by r.distance asc;"
        cursor = mysql.connection.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        return data if len(data) else None
    except Exception as e:
        print(e)
        return e
