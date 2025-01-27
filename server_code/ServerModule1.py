import sqlite3
import anvil.server
from anvil.files import data_files
from datetime import datetime
import hashlib

def get_db_connection():
    return sqlite3.connect(data_files['bank_transactions.db'])

@anvil.server.callable
def get_other_users(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UID, Name FROM User WHERE UID != ?", (current_user_id,))
        rows = cursor.fetchall()
        return [(row[1], row[0]) for row in rows]
    finally:
        conn.close()

@anvil.server.callable
def unsafe_login(username, password):
    """
    Level 1: Keine Absicherung (unsicher).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = f"SELECT * FROM User WHERE Email = '{username}' AND Password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        if user:
            user_id   = user[0]
            user_name = user[1]
            balance   = user[4]

            transactions_str = get_user_transactions(cursor, user_id)
            return (True, "Unsicherer Login erfolgreich", user_name, balance, transactions_str, user_id)
        else:
            return (False, "Ungültige Anmeldedaten (Level 1)", None, None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

@anvil.server.callable
def safe_login(username, password):
    """
    Level 2: Parametrisierte Queries (sicherer gegen SQL-Injection),
    Passwörter liegen noch unverschlüsselt in der DB.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Parameter-Bindung verhindert einfache SQL-Injection
        cursor.execute("SELECT * FROM User WHERE Email = ? AND Password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            user_id   = user[0]
            user_name = user[1]
            balance   = user[4]

            transactions_str = get_user_transactions(cursor, user_id)
            return (True, "Login erfolgreich (Level 2)", user_name, balance, transactions_str, user_id)
        else:
            return (False, "Ungültige Anmeldedaten (Level 2)", None, None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

@anvil.server.callable
def hashed_login(username, password):
    """
    Level 3: Parametrisierte Queries + Passwort-Hashing.
    Hier werden Passwörter in der DB nur als Hash gespeichert.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Zuerst den Datensatz anhand der Email holen (parametrisierte Query)
        cursor.execute("SELECT * FROM User WHERE Email = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return (False, "Ungültige Anmeldedaten (Level 3)", None, None, None, None)

        # wir nehmen an, dass in 'Password' jetzt der Hash liegt
        user_id         = user[0]
        user_name       = user[1]
        stored_hash     = user[6]
        balance         = user[4]

        # Den SHA256-Hash des eingegebenen Passworts berechnen
        entered_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Vergleichen mit dem gespeicherten Hash
        if entered_hash == stored_hash:
            transactions_str = get_user_transactions(cursor, user_id)
            return (True, "Login erfolgreich (Level 3: Hash)", user_name, balance, transactions_str, user_id)
        else:
            return (False, "Passwort falsch (Level 3)", None, None, None, None)

    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

def get_user_transactions(cursor, user_id):
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
    """, (user_id,))
    rows = cursor.fetchall()

    return "\n".join([
        f"{row[0]} | {row[1]} -> {row[2]} | {row[3]:.2f} EUR"
        for row in rows
    ])

@anvil.server.callable
def transfer_money(sender_id, receiver_id, amount):
    if amount <= 0:
        return (False, "Betrag muss positiv sein!", None, None)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Daten vom Sender holen
        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (sender_id,))
        sender = cursor.fetchone()
        if not sender:
            return (False, "Sender nicht gefunden!", None, None)
        
        sender_balance = sender[1]
        sender_iban    = sender[2]

        # Daten vom Empfänger holen
        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (receiver_id,))
        receiver = cursor.fetchone()
        if not receiver:
            return (False, "Empfänger nicht gefunden!", None, None)
        
        receiver_balance = receiver[1]
        receiver_iban    = receiver[2]

        # Prüfen, ob Sender genügend Guthaben hat
        if sender_balance < amount:
            return (False, f"Unzureichendes Guthaben: {sender_balance:.2f} EUR", None, None)

        # Guthaben aktualisieren
        new_sender_balance = sender_balance - amount
        new_receiver_balance = receiver_balance + amount

        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_sender_balance, sender_id))
        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_receiver_balance, receiver_id))

        # Neue Transaktion anlegen (Tabelle Transactions)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Transactions (Date, SenderIBAN, ReceiverIBAN, Amount)
            VALUES (?, ?, ?, ?)
        """, (now_str, sender_iban, receiver_iban, amount))
        transaction_id = cursor.lastrowid

        # Eintrag in User_Transactions (Sender)
        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Sender')
        """, (sender_id, transaction_id))

        # Eintrag in User_Transactions (Empfänger)
        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Receiver')
        """, (receiver_id, transaction_id))

        conn.commit()

        # Aktualisierte Transaktionen des Senders
        updated_transactions_str = get_user_transactions(cursor, sender_id)

        return (True, "Überweisung erfolgreich", new_sender_balance, updated_transactions_str)

    except Exception as e:
        conn.rollback()
        return (False, str(e), None, None)
    finally:
        conn.close()