import unittest
import re
from physician import process_hl7_message

class TestPhysicianMappingConsistency(unittest.TestCase):
    def test_consistent_mapping_across_messages(self):
        # Define a physician field that should be mapped.
        original_physician = "DOUJO^Douglas^John^A^^^DO"
        
        # Construct two HL7 messages that include the same physician in the PV1 segment.
        message1 = (
            "MSH|^~\\&|HOSP1|FAC1|...\n"
            "EVN|A04|202503190223\n"
            "PID|1||H000004935|H4907|palma^aydee^^^^^L\n"
            "PV1|1|E|H.ER^^|EL|||"+ original_physician +"|OtherField\n"
        )
        message2 = (
            "MSH|^~\\&|HOSP2|FAC2|...\n"
            "EVN|A04|202503190223\n"
            "PID|1||H000004936|H4908|smith^john^^^^^L\n"
            "PV1|1|E|H.ER^^|EL|||"+ original_physician +"|OtherField\n"
        )
        
        # Create a shared mapping dictionary.
        physician_mapping = {}
        
        # Process both messages.
        processed_msg1 = process_hl7_message(message1, physician_mapping)
        processed_msg2 = process_hl7_message(message2, physician_mapping)
        
        # Check that the original physician value is in the mapping dictionary.
        self.assertIn(original_physician, physician_mapping)
        fake_value = physician_mapping[original_physician]
        
        # Both processed messages should now contain the same fake physician value.
        self.assertIn(fake_value, processed_msg1)
        self.assertIn(fake_value, processed_msg2)
        
        # Optionally, ensure that the original value does not appear in the output.
        self.assertNotIn(original_physician, processed_msg1)
        self.assertNotIn(original_physician, processed_msg2)

if __name__ == '__main__':
    unittest.main()
