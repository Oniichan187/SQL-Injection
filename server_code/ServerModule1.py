import sqlite3
import anvil.server
from anvil.files import data_files
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect(data_files['bank_transactions.db'])
    return conn

@anvil.server.callable
def get_other_users(current_user_id):
    """
    Liefert eine Liste mit allen anderen Nutzern (UID != current_user_id).
    Format: [(Name, UID), (Name2, UID2), ...]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UID, Name FROM User WHERE UID != ?", (current_user_id,))
        rows = cursor.fetchall()
        # Umbauen auf [(Name, UID), ...], denn in Anvil-Dropdown kann .items = [(label, value), ...]
        return [(row[1], row[0]) for row in rows]
    finally:
        conn.close()

@anvil.server.callable
def safe_login(username, password):
    """
    Sicherer Login via Parameter-Bindung (verhindert SQL-Injection).
    Gibt zusätzlich die UID des Nutzers zurück.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM User WHERE Email = ? AND Password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        if user:
            # user = (UID, Name, Email, Age, Balance, IBAN, Password)
            user_id   = user[0]
            user_name = user[1]  
            balance   = user[4]
            
            # Transaktionen abrufen
            transactions_str = get_user_transactions(cursor, user_id)
            
            return (True, "Login erfolgreich", user_name, balance, transactions_str, user_id)
        else:
            return (False, "Ungültige Anmeldedaten", None, None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

@anvil.server.callable
def unsafe_login(username, password):
    """
    *Unsicherer* Login OHNE Parameter-Bindung (verwundbar für SQL-Injection!).
    Hier kann man z.B. als Benutzernamen `anything%' OR '1'='1` testen.
    Gibt zusätzlich die UID des Nutzers zurück.
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
            return (False, "Ungültige Anmeldedaten (unsicherer Login)", None, None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

def get_user_transactions(cursor, user_id):
    """
    Hilfsfunktion, um alle Transaktionen eines Nutzers zu formatieren.
    Gibt den formatierten String zurück.
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
    transactions = cursor.fetchall()

    formatted_transactions = "\n".join([
        f"{date} | {sender} -> {receiver} | {amount:.2f} EUR"
        for date, sender, receiver, amount in transactions
    ])
    return formatted_transactions


@anvil.server.callable
def transfer_money(sender_id, receiver_id, amount):
    """
    Führt eine Überweisung durch:
    - Prüft Guthaben des Senders
    - Zieht Betrag ab / Fügt Betrag beim Empfänger hinzu
    - Legt einen Eintrag in Tabelle Transactions + User_Transactions an
    - Gibt (success, msg, new_balance, updated_transactions_str) zurück
    """
    if amount <= 0:
        return (False, "Betrag muss positiv sein!", None, None)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1) Hol die Daten von Sender und Empfänger
        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (sender_id,))
        sender_user = cursor.fetchone()
        if not sender_user:
            return (False, "Sender nicht gefunden!", None, None)
        
        sender_balance = sender_user[1]
        sender_iban    = sender_user[2]

        cursor.execute("SELECT UID, Balance, IBAN FROM User WHERE UID = ?", (receiver_id,))
        receiver_user = cursor.fetchone()
        if not receiver_user:
            return (False, "Empfänger nicht gefunden!", None, None)
        
        receiver_balance = receiver_user[1]
        receiver_iban    = receiver_user[2]

        # 2) Prüfen, ob Sender genug Guthaben hat
        if sender_balance < amount:
            return (False, f"Unzureichendes Guthaben (verfügbar: {sender_balance:.2f} EUR)!", None, None)
        
        # 3) Kontostände aktualisieren
        new_sender_balance   = sender_balance - amount
        new_receiver_balance = receiver_balance + amount

        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_sender_balance, sender_id))
        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_receiver_balance, receiver_id))

        # 4) Neue Transaktion anlegen
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Transactions (Date, SenderIBAN, ReceiverIBAN, Amount)
            VALUES (?, ?, ?, ?)
        """, (now_str, sender_iban, receiver_iban, amount))
        transaction_id = cursor.lastrowid

        # 5) Einträge in User_Transactions
        #    Sender hat Rolle = 'Sender', Empfänger hat Rolle = 'Receiver'
        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Sender')
        """, (sender_id, transaction_id))

        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Receiver')
        """, (receiver_id, transaction_id))

        conn.commit()

        # 6) Aktuellen Kontostand vom Sender zurückgeben + aktualisierte Transaktionen
        updated_transactions_str = get_user_transactions(cursor, sender_id)
        
        return (True, "Überweisung erfolgreich", new_sender_balance, updated_transactions_str)
    except Exception as e:
        conn.rollback()
        return (False, str(e), None, None)
    finally:
        conn.close()
