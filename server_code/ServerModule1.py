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
    """
    Gibt zurück: (Bool success, user_row_or_string, transaktionen_list)
       success = True / False
       user_row_or_string = Falls success=True => user-row, sonst Fehlertext
       transaktionen_list = Liste aller relevanten Transaktionen oder []
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM User WHERE Email = ? AND Password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            # IBAN aus dem User-Datensatz
            user_iban = user[5]
            # Transaktionen ermitteln
            cursor.execute("""
                SELECT * FROM Transactions 
                WHERE SenderIBAN = ? OR ReceiverIBAN = ?
            """, (user_iban, user_iban))
            transactions = cursor.fetchall()
            return (True, user, transactions)
        else:
            return (False, "Ungültige Anmeldedaten", [])
    except Exception as e:
        return (False, str(e), [])
    finally:
        conn.close()

@anvil.server.callable
def vulnerable_login(username, password):
    """
    Unsichere Variante (SQL-Injection möglich).
    Rückgabe analog zu safe_login.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Unsicheres Statement
        query = f"SELECT * FROM User WHERE Email = '{username}' AND Password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        if user:
            user_iban = user[5]
            query_trans = f"""
                SELECT * FROM Transactions
                WHERE SenderIBAN = '{user_iban}' OR ReceiverIBAN = '{user_iban}'
            """
            cursor.execute(query_trans)
            transactions = cursor.fetchall()
            return (True, user, transactions)
        else:
            return (False, "Ungültige Anmeldedaten (vulnerable)", [])
    except Exception as e:
        return (False, f"Fehler bei der SQL-Injection: {str(e)}", [])
    finally:
        conn.close()
