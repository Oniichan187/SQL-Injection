import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.files
from anvil.files import data_files
import anvil.server
import sqlite3

def get_db_connection():
    conn = sqlite3.connect(data_files['bank_transactions.db']) 
    return conn

@anvil.server.callable
def safe_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM User WHERE Email = ? AND Password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            return (True, "Benutzer gefunden.")
        else:
            return (False, "Ungültige Anmeldedaten.")
    except Exception as e:
        return (False, str(e))
    finally:
        conn.close()

@anvil.server.callable
def vulnerable_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = f"SELECT * FROM User WHERE Email = '{username}' AND Password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        if user:
            return "Anmeldung erfolgreich (vulnerable)."
        else:
            return "Anmeldung fehlgeschlagen (vulnerable)."
    except Exception as e:
        return f"Fehler bei der SQL-Injection: {str(e)}"
    finally:
        conn.close()
