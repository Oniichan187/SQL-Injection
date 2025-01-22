import sqlite3
import anvil.server
from anvil.files import data_files
from datetime import datetime

def get_db_connection():
    """
    Gibt eine DB-Verbindung zurück. 'bank_transactions.db' muss als
    Data-File in Anvil hinterlegt sein.
    """
    return sqlite3.connect(data_files['bank_transactions.db'])

@anvil.server.callable
def get_other_users(current_user_id):
    """
    Liefert eine Liste aller anderen User (UID != current_user_id).
    Format für Anvil-Dropdown: [(Name, UID), (Name2, UID2), ...].
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UID, Name FROM User WHERE UID != ?", (current_user_id,))
        rows = cursor.fetchall()
        return [(row[1], row[0]) for row in rows]
    finally:
        conn.close()

@anvil.server.callable
def safe_login(username, password):
    """
    Sicherer Login mit Parameter-Bindung (verhindert SQL-Injection).
    Liefert (success, message, user_name, balance, transactions_str, user_id).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM User WHERE Email = ? AND Password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            user_id   = user[0]
            user_name = user[1]
            balance   = user[4]

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
    *Unsicherer* Login ohne Parameter-Bindung: Anfällig für SQL-Injection!
    Liefert (success, message, user_name, balance, transactions_str, user_id).
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
            return (False, "Ungültige Anmeldedaten", None, None, None, None)
    except Exception as e:
        return (False, str(e), None, None, None, None)
    finally:
        conn.close()

def get_user_transactions(cursor, user_id):
    """
    Liest alle Transaktionen eines Nutzers aus und formatiert sie als String.
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
def transfer_money(sender_id, receiver_id, amount):
    """
    Führt eine Überweisung durch:
      1) Prüft Sender-Guthaben
      2) Zieht Betrag vom Sender ab, addiert beim Empfänger
      3) Legt neuen Eintrag in Transactions an
      4) Je einen Eintrag in User_Transactions (Sender, Receiver)
      5) Gibt aktualisierten Kontostand des Senders + neue Transaktionsliste zurück.

    Liefert (success, msg, new_sender_balance, updated_transactions_str).
    """
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

        # In DB schreiben
        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_sender_balance, sender_id))
        cursor.execute("UPDATE User SET Balance = ? WHERE UID = ?", (new_receiver_balance, receiver_id))

        # Neue Transaktion anlegen (Tabelle Transactions)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Transactions (Date, SenderIBAN, ReceiverIBAN, Amount)
            VALUES (?, ?, ?, ?)
        """, (now_str, sender_iban, receiver_iban, amount))
        transaction_id = cursor.lastrowid

        # User_Transactions-Eintrag für Sender
        cursor.execute("""
            INSERT INTO User_Transactions (UserID, TransactionID, Role)
            VALUES (?, ?, 'Sender')
        """, (sender_id, transaction_id))

        # User_Transactions-Eintrag für Empfänger
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
