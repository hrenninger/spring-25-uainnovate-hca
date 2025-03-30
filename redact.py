import re
import json

def load_sensitive_tokens(deid_filepath):
    """
    Loads sensitive tokens from a de-identified file.
    The file is expected to contain blocks separated by lines containing dashes.
    Each block should have a "De-Identified Data:" section containing a JSON object
    with a "sensitive_info" list.
    Returns a set of sensitive tokens.
    """
    sensitive_tokens = set()
    with open(deid_filepath, 'r') as f:
        block = ""
        for line in f:
            if line.strip() == "--------------------------------------------------------------------------------":
                # Process the block if it contains de-identified data.
                if "De-Identified Data:" in block:
                    json_start = block.find("{")
                    json_end = block.rfind("}")
                    if json_start != -1 and json_end != -1:
                        json_str = block[json_start:json_end+1]
                        try:
                            data = json.loads(json_str)
                            tokens = data.get("sensitive_info", [])
                            for token in tokens:
                                sensitive_tokens.add(token)
                        except Exception as e:
                            # If JSON parsing fails, skip this block.
                            pass
                block = ""
            else:
                block += line
        # Process any remaining block not followed by a separator.
        if block and "De-Identified Data:" in block:
            json_start = block.find("{")
            json_end = block.rfind("}")
            if json_start != -1 and json_end != -1:
                json_str = block[json_start:json_end+1]
                try:
                    data = json.loads(json_str)
                    tokens = data.get("sensitive_info", [])
                    for token in tokens:
                        sensitive_tokens.add(token)
                except Exception as e:
                    pass
    return sensitive_tokens

def redact_text(text, sensitive_tokens):
    """
    For a given text string, replace every occurrence (case-insensitive) of each sensitive token
    with a string of asterisks (*) of the same length.
    """
    for token in sensitive_tokens:
        # Use word boundaries to match only complete tokens.
        pattern = r'\b' + re.escape(token) + r'\b'
        text = re.sub(pattern, lambda m: '*' * len(m.group(0)), text, flags=re.IGNORECASE)
    return text

def redact_pid_line(line, sensitive_indices):
    """
    Redacts the PHI in a PID segment by replacing the designated fields entirely with asterisks.
    The line is split on the '|' delimiter and fields are redacted if they exist.
    Field numbering is 1-based (after the segment name at index 0).
    """
    fields = line.rstrip("\n").split("|")
    for idx in sensitive_indices:
        if idx < len(fields) and fields[idx]:
            # Replace each character in the field with an asterisk.
            fields[idx] = '*' * len(fields[idx])
    return "|".join(fields)

def redact_obx_line(line, sensitive_tokens):
    """
    Redacts any PHI found in OBX segments within the free-text notes field (OBX-5).
    """
    fields = line.rstrip("\n").split("|")
    # HL7 OBX: OBX-1 is index 1, OBX-2 index 2, ... OBX-5 is index 5 (since index 0 is "OBX").
    if len(fields) > 5:
        fields[5] = redact_text(fields[5], sensitive_tokens)
    return "|".join(fields)

def main():
    # Load the sensitive tokens from the de-identified file.
    sensitive_tokens = load_sensitive_tokens("messages_with_deid.txt")
    # Sort tokens by length descending (optional, to avoid substring conflicts)
    sensitive_tokens = sorted(sensitive_tokens, key=len, reverse=True)

    # Define the list of PID field indices to redact.
    sensitive_pid_indices = [3, 4, 5, 7, 9, 11, 12, 13, 14, 18, 19]

    # Open the output file for writing.
    with open("obx_messages_redacted.txt", "w") as outfile:
        current_message_lines = []  # List to hold lines for the current message

        # Process the source HL7 messages.
        with open("source_hl7_messages_v2.hl7", "r") as infile:
            for line in infile:
                # Remove any trailing newline characters.
                line = line.rstrip("\n")

                # Check if this line indicates the start of a new message.
                if line.startswith("MSH"):
                    # If we already have a message collected, write it out.
                    if current_message_lines:
                        for redacted_line in current_message_lines:
                            outfile.write(redacted_line + "\n")
                        # Optionally, flush to ensure the data is written immediately.
                        outfile.flush()
                        # Reset the current message.
                        current_message_lines = []

                # Process the line based on its segment type.
                # if line.startswith("PID"):
                #     current_message_lines.append(redact_pid_line(line, sensitive_pid_indices))
                if line.startswith("OBX"):
                    current_message_lines.append(redact_obx_line(line, sensitive_tokens))
                else:
                    current_message_lines.append(line)

            # After processing all lines, write out any remaining message.
            if current_message_lines:
                for redacted_line in current_message_lines:
                    outfile.write(redacted_line + "\n")
                outfile.flush()

if __name__ == "__main__":
    main()
