#!/usr/bin/env python3
import re
import argparse
from faker import Faker

fake = Faker()

def is_physician_field(field_value: str) -> bool:
    """
    Determine if a field likely represents a physician.
    Here, we assume that a physician field has at least four caret-separated parts
    and the last part (typically the role code) is one of 'DO', 'MD', or 'DR'.
    """
    if not field_value.strip():
        return False
    parts = field_value.split("^")
    return len(parts) >= 4 and parts[-1].upper() in {"DO", "MD", "DR"}

def map_physician_field(value: str, mapping: dict) -> str:
    """
    If the value is recognized as a physician field, return its consistent fake mapping.
    Otherwise, return the original value.
    """
    if not is_physician_field(value):
        return value

    if value in mapping:
        return mapping[value]
    
    # Parse the original field to preserve the role code.
    parts = value.split("^")
    role = parts[-1]  # Preserve original role (e.g., DO, MD, DR)
    
    # Generate a fake physician name using Faker.
    fake_first = fake.first_name()
    fake_last = fake.last_name()
    fake_initial = fake_first[0]
    # Generate a fake identifier (a five-character alphanumeric string)
    fake_id = fake.bothify(text="?????")
    
    # Construct the new HL7-formatted physician field.
    new_value = f"{fake_id}^{fake_last}^{fake_first}^{fake_initial}^^^{role}"
    mapping[value] = new_value
    return new_value

def process_hl7_message(message: str, mapping: dict) -> str:
    """
    Process a single HL7 message by iterating over its segments.
    For any PV1 segment, replace physician fields with their mapped fake values.
    """
    segments = message.splitlines()
    new_segments = []
    for segment in segments:
        if segment.startswith("PV1"):
            fields = segment.split("|")
            new_fields = [map_physician_field(field, mapping) for field in fields]
            new_segments.append("|".join(new_fields))
        else:
            new_segments.append(segment)
    return "\n".join(new_segments)

def extract_physician_fields(msg: str, mapping: dict) -> list:
    """
    Extracts physician fields from any PV1 segments in the HL7 message.
    For each field that is recognized as a physician field (using is_physician_field),
    map it to a fake value using map_physician_field, and return a list of these values.
    """
    fake_physicians = []
    for line in msg.splitlines():
        if line.startswith("PV1"):
            fields = line.split("|")
            for field in fields:
                if is_physician_field(field):
                    fake_field = map_physician_field(field, mapping)
                    fake_physicians.append(fake_field)
    return fake_physicians


def main():
    parser = argparse.ArgumentParser(
        description="Map HL7 PV1 physician fields to consistent fake physicians"
    )
    parser.add_argument("hl7_file", help="Path to HL7 file")
    parser.add_argument("--output", help="Output file name", default="messages_physician_deidentified.hl7")
    args = parser.parse_args()
    
    with open(args.hl7_file, "r") as infile:
        content = infile.read()
    
    # Split messages using the standard MSH segment as delimiter.
    messages = re.split(r'(?=^MSH\|)', content, flags=re.MULTILINE)
    messages = [msg for msg in messages if msg.strip()]
    
    physician_mapping = {}  # This dictionary ensures consistency across messages.
    processed_messages = []
    
    for msg in messages:
        new_msg = process_hl7_message(msg, physician_mapping)
        processed_messages.append(new_msg)
    
    output_content = "\n".join(processed_messages)
    with open(args.output, "w") as outfile:
        outfile.write(output_content)
    
    print(f"Processing complete. Output written to '{args.output}'.")

if __name__ == "__main__":
    main()
