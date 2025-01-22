from ._anvil_designer import StartTemplate
from anvil import *
import anvil.server

class Start(StartTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
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

    def button_login_click_click(self, **event_args):
        if self.handle_login_click.text == "Login":
            username = self.Input_User.text
            password = self.Input_Password.text

            # Unterscheide, ob "Checkbox_SQL" (unsicherer Login) gesetzt ist
            if self.Checkbox_SQL.checked:
                # UNSICHERER Login mit SQL-Injection
                success, message, user_name, balance, transactions = anvil.server.call(
                    'unsafe_login', username, password
                )
            else:
                # SICHERER Login
                success, message, user_name, balance, transactions = anvil.server.call(
                    'safe_login', username, password
                )

            if success:
                # Login erfolgreich, UI anpassen
                # Name + Kontostand im gleichen Label anzeigen:
                self.label_2.text = f"{user_name} - Kontostand: {balance:.2f} EUR"
                
                # TextBox mit Transaktionen anzeigen
                self.text_box_1.text = transactions
                self.text_box_1.visible = True
                
                # Suche/Placeholder just for demonstration
                self.Lable_User.text = "Suche:"
                self.Input_User.placeholder = ""
                self.Input_User.text = ""
                
                # Eingabefelder für Passwort ausblenden
                self.Label_Password.visible = False
                self.Input_Password.visible = False
                
                # Button auf Logout ändern
                self.handle_login_click.text = "Logout"
            else:
                alert(message, title="Fehler")
        else:
            # Logout durchführen
            self.reset_to_start()
    

    def check_box_1_change(self, **event_args):
        pass

    def Input_User_pressed_enter(self, **event_args):
        """This method is called when the user presses Enter in this text box"""
        pass

    def Input_Password_pressed_enter(self, **event_args):
        """This method is called when the user presses Enter in this text box"""
        pass
