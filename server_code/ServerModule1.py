import sqlite3
import anvil.server
from anvil.files import data_files

def get_db_connection():
    conn = sqlite3.connect(data_files['bank_transactions.db'])
    return conn

@anvil.server.callable
def safe_login(username, password):
    """
    Sicherer Login via Parameter-Bindung (verhindert SQL-Injection).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Überprüfen, ob Benutzer existiert
        cursor.execute(
            "SELECT * FROM User WHERE Email = ? AND Password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        if user:
            # user = (UID, Name, Email, Age, Balance, IBAN, Password)
            user_name = user[1]  
            balance = user[4]  
            
            # Transaktionen abrufen
            cursor.execute("""
                SELECT t.Date,
                       s.Name AS SenderName,
                       r.Name AS ReceiverName,
                       t.Amount
                FROM Transactions t
                JOIN User s ON t.SenderIBAN = s.IBAN
                JOIN User r ON t.ReceiverIBAN = r.IBAN
                JOIN User_Transactions ut ON t.TransactionID = ut.TransactionID
                WHERE ut.UserID = ?
            """, (user[0],))  # user[0] = UID
            transactions = cursor.fetchall()
            
            # Transaktionen formatieren
            formatted_transactions = "\n".join([
                f"{date} | {sender} -> {receiver} | {amount:.2f} EUR"
                for date, sender, receiver, amount in transactions
            ])
            
            return (True, "Login erfolgreich", user_name, balance, formatted_transactions)
        else:
            return (False, "Ungültige Anmeldedaten", None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None)
    finally:
        conn.close()


@anvil.server.callable
def unsafe_login(username, password):
    """
    *Unsicherer* Login OHNE Parameter-Bindung (verwundbar für SQL-Injection!).
    Hier kann man z.B. als Benutzernamen `anything%' OR '1'='1` testen.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # UNSICHERES Query per string.format oder f-String
        query = f"SELECT * FROM User WHERE Email = '{username}' AND Password = '{password}'"
        cursor.execute(query)
        
        user = cursor.fetchone()
        if user:
            # user = (UID, Name, Email, Age, Balance, IBAN, Password)
            user_name = user[1]
            balance   = user[4]

            # Transaktionen abrufen (wie oben)
            cursor.execute(f"""
                SELECT t.Date,
                       s.Name AS SenderName,
                       r.Name AS ReceiverName,
                       t.Amount
                FROM Transactions t
                JOIN User s ON t.SenderIBAN = s.IBAN
                JOIN User r ON t.ReceiverIBAN = r.IBAN
                JOIN User_Transactions ut ON t.TransactionID = ut.TransactionID
                WHERE ut.UserID = {user[0]}
            """)
            transactions = cursor.fetchall()
            
            # Transaktionen formatieren
            formatted_transactions = "\n".join([
                f"{date} | {sender} -> {receiver} | {amount:.2f} EUR"
                for date, sender, receiver, amount in transactions
            ])

            return (True, "Unsicherer Login erfolgreich", user_name, balance, formatted_transactions)
        else:
            return (False, "Ungültige Anmeldedaten (unsicherer Login)", None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None)
    finally:
        conn.close()
