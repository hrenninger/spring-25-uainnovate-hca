import re
import pandas as pd

def is_field_empty(value):
    """
    Returns True if the value is empty after stripping whitespace or 
    if it only contains caret (^) characters.
    """
    cleaned = value.strip()
    return not cleaned or cleaned.replace("^", "") == ""

def parse_hl7_message_all_fields(message):
    """
    Parse an HL7 message into a dictionary containing every segment's fields.
    If a segment appears more than once, subsequent occurrences are given a suffix.
    For example, the first OBX segment fields will be labeled "OBX-1", "OBX-2", etc.
    and the second occurrence will be "OBX#2-1", "OBX#2-2", etc.
    """
    row = {}
    segment_counts = {}
    # Split the message into lines (segments)
    lines = message.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Split segment by HL7 field delimiter
        fields = line.split("|")
        seg = fields[0]
        # Update count for this segment type
        count = segment_counts.get(seg, 0) + 1
        segment_counts[seg] = count
        
        # For each field after the segment identifier, assign a key
        for i in range(1, len(fields)):
            key = f"{seg}-{i}" if count == 1 else f"{seg}#{count}-{i}"
            row[key] = fields[i]
    return row

def parse_hl7_file_all_fields(file_path):
    """
    Reads an HL7 file and returns a list of tuples, each containing:
      (original_message, parsed_dictionary)
    Uses a regular expression to split messages when a line starts with "MSH".
    """
    with open(file_path, "r") as f:
        content = f.read().strip()
    
    # Split messages using regex on lines that start with "MSH"
    messages = re.split(r'(?=^MSH)', content, flags=re.MULTILINE)
    messages = [msg.strip() for msg in messages if msg.strip()]
    
    records = []
    total_messages = len(messages)
    for msg in messages:
        record = parse_hl7_message_all_fields(msg)
        if record:
            records.append((msg, record))
    return records, total_messages

if __name__ == "__main__":
    input_file = "source_hl7_messages_v2.hl7"
    output_file = "filtered_hl7_messages.hl7"
    
    # Parse the HL7 file into individual messages.
    records, total_messages = parse_hl7_file_all_fields(input_file)
    
    # Fields to check.
    fields_of_interest = ["PID-3", "PID-4", "PID-5", "PID-11", "PID-12", 
                          "PID-7", "PID-13", "PID-14", "PID-6", "PID-9",
                          "PID-18", "PID-19", "PID-20", "PID-23", "PID-29", "PID-30"]
    
    output_lines = []
    count_filtered = 0
    field_counts = {field: 0 for field in fields_of_interest}
    
    # Iterate over each message and its parsed fields.
    for original_message, record in records:
        # Find which of the fields of interest are non-empty (considering '^' as empty).
        present_fields = [field for field in fields_of_interest 
                          if field in record and not is_field_empty(record[field])]
        if present_fields:
            count_filtered += 1
            # Update counts for each field present in this message.
            for field in present_fields:
                field_counts[field] += 1
            header = "Fields present: " + ", ".join(present_fields)
            output_lines.append(header)
            output_lines.append(original_message)
            output_lines.append("--------")  # Delimiter line between messages
    
    # Write out only the filtered messages to the output file.
    with open(output_file, "w") as f:
        f.write("\n".join(output_lines))
    
    # Print summary to terminal.
    print(f"Filtered {count_filtered} messages with fields {fields_of_interest} written to {output_file}")
    print("Counts for each field:")
    for field in fields_of_interest:
        print(f"  {field}: {field_counts[field]}")
    print(f"Total messages processed: {total_messages}")
