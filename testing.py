import os
import json
import random

def parse_output_file(filename):
    """
    Parse the output file "messages_with_deid.txt" produced by your de-identification script.
    Returns a dictionary mapping unique_key -> list of de-identified data dictionaries.
    """
    with open(filename, "r") as f:
        content = f.read()
    
    # Each message block is separated by a line of 80 dashes.
    blocks = content.split("-" * 80)
    results = {}
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        unique_key = None
        deid_json = None
        capture = False
        json_lines = []
        for line in lines:
            if line.startswith("Unique Key:"):
                unique_key = line.split("Unique Key:")[1].strip()
            if "De-Identified Data:" in line:
                capture = True
                continue  # Skip header line
            if capture:
                json_lines.append(line)
        if unique_key and json_lines:
            json_str = "\n".join(json_lines).strip()
            try:
                deid_data = json.loads(json_str)
                results.setdefault(unique_key, []).append(deid_data)
            except Exception as e:
                print(f"Error parsing JSON for key {unique_key}: {e}")
    return results

def test_consistency(random_sample_count=5, output_file="messages_with_deid.txt"):
    # Parse the output file
    grouped = parse_output_file(output_file)
    
    # Filter keys that appear more than once for meaningful consistency testing.
    multi_occurrence_keys = {k: v for k, v in grouped.items() if len(v) > 1}
    
    if not multi_occurrence_keys:
        print("No keys appear more than once in the output file. Cannot test consistency across messages.")
        return
    
    # Randomly sample keys (or all if fewer than random_sample_count)
    sample_keys = random.sample(list(multi_occurrence_keys.keys()), 
                                min(random_sample_count, len(multi_occurrence_keys)))
    
    all_passed = True
    for key in sample_keys:
        deid_list = multi_occurrence_keys[key]
        # Compare by converting each dict to a sorted JSON string.
        first_str = json.dumps(deid_list[0], sort_keys=True)
        consistent = all(json.dumps(item, sort_keys=True) == first_str for item in deid_list[1:])
        if consistent:
            print(f"Unique key {key} is consistent across {len(deid_list)} messages.")
        else:
            print(f"Inconsistency found for unique key {key}:")
            for idx, item in enumerate(deid_list, start=1):
                print(f"Message {idx}: {json.dumps(item, indent=2, sort_keys=True)}")
            all_passed = False

    if all_passed:
        print("Test passed: All sampled unique keys show consistent de-identified data.")
    else:
        print("Test failed: Inconsistencies were found.")

if __name__ == "__main__":
    # Adjust the output file name if needed.
    test_consistency(random_sample_count=5, output_file="messages_with_deid.txt")
