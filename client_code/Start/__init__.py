from ._anvil_designer import StartTemplate
from anvil import *
import anvil.server

class Start(StartTemplate):
    def __init__(self, **properties):
        # Standard-Initialisierung
        self.init_components(**properties)
        
        # Dropdown_SQL mit den 3 Level füllen
        self.Dropdown_SQL.items = [
            "Level 1",  # Unsicher
            "Level 2",  # Parameter
            "Level 3",  # Parameter + Hash
        ]
        self.Dropdown_SQL.selected_value = "Level 1"  # Standard: Unsicher

        # Speichert die UserID des aktuell eingeloggten Nutzers
        self.current_user_id = None
        
        # (Optional) Placeholder für den Betrag
        self.text_box_betrag.placeholder = "z.B. 100.50"

        # FlowPanel soll anfangs unsichtbar sein
        self.flow_panel_transaktion.visible = False

        self.reset_to_start()

    def reset_to_start(self):
        """Setzt die UI in den Ausgangszustand (z.B. nach Logout)."""
        self.label_2.text = "Diamond Financial Holdings"
        self.handle_login_click.text = "Login"
        self.text_box_1.visible = False
        self.text_box_1.text = ""
        self.Input_User.placeholder = "Benutzername"
        self.Input_Password.placeholder = "Passwort"
        self.Lable_User.text = "Benutzername:"
        self.Input_User.text = ""
        self.Input_Password.text = ""
        self.label_5.visible = False

        self.Label_Password.visible = True
        self.Input_Password.visible = True

        # FlowPanel für Transaktionen unsichtbar
        self.flow_panel_transaktion.visible = False

        # Dropdown leeren, Betrag zurücksetzen
        self.drop_down_1.items = []
        self.text_box_betrag.text = ""

        self.current_user_id = None

        # (Neu) Für die Suche
        self.all_transactions_str = ""  # enthält später das Original-Transaktions-Log

    def button_login_click_click(self, **event_args):
        """Wird aufgerufen, wenn der Login-Button geklickt wird."""
        if self.handle_login_click.text == "Login":
            username = self.Input_User.text
            password = self.Input_Password.text

            # Ausgewähltes Level im Dropdown
            selected_level = self.Dropdown_SQL.selected_value

            if selected_level == "Level 1":
                # Level 1: UNSICHERER Login
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'unsafe_login', username, password
                )

            elif selected_level == "Level 2":
                # Level 2: Parametergebunden
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'safe_login', username, password
                )

            else:  # Level 3
                # Level 3: Parametrisierte Queries + Passwort als Hash
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'hashed_login', username, password
                )

            if success:
                # Login erfolgreich
                self.current_user_id = user_id
                self.label_2.text = f"{user_name} - Kontostand: {balance:.2f} EUR"

                # (WICHTIG) Original-Transaktionen speichern
                self.all_transactions_str = transactions_str

                # In der TextBox anzeigen
                self.text_box_1.text = self.all_transactions_str
                self.text_box_1.visible = True

                # Suche
                self.Lable_User.text = "Suche:"
                self.Input_User.placeholder = "Tippe Suchbegriff und drücke Enter"
                self.Input_User.text = ""

                # Verstecke Passwort-Felder
                self.Label_Password.visible = False
                self.Input_Password.visible = False
                self.label_5.visible = True

                # Button-Text auf Logout
                self.handle_login_click.text = "Logout"

                # FlowPanel für Transaktion anzeigen
                self.flow_panel_transaktion.visible = True

                # Empfänger-Liste in Dropdown laden
                users_list = anvil.server.call('get_other_users', user_id)
                self.drop_down_1.items = users_list

            else:
                alert(message, title="Fehler")

        else:
            # Logout
            self.reset_to_start()

    def Input_User_pressed_enter(self, **event_args):
        """Suche in den angezeigten Transaktionen."""
        if self.Lable_User.text == "Suche:":
            search_text = self.Input_User.text.lower().strip()

            if not search_text:
                # Wenn keine Sucheingabe, zeige alle Transaktionen wieder
                self.text_box_1.text = self.all_transactions_str
            else:
                # Zeilen aus dem ORIGINAL-String filtern
                lines = self.all_transactions_str.split("\n")
                filtered = [line for line in lines if search_text in line.lower()]
                self.text_box_1.text = "\n".join(filtered)

            self.Input_User.text = ""

    def Input_Password_pressed_enter(self, **event_args):
        pass

    def make_transaktion_click(self, **event_args):
        """
        Button, um eine Buchung (Überweisung) auszulösen.
        Aktualisiert Kontostände & Transaktionsliste.
        """
        if not self.current_user_id:
            alert("Bitte erst einloggen!")
            return

        # Empfänger-ID aus dem Dropdown
        receiver_id = self.drop_down_1.selected_value
        if not receiver_id:
            alert("Bitte einen Empfänger auswählen!")
            return

        # Betrag aus der Textbox
        betrag_str = self.text_box_betrag.text.strip()
        if not betrag_str:
            alert("Bitte einen Betrag eingeben!")
            return

        # Betrag in float umwandeln
        try:
            betrag = float(betrag_str)
        except ValueError:
            alert("Ungültiger Betrag. Bitte eine Zahl eingeben (z.B. 100.50).")
            return

        success, msg, new_balance, updated_transactions = anvil.server.call(
            'transfer_money',
            self.current_user_id,
            receiver_id,
            betrag
        )

        if success:
            alert("Überweisung erfolgreich!")
            
            # Kontostand aktualisieren
            name_part = self.label_2.text.split(" - ")[0]
            self.label_2.text = f"{name_part} - Kontostand: {new_balance:.2f} EUR"

            # (WICHTIG) Auch den Original-String updaten, damit die Suche weiter korrekt funktioniert
            self.all_transactions_str = updated_transactions
            self.text_box_1.text = updated_transactions

            # Betrag-Textbox leeren
            self.text_box_betrag.text = ""
        else:
            alert(msg, title="Fehler")
