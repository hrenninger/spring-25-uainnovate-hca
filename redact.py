import re
from datetime import datetime

def redact_field(field, replacement="****"):
    """Return a redacted value for a field."""
    return replacement

def redact_pid_segment(line):
    """
    Redact sensitive PHI in the PID segment.
    Expected redactions (using HL7 field positions):
      - PID-3 (MRN)       -> index 3
      - PID-5 (Patient Name) -> index 5
      - PID-6 (Mother's Maiden Name) -> index 6
      - PID-7 (Birthdate)  -> index 7 (with special handling for age)
      - PID-11 (Address)   -> index 11
      - PID-13 (Home Phone) -> index 13
      - PID-14 (Business Phone) -> index 14
      - PID-18 (Account Number) -> index 18
      - PID-19 (SSN)       -> index 19
    """
    fields = line.split("|")
    
    # Redact MRN (PID-3)
    if len(fields) > 3:
        fields[3] = redact_field(fields[3])
    # Redact Patient Name (PID-5)
    if len(fields) > 5:
        fields[5] = redact_field(fields[5])
    # Redact Mother's Maiden Name (PID-6)
    if len(fields) > 6:
        fields[6] = redact_field(fields[6])
    # Process Birthdate (PID-7)
    if len(fields) > 7:
        birthdate = fields[7]
        new_birthdate = "****"  # default redaction
        try:
            # Assume birthdate is in YYYYMMDD (or longer) format.
            if len(birthdate) >= 8:
                dt = datetime.strptime(birthdate[:8], "%Y%m%d")
                today = datetime.today()
                age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
                # If the patient is 90 or older, aggregate into a single category.
                if age >= 90:
                    new_birthdate = "90+"
                else:
                    new_birthdate = "****"
        except Exception:
            new_birthdate = "****"
        fields[7] = new_birthdate
    # Redact Address (PID-11)
    if len(fields) > 11:
        fields[11] = redact_field(fields[11])
    # Redact Home Phone (PID-13)
    if len(fields) > 13:
        fields[13] = redact_field(fields[13])
    # Redact Business Phone (PID-14)
    if len(fields) > 14:
        fields[14] = redact_field(fields[14])
    # Redact Account Number (PID-18)
    if len(fields) > 18:
        fields[18] = redact_field(fields[18])
    # Redact SSN (PID-19)
    if len(fields) > 19:
        fields[19] = redact_field(fields[19])
    
    return "|".join(fields)

def generic_redact(text):
    """
    Apply regex-based redaction to catch email addresses, phone numbers,
    and SSNs that might appear outside of structured fields.
    """
    # Redact email addresses
    text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', "****", text)
    # Redact phone numbers (simple US phone pattern)
    text = re.sub(r'\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b', "****", text)
    # Redact SSNs in formats like 123-45-6789
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', "****", text)
    return text

def redact_message(message):
    """
    Process an HL7 message line by line. If the line is a PID segment,
    perform field-based redaction; otherwise, apply generic regex redaction.
    """
    redacted_lines = []
    for line in message.splitlines():
        if line.startswith("PID|"):
            redacted_line = redact_pid_segment(line)
        else:
            redacted_line = generic_redact(line)
        redacted_lines.append(redacted_line)
    return "\n".join(redacted_lines)

# Replace 'your_hl7_file.hl7' with the path to your HL7 file
with open("source_hl7_messages_v2.hl7", "r") as infile:
    content = infile.read()

# Split the file into individual messages.
# We assume that each message starts with "MSH|" at the beginning of a line.
messages = re.split(r'(?=^MSH\|)', content, flags=re.MULTILINE)
redacted_messages = [redact_message(msg) for msg in messages if msg.strip()]

with open("messages_redacted.txt", "w") as outfile:
    for msg in redacted_messages:
        outfile.write(msg + "\n")

print("Redaction complete. Redacted messages written to 'messages_redacted.txt'.")
