def redact_text(text):
    """Replace every character in text with an asterisk."""
    return "*" * len(text) if text else text

def process_pid(segment):
    """
    Process a PID segment by redacting PHI in the following fields (if they exist):
      - PID-3 (index 3)
      - PID-4 (index 4)
      - PID-5 (index 5)
      - PID-7 (index 7)
      - PID-9 (index 9)
      - PID-11 (index 11)
      - PID-12 (index 12)
      - PID-13 (index 13)
      - PID-14 (index 14)
      - PID-18 (index 18)
      - PID-19 (index 19)
    Note: The HL7 segment is split on "|" and the segment name "PID" is at index 0.
    """
    fields = segment.split("|")
    # Define the 1-indexed fields to redact (converted to 0-indexed)
    indices_to_redact = [3, 4, 5, 7, 9, 11, 12, 13, 14, 18, 19]
    for idx in indices_to_redact:
        if idx < len(fields) and fields[idx]:
            fields[idx] = redact_text(fields[idx])
    return "|".join(fields)

def process_segment(segment):
    """
    Process a segment of the HL7 message. If the segment is a PID segment,
    apply redaction; otherwise, return the segment unchanged.
    """
    if segment.startswith("PID"):
        return process_pid(segment)
    else:
        return segment

def parse_hl7_messages(file_path):
    """
    Read the HL7 file and split it into individual messages.
    Assumes each message starts with 'MSH'. If a message (except the first)
    lost the 'MSH' during splitting, it is added back.
    """
    with open(file_path, "r") as f:
        content = f.read().strip()
    
    # Split messages assuming each new message starts with "\nMSH"
    messages = content.split("\nMSH")
    # Add back the "MSH" for messages that lost it in the split (all except the first)
    messages = [messages[0]] + ["MSH" + m for m in messages[1:]]
    return messages

def redact_message(message):
    """
    Process one HL7 message line by line.
    """
    lines = message.splitlines()
    redacted_lines = []
    for line in lines:
        redacted_line = process_segment(line)
        redacted_lines.append(redacted_line)
    return "\n".join(redacted_lines)

def main():
    input_file = "source_hl7_messages_v2.hl7"  # Replace with the path to your HL7 file
    output_file = "messages_redacted.txt"
    
    messages = parse_hl7_messages(input_file)
    redacted_messages = [redact_message(msg) for msg in messages]
    
    # Write out each redacted message, separating them with a blank line
    with open(output_file, "w") as f:
        for msg in redacted_messages:
            f.write(msg.strip() + "\n\n")
    
    print(f"Redacted messages have been written to {output_file}")

if __name__ == "__main__":
    main()
