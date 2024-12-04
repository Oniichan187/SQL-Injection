from ._anvil_designer import StartTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

class Start(StartTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.text_box_1.visible = False

    def button_login_click(self, **event_args):
        username = self.input_username.text
        password = self.input_password.text
        sql_injection_allowed = self.checkbox_sql_injection.checked

        if not sql_injection_allowed:
            success, message = anvil.server.call('safe_login', username, password)
            if success:
                alert("Anmeldung erfolgreich!")
            else:
                alert(f"Anmeldung fehlgeschlagen: {message}")
        else:
            injection_result = anvil.server.call('vulnerable_login', username, password)
            self.text_box_1.text = injection_result
            self.text_box_1.visible = True
