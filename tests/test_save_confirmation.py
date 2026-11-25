import unittest
from unittest.mock import Mock, patch
from md_to_pdf.gui import confirm_changes

class ConfirmationTests(unittest.TestCase):
    def test_clean_does_not_prompt(self):
        save=Mock()
        with patch("md_to_pdf.gui.ask_save_changes") as ask:
            self.assertTrue(confirm_changes(None,False,save))
            ask.assert_not_called()
            save.assert_not_called()

    def test_three_choices_and_failed_save(self):
        for answer,success,expected in (("save",True,True),("save",False,False),
                                         ("discard",False,True),("cancel",True,False)):
            with self.subTest(answer=answer,success=success):
                save=Mock(return_value=success)
                with patch("md_to_pdf.gui.ask_save_changes",return_value=answer):
                    self.assertEqual(confirm_changes(None,True,save),expected)
                    self.assertEqual(save.call_count,int(answer=="save"))
