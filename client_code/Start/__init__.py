from ._anvil_designer import StartTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

class Start(StartTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

        # Textbox zu Beginn unsichtbar machen
        self.text_box_1.visible = False
        self.text_box_1.text = ""  # Textbox-Inhalt leeren

    def button_login_click_click(self, **event_args):  # Umbenannte Methode
        username = self.Input_User.text
        password = self.Input_Password.text
        sql_injection_allowed = self.Checkbox_SQL.checked

        if not sql_injection_allowed:
            success, message = anvil.server.call('safe_login', username, password)
            if success:
                self.text_box_1.text = "Anmeldung erfolgreich!"
                self.text_box_1.foreground = "green"
            else:
                self.text_box_1.text = f"Anmeldung fehlgeschlagen: {message}"
                self.text_box_1.foreground = "red"
        else:
            injection_result = anvil.server.call('vulnerable_login', username, password)
            self.text_box_1.text = injection_result

        self.text_box_1.visible = True  # Textbox sichtbar machen

    def Input_User_pressed_enter(self, **event_args):
        """Methode für Enter-Taste in Username-Textbox"""
        pass

    def Input_Password_pressed_enter(self, **event_args):
        """Methode für Enter-Taste in Passwort-Textbox"""
        pass

    def text_box_1_pressed_enter(self, **event_args):
        """Methode für Enter-Taste in Textbox 1"""
        pass

    def check_box_1_change(self, **event_args):
        """Methode für Checkbox-Änderungen"""
        pass
