from ._anvil_designer import StartTemplate
from anvil import *
import anvil.server

class Start(StartTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

        # Hier speichern wir die UserID des eingeloggten Nutzers
        self.current_user_id = None

        # Hier speichern wir die Liste mit allen Transaktionen (Strings) für die Suche
        self.all_transactions = []

        # Das FlowPanel für Transaktionen (Dropdown/Betrag/Button) soll erst unsichtbar sein
        self.flow_panel_transaktion.visible = False
        
        self.reset_to_start()

    def reset_to_start(self):
        self.label_2.text = "Bank"  # Standardtext für label_2
        self.handle_login_click.text = "Login"  # Button zurück auf Login
        self.text_box_1.visible = False
        self.text_box_1.text = ""
        self.Input_User.placeholder = "Benutzername"
        self.Input_Password.placeholder = "Passwort"
        self.Lable_User.text = "Benutzername:"
        self.Input_User.text = ""
        self.Input_Password.text = ""

        # Eingabefelder sichtbar machen
        self.Label_Password.visible = True
        self.Input_Password.visible = True

        # FlowPanel für Transaktionen unsichtbar machen
        self.flow_panel_transaktion.visible = False

        # Zur Sicherheit auch den Dropdown und Betrag zurücksetzen
        self.drop_down_1.items = []
        self.text_box_betrag.text = ""

        # Keine aktive UserID
        self.current_user_id = None

        # Leeren wir die gespeicherten Transaktionen
        self.all_transactions = []

    def button_login_click_click(self, **event_args):
        if self.handle_login_click.text == "Login":
            username = self.Input_User.text
            password = self.Input_Password.text

            # Unterscheide, ob "Checkbox_SQL" (unsicherer Login) gesetzt ist
            if hasattr(self, "Checkbox_SQL") and self.Checkbox_SQL.checked:
                # UNSICHERER Login mit SQL-Injection
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'unsafe_login', username, password
                )
            else:
                # SICHERER Login
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'safe_login', username, password
                )

            if success:
                # Login erfolgreich
                self.current_user_id = user_id  # Speichere unsere UserID
                self.label_2.text = f"{user_name} - Kontostand: {balance:.2f} EUR"

                # Transaktionen in self.all_transactions zwischenspeichern
                self.all_transactions = transactions_str.split("\n") if transactions_str else []
                
                # Alle Transaktionen anzeigen
                self.text_box_1.text = transactions_str
                self.text_box_1.visible = True
                
                # Suche/Placeholder
                self.Lable_User.text = "Suche:"
                self.Input_User.placeholder = "Tippe Suchbegriff und drücke Enter"
                self.Input_User.text = ""
                
                # Eingabefelder für Passwort ausblenden
                self.Label_Password.visible = False
                self.Input_Password.visible = False
                
                # Button auf Logout ändern
                self.handle_login_click.text = "Logout"

                # FlowPanel für Transaktionen einblenden
                self.flow_panel_transaktion.visible = True

                # Dropdown mit anderen Nutzern füllen (Empfänger)
                users_list = anvil.server.call('get_other_users', user_id)
                # Erwartetes Format: [(EmpfaengerName, EmpfaengerID), (EmpfaengerName, EmpfaengerID), ...]
                self.drop_down_1.items = users_list

            else:
                alert(message, title="Fehler")
        else:
            # Logout durchführen
            self.reset_to_start()
    

    def check_box_1_change(self, **event_args):
        """Nur ein Platzhalter-Event, falls du mit Checkbox etwas tun willst."""
        pass

    def Input_User_pressed_enter(self, **event_args):
        """
        Wird aufgerufen, wenn der Nutzer in 'Input_User' Enter drückt.
        Nach dem Login interpretieren wir 'Input_User' als Suchfeld.
        """
        if self.Lable_User.text == "Suche:":
            search_text = self.Input_User.text.lower().strip()
            
            # Filtern der Transaktionszeilen
            filtered_transactions = [
                line for line in self.all_transactions
                if search_text in line.lower()
            ]
            
            # Gefilterte Zeilen anzeigen
            self.text_box_1.text = "\n".join(filtered_transactions)
            
            # Suchfeld leeren
            self.Input_User.text = ""

    def Input_Password_pressed_enter(self, **event_args):
        """Wird aufgerufen, wenn der Nutzer in 'Input_Password' Enter drückt."""
        pass

    def button_ueberweisen_click(self, **event_args):
        """
        Diese Methode führt den Transfer aus, wenn auf den Button geklickt wird.
        """
        if not self.current_user_id:
            alert("Bitte erst einloggen!")
            return

        # Ausgewählter Empfänger
        selected = self.drop_down_1.selected_value
        if not selected:
            alert("Bitte Empfänger auswählen!")
            return
        
        # selected = EmpfaengerID (weil wir .items = [(Name, ID), ...] gesetzt haben)
        receiver_id = selected

        # Betrag einlesen
        betrag_str = self.text_box_betrag.text.strip()
        if not betrag_str:
            alert("Bitte einen Betrag eingeben!")
            return

        # Versuch, Betrag in float zu konvertieren
        try:
            betrag = float(betrag_str)
        except ValueError:
            alert("Ungültiger Betrag. Bitte eine Zahl eingeben.")
            return

        # Serveraufruf: transfer_money
        success, msg, new_balance, updated_transactions_str = anvil.server.call(
            'transfer_money', 
            self.current_user_id, 
            receiver_id, 
            betrag
        )
        if success:
            alert("Überweisung erfolgreich!")
            # Kontostand und Transaktionen updaten
            self.label_2.text = self.label_2.text.split(" - ")[0] + f" - Kontostand: {new_balance:.2f} EUR"
            
            # Neue Transaktionen speichern & anzeigen
            self.all_transactions = updated_transactions_str.split("\n") if updated_transactions_str else []
            self.text_box_1.text = updated_transactions_str

            # Eingabefelder zurücksetzen
            self.text_box_betrag.text = ""
        else:
            alert(msg, title="Fehler")
