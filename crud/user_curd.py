# crud/user_crud.py

from db.connection import get_db_connection

def create_user(name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id;", (name, email))
        user_id = cur.fetchone()[0]
        conn.commit()
        return f"User created with ID: {user_id}"
    except Exception as e:
        conn.rollback()
        return f"[CREATE ERROR] {e}"
    finally:
        cur.close()
        conn.close()

def read_user(user_id=None, name=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if user_id:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
        elif name:
            cur.execute("SELECT * FROM users WHERE name ILIKE %s;", (f"%{name}%",))
        else:
            cur.execute("SELECT * FROM users;")

        rows = cur.fetchall()
        if not rows:
            return "No users found."
        return "\n".join([f"id: {r[0]}, name: {r[1]}, email: {r[2]}" for r in rows])
    except Exception as e:
        return f"[READ ERROR] {e}"
    finally:
        cur.close()
        conn.close()

def update_user(user_id, name=None, email=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if name:
            cur.execute("UPDATE users SET name = %s WHERE id = %s;", (name, user_id))
        if email:
            cur.execute("UPDATE users SET email = %s WHERE id = %s;", (email, user_id))
        conn.commit()
        return "User updated successfully."
    except Exception as e:
        conn.rollback()
        return f"[UPDATE ERROR] {e}"
    finally:
        cur.close()
        conn.close()

def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id;", (user_id,))
        deleted = cur.fetchone()
        conn.commit()

        if deleted:
            return f"User with ID {user_id} deleted successfully."
        else:
            return f"No user found with ID {user_id}."
    except Exception as e:
        conn.rollback()
        return str(e)
    finally:
        cur.close()
        conn.close()

