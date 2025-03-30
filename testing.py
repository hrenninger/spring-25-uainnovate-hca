import os
import subprocess
import json

def test_consistent_identity():
    # Create a temporary HL7 file with five identical messages for the same patient.
    # Each message includes the same facility (FAC001) and MRN (123456) so the unique key is the same.
    hl7_message = (
        "MSH|^~\\&|SendingApp|FAC001|ReceivingApp|FAC001|20230101120000||ADT^A01|MSGID1|P|2.3\n"
        "PID|1|123456|123456||Smith^Joe||19800101|M|||123 Fake St^^Faketown^CA^90210||555-555-1234|||\n"
    )
    # Create five copies of the same message
    hl7_content = hl7_message * 5
    
    temp_filename = "temp_test.hl7"
    with open(temp_filename, "w") as f:
        f.write(hl7_content)
    
    # Run the de-identification processing script.
    # Adjust "deid_processor.py" if your main script has a different name.
    subprocess.run(["python", "encrypt.py", temp_filename])
    
    # Read the output file (assuming your script writes to "messages_with_deid.txt")
    output_filename = "messages_with_deid.txt"
    try:
        with open(output_filename, "r") as f:
            output = f.read()
    except Exception as e:
        print("Error reading output file:", e)
        return
    
    # Parse the output to extract de-identified JSON blocks.
    # Our output file is formatted with sections separated by a line of dashes.
    segments = output.split("-" * 80)
    identities = []
    for segment in segments:
        if "De-Identified Data:" in segment:
            lines = segment.strip().splitlines()
            # Find the JSON portion after the "De-Identified Data:" header.
            json_lines = []
            found = False
            for line in lines:
                if found:
                    json_lines.append(line)
                if "De-Identified Data:" in line:
                    found = True
            json_str = "\n".join(json_lines).strip()
            if json_str:
                try:
                    data = json.loads(json_str)
                    identities.append(data)
                except Exception as e:
                    print("JSON parsing error:", e)
    
    if not identities:
        print("Test failed: No de-identified data found.")
        return
    
    # Check that all identities have the same fake values.
    first_identity = identities[0]
    consistent = True
    for idx, ident in enumerate(identities[1:], start=2):
        if (ident.get("new_name") != first_identity.get("new_name") or
            ident.get("new_mrn") != first_identity.get("new_mrn") or
            ident.get("new_dob") != first_identity.get("new_dob") or
            ident.get("new_ssn") != first_identity.get("new_ssn")):
            print(f"Inconsistency found in message {idx}:")
            print("First identity:", first_identity)
            print("Current identity:", ident)
            consistent = False
            break

    if consistent:
        print("Test passed: De-identified data is consistent across all messages.")
    else:
        print("Test failed: De-identified data is not consistent.")

    # Clean up temporary files
    os.remove(temp_filename)
    os.remove(output_filename)

if __name__ == "__main__":
    test_consistent_identity()
