import re
from datetime import datetime

def parse_hl7_date(date_str):
    """
    Parse an HL7 date/time string.
    HL7 dates are often in the format YYYYMMDDHHMMSS (or a shorter version).
    This function attempts to parse the first 14 characters if available.
    """
    try:
        # Use the first 14 characters if available
        if len(date_str) >= 14:
            return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
        # If only date is provided (YYYYMMDD)
        elif len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        # In case of error, return a very early date so this message sorts first
        return datetime.min
    # Default fallback
    return datetime.min

# Replace 'your_hl7_file.hl7' with the path to your actual HL7 file
with open('source_hl7_messages_v2.hl7', 'r') as infile:
    content = infile.read()

# Split the file into messages.
# We assume that each message starts with "MSH|" at the beginning of a line.
messages = re.split(r'(?=^MSH\|)', content, flags=re.MULTILINE)
messages = [msg for msg in messages if msg.strip()]  # Remove any empty messages

# Extract the Date/Time from MSH-7 for each message and store with the message.
messages_with_dt = []
for msg in messages:
    lines = msg.splitlines()
    if lines:
        # The first line is the MSH segment.
        msh_fields = lines[0].split('|')
        if len(msh_fields) >= 7:
            date_str = msh_fields[6]
            dt = parse_hl7_date(date_str)
        else:
            dt = datetime.min  # fallback if MSH-7 is missing
        messages_with_dt.append((dt, msg))

# Sort messages by the extracted datetime (oldest to newest)
sorted_messages = sorted(messages_with_dt, key=lambda x: x[0])

# Write the sorted messages to a new file.
with open('messages_sorted.txt', 'w') as outfile:
    for dt, msg in sorted_messages:
        outfile.write(msg + "\n")  # Ensure messages are separated by a newline

print("Sorting complete. Sorted messages written to 'messages_sorted.txt'.")
