import sqlite3
import anvil.server
from anvil.files import data_files
from datetime import datetime
import hashlib

def get_db_connection(level=1):
    """
    Öffnet je nach Level eine andere SQLite-Datenbank:
      - bank_transactions.db für Level 1 und 2
      - bank_transactions_level3.db für Level 3
    """
    if level == 3:
        return sqlite3.connect(data_files['bank_transactions_level3.db'])
    else:
        return sqlite3.connect(data_files['bank_transactions.db'])


@anvil.server.callable
def get_other_users(current_user_id, level):
    """
    Gibt alle anderen Benutzer (Name, UID) zurück,
    damit der eingeloggte User Empfänger für Überweisungen auswählen kann.
    """
    conn = get_db_connection(level)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UID, Name FROM User WHERE UID != ?", (current_user_id,))
        rows = cursor.fetchall()
        # Rückgabe list (Name, UID)
        return [(row[1], row[0]) for row in rows]
    finally:
        conn.close()


@anvil.server.callable
def unsafe_login(username, password, level):
    """
    Level 1: UNSICHERER Login (SQL-Injection möglich).
    Achtung: Hier werden Strings direkt in das SQL-Statement eingesetzt.
    """
    conn = get_db_connection(level)
    cursor = conn.cursor()
    try:
        # SQL-Injection möglich
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
def safe_login(username, password, level):
    """
    Level 2: Parametrisierte Queries (verhindert einfache SQL-Injection),
    ABER Passwörter noch im Klartext in der DB.
    """
    conn = get_db_connection(level)
    cursor = conn.cursor()
    try:
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
def hashed_login(username, password, level):
    """
    Level 3: Parametrisierte Queries + Passwort-Hashing.
    Greift auf die bank_transactions_level3.db zu (siehe get_db_connection(level=3)).
    """
    conn = get_db_connection(level)
    cursor = conn.cursor()
    try:
        # Prüfen, ob es den Benutzer gibt
        cursor.execute("SELECT * FROM User WHERE Email = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return (False, "Ungültige Anmeldedaten (Level 3)", None, None, None, None)

        user_id         = user[0]
        user_name       = user[1]
        stored_hash     = user[6]  # Passwort-Hash in der DB
        balance         = user[4]

        # Eingebenes Passwort hashen
        entered_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

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
    """
    Gibt die Transaktionen für einen bestimmten User als String zurück.
    """
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
def transfer_money(sender_id, receiver_id, amount, level):
    """
    Führt eine Überweisung durch und legt die Transaktion in der jeweiligen
    (je nach Level) Datenbank ab.
    """
    if amount <= 0:
        return (False, "Betrag muss positiv sein!", None, None)

    conn = get_db_connection(level)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (sender_id,))
        sender = cursor.fetchone()
        if not sender:
            return (False, "Sender nicht gefunden!", None, None)
        
        sender_balance = sender[1]
        sender_iban    = sender[2]

        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (receiver_id,))
        receiver = cursor.fetchone()
        if not receiver:
            return (False, "Empfänger nicht gefunden!", None, None)
        
        receiver_balance = receiver[1]
        receiver_iban    = receiver[2]

        if sender_balance < amount:
            return (False, f"Unzureichendes Guthaben: {sender_balance:.2f} EUR", None, None)

        new_sender_balance = sender_balance - amount
        new_receiver_balance = receiver_balance + amount

        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_sender_balance, sender_id))
        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_receiver_balance, receiver_id))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Transactions (Date, SenderIBAN, ReceiverIBAN, Amount)
            VALUES (?, ?, ?, ?)
        """, (now_str, sender_iban, receiver_iban, amount))
        transaction_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Sender')
        """, (sender_id, transaction_id))

        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Receiver')
        """, (receiver_id, transaction_id))

        conn.commit()

        updated_transactions_str = get_user_transactions(cursor, sender_id)

        return (True, "Überweisung erfolgreich", new_sender_balance, updated_transactions_str)

    except Exception as e:
        conn.rollback()
        return (False, str(e), None, None)
    finally:
        conn.close()
