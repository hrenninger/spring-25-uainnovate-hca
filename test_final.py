import re
from collections import defaultdict

def parse_segment(msg, segment_type):
    for line in msg.splitlines():
        if line.startswith(segment_type + "|"):
            return line.strip().split("|")
    return []

def extract_account_numbers(msg):
    pid = parse_segment(msg, "PID")
    if not pid:
        return None, None
    
    # Extract PID-18 (account number)
    account_number = pid[18] if len(pid) > 18 else ""
    
    # Extract PID-21 (mother's identifier)
    mother_id = pid[21] if len(pid) > 21 else ""
    
    return account_number, mother_id

def load_message_pairs(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Split based on "Original HL7 Message:" markers
    raw_pairs = re.split(r"Original HL7 Message:\s*", content)[1:]
    message_pairs = []

    for pair in raw_pairs:
        split_msgs = re.split(r"De-Identified HL7 Message:\s*", pair.strip())
        if len(split_msgs) == 2:
            original_msg, deid_msg = split_msgs
            message_pairs.append((original_msg.strip(), deid_msg.strip()))

    return message_pairs

def check_consistent_mapping(filepath):
    """
    Check if the same PID-18 and PID-21 values are consistently mapped 
    to the same deidentified values across all messages.
    """
    message_pairs = load_message_pairs(filepath)
    
    # Track how original values map to deidentified values
    pid18_mapping = {}
    pid21_mapping = {}
    
    # List for inconsistencies
    inconsistencies = []
    
    # Build the mappings
    for i, (orig_msg, deid_msg) in enumerate(message_pairs):
        orig_acc, orig_mother = extract_account_numbers(orig_msg)
        deid_acc, deid_mother = extract_account_numbers(deid_msg)
        
        msg_id = f"Message #{i+1}"
        
        # Check PID-18 consistency
        if orig_acc and deid_acc:
            if orig_acc in pid18_mapping:
                if pid18_mapping[orig_acc] != deid_acc:
                    inconsistencies.append(
                        f"❌ PID-18 Inconsistency: Original '{orig_acc}' mapped to '{pid18_mapping[orig_acc]}' "
                        f"and '{deid_acc}' in {msg_id}"
                    )
            else:
                pid18_mapping[orig_acc] = deid_acc
        
        # Check PID-21 consistency
        if orig_mother and deid_mother:
            if orig_mother in pid21_mapping:
                if pid21_mapping[orig_mother] != deid_mother:
                    inconsistencies.append(
                        f"❌ PID-21 Inconsistency: Original '{orig_mother}' mapped to '{pid21_mapping[orig_mother]}' "
                        f"and '{deid_mother}' in {msg_id}"
                    )
            else:
                pid21_mapping[orig_mother] = deid_mother
    
    # Check cross-field relationships
    # Find cases where a value appears in both PID-18 and PID-21 fields
    common_values = set(pid18_mapping.keys()) & set(pid21_mapping.keys())
    for value in common_values:
        if pid18_mapping[value] != pid21_mapping[value]:
            inconsistencies.append(
                f"❌ Cross-field inconsistency: Value '{value}' mapped to '{pid18_mapping[value]}' as PID-18 "
                f"but to '{pid21_mapping[value]}' as PID-21"
            )
    
    # Print results
    print("\n🔍 CHECKING CONSISTENCY OF PID-18/PID-21 MAPPING")
    if inconsistencies:
        for item in inconsistencies:
            print(item)
    else:
        print("✅ All PID-18 and PID-21 values are consistently mapped across messages")
    
    # Print the complete mapping for inspection
    print("\n📋 PID-18 MAPPING (ACCOUNT NUMBERS)")
    for orig, deid in pid18_mapping.items():
        print(f"{orig} → {deid}")
    
    print("\n📋 PID-21 MAPPING (MOTHER IDs)")
    for orig, deid in pid21_mapping.items():
        print(f"{orig} → {deid}")
    
    # Special check for mother-baby links
    print("\n👩‍👧 MOTHER-BABY LINK CHECK (CROSS-FIELD VALUES)")
    for value in common_values:
        print(f"Original: {value}, As PID-18: {pid18_mapping[value]}, As PID-21: {pid21_mapping[value]}")
        
        if pid18_mapping[value] == pid21_mapping[value]:
            print(f"✅ Consistent mapping for {value}")
        else:
            print(f"❌ Inconsistent mapping for {value}")

if __name__ == "__main__":
    check_consistent_mapping("messages_deidentified.txt")  # Replace with your actual file path