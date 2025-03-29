def parse_hl7_messages(file_path):
    """Read the HL7 file and split into individual messages.
    Assumes each message starts with 'MSH'."""
    with open(file_path, "r") as f:
        content = f.read().strip()
    
    # Split on occurrences of newline followed by 'MSH'
    # (if the file is created by concatenating HL7 messages one after the other)
    messages = content.split("\nMSH")
    
    # The first message might already start with MSH.
    # For all messages after the first, add back the missing 'MSH'
    messages = [messages[0]] + ["MSH" + m for m in messages[1:]]
    return messages

def extract_datetime(message):
    """Extract the MSH-7 field (Date/Time) from the message.
    This function assumes that MSH fields are '|' separated
    and returns the first 12 characters of MSH-7 (YYYYMMDDHHMM)."""
    lines = message.splitlines()
    for line in lines:
        if line.startswith("MSH"):
            fields = line.split("|")
            if len(fields) > 6:
                # MSH-7 is the 7th field (index 6)
                dt_field = fields[6].strip()
                # Use first 12 characters (ignoring timezone offsets, if any)
                return dt_field[:12]
    return ""

def sort_messages_by_datetime(messages):
    """Sort messages using the extracted datetime."""
    return sorted(messages, key=lambda msg: extract_datetime(msg))

def main():
    input_file = "source_hl7_messages_v2.hl7"  # replace with your HL7 file name
    output_file = "messages_sorted.txt"
    
    # Parse and sort the messages
    messages = parse_hl7_messages(input_file)
    sorted_messages = sort_messages_by_datetime(messages)
    
    # Write the sorted messages to the output file
    with open(output_file, "w") as f:
        for msg in sorted_messages:
            # Write each message separated by a blank line for clarity
            f.write(msg.strip() + "\n\n")
    
    print(f"Sorted messages have been written to {output_file}")

if __name__ == "__main__":
    main()
