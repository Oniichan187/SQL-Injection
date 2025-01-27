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
            "Level 2",  # Parametrisiert (aber Klartext-PW)
            "Level 3",  # Parametrisiert + gehashte Passwörter
        ]
        self.Dropdown_SQL.selected_value = "Level 1"  # Standard

        self.current_user_id = None
        
        self.text_box_betrag.placeholder = "z.B. 100.50"

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

        self.flow_panel_transaktion.visible = False

        self.drop_down_1.items = []
        self.text_box_betrag.text = ""

        self.current_user_id = None

        self.all_transactions_str = ""

    def button_login_click_click(self, **event_args):
        """Wird aufgerufen, wenn der Login-Button geklickt wird."""
        if self.handle_login_click.text == "Login":
            username = self.Input_User.text
            password = self.Input_Password.text

            # Ausgewähltes Level im Dropdown
            selected_level = self.Dropdown_SQL.selected_value
            level_param = None
            if selected_level == "Level 1":
                level_param = 1
                # UNSICHERER Login
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'unsafe_login', username, password, level_param
                )
            elif selected_level == "Level 2":
                level_param = 2
                # Parametergebundener Login (Klartext-PW)
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'safe_login', username, password, level_param
                )
            else:  # Level 3
                level_param = 3
                # Parametrisiert + Passwort-Hash
                success, message, user_name, balance, transactions_str, user_id = anvil.server.call(
                    'hashed_login', username, password, level_param
                )

            if success:
                self.current_user_id = user_id
                self.label_2.text = f"{user_name} - Kontostand: {balance:.2f} EUR"

                self.all_transactions_str = transactions_str

                self.text_box_1.text = self.all_transactions_str
                self.text_box_1.visible = True

                self.Lable_User.text = "Suche:"
                self.Input_User.placeholder = "Tippe Suchbegriff und drücke Enter"
                self.Input_User.text = ""

                self.Label_Password.visible = False
                self.Input_Password.visible = False
                self.label_5.visible = True

                self.handle_login_click.text = "Logout"

                self.flow_panel_transaktion.visible = True

                users_list = anvil.server.call('get_other_users', user_id, level_param)
                self.drop_down_1.items = users_list

              #info label level 3
                if selected_level == "Level 3":
                  self.label_level3_info.visible = True
                  self.label_level3_info.text = (
                    "Sie sind jetzt in Level 3 eingeloggt.\n"
                    "Die Datenbank ist zwar strukturgleich (Tabellen User, Transactions, User_Transactions), "
                    "aber die Passwörter werden gehasht gespeichert.\n"
                    "Bitte beachten Sie, dass sich die Transaktionen und Kontostände "
                    "von Level 1 und 2 unterscheiden können."
                  )
                else:
                    self.label_level3_info.visible = False
                    self.label_level3_info.text = ""
                  
            else:
                alert(message, title="Fehler")

        else:
            # Logout
            self.reset_to_start()

    def Input_User_pressed_enter(self, **event_args):
        """Sucht in den angezeigten Transaktionen."""
        if self.Lable_User.text == "Suche:":
            search_text = self.Input_User.text.lower().strip()

            if not search_text:
                self.text_box_1.text = self.all_transactions_str
            else:
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

        selected_level = self.Dropdown_SQL.selected_value
        if selected_level == "Level 1":
            level_param = 1
        elif selected_level == "Level 2":
            level_param = 2
        else:
            level_param = 3

        receiver_id = self.drop_down_1.selected_value
        if not receiver_id:
            alert("Bitte einen Empfänger auswählen!")
            return

        betrag_str = self.text_box_betrag.text.strip()
        if not betrag_str:
            alert("Bitte einen Betrag eingeben!")
            return

        try:
            betrag = float(betrag_str)
        except ValueError:
            alert("Ungültiger Betrag. Bitte eine Zahl eingeben (z.B. 100.50).")
            return

        success, msg, new_balance, updated_transactions = anvil.server.call(
            'transfer_money',
            self.current_user_id,
            receiver_id,
            betrag,
            level_param
        )

        if success:
            alert("Überweisung erfolgreich!")
            
            name_part = self.label_2.text.split(" - ")[0]
            self.label_2.text = f"{name_part} - Kontostand: {new_balance:.2f} EUR"

            self.all_transactions_str = updated_transactions
            self.text_box_1.text = updated_transactions

            self.text_box_betrag.text = ""
        else:
            alert(msg, title="Fehler")
