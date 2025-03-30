import re
import json
import hashlib
import hmac
import argparse
import random
import calendar
from datetime import datetime
from faker import Faker
from physician import is_physician_field, extract_physician_fields, process_hl7_message as process_physician_segment

fake = Faker()

# Sensitive words/phrases list is no longer used for OBX redaction.
sensitive_words = [
    "SSN",
    "Account",
    "DOB",
    "SensitivePhrase"  # This list is retained but not applied.
]

def preserve_carets(original_field: str, new_value: str) -> str:
    """
    Preserve the number of components (separated by '^') from the original_field.
    If the new_value has fewer components, append empty strings so that the total count matches.
    """
    orig_components = original_field.split("^")
    new_components = new_value.split("^")
    if len(new_components) < len(orig_components):
        new_components += [""] * (len(orig_components) - len(new_components))
    return "^".join(new_components)

def parse_hl7_date(message):
    try:
        for line in message.splitlines():
            if line.startswith("MSH"):
                fields = line.split("|")
                if len(fields) > 6:
                    dt_field = fields[6].strip()[:12]
                    if len(dt_field) == 12:
                        return datetime.strptime(dt_field, "%Y%m%d%H%M")
                    elif len(dt_field) == 8:
                        return datetime.strptime(dt_field, "%Y%m%d")
    except Exception:
        return datetime.min
    return datetime.min

def generate_unique_key(facility: str, pid_3: str, secret_key: str = None, use_hmac: bool = False) -> str:
    composite = f"{facility}-{pid_3}"
    if use_hmac and secret_key:
        key_bytes = secret_key.encode('utf-8')
        composite_bytes = composite.encode('utf-8')
        hash_obj = hmac.new(key_bytes, composite_bytes, hashlib.sha256)
    else:
        hash_obj = hashlib.sha256(composite.encode('utf-8'))
    return hash_obj.hexdigest()

def extract_fields_from_message(msg: str):
    facility = None
    pid_3 = None
    lines = msg.splitlines()
    if lines:
        msh_fields = lines[0].split("|")
        if len(msh_fields) >= 4:
            facility = msh_fields[3]
    for line in lines:
        if line.startswith("PID"):
            pid_fields = line.split("|")
            if len(pid_fields) >= 4:
                # PID-3 may have repeating values separated by "~"
                pid3_reps = pid_fields[3].split("~")
                pid_3 = pid3_reps[0].split("^")[0].strip()
            break
    return facility, pid_3

def extract_patient_data(msg: str) -> dict:
    data = {
        "pid_3": "",            # Primary identifier from PID-3 (first repetition)
        "pid_3_account": "",    # Account number from PID-3 if type code is "AN"
        "pid_4": "",            # Alternate Patient ID (PID-4)
        "pid_5": "",            # Patient Name (PID-5)
        "pid_6": "",            # Mother's Maiden Name (PID-6)
        "pid_7": "",            # Date of Birth (PID-7)
        "pid_8": "",            # Sex (PID-8)
        "pid_9": "",            # Patient Alias (PID-9)
        "pid_11": {},           # Patient Address (PID-11) as dict (city, state, zipcode)
        "pid_13": "",           # Home Phone (PID-13)
        "pid_14": "",           # Business Phone (PID-14)
        "pid_18": "",           # Account Number (PID-18)
        "pid_19": "",           # SSN (PID-19)
        "pid_21": ""            # Mother's Identifier (PID-21)
    }
    for line in msg.splitlines():
        if line.startswith("PID"):
            pid_fields = line.split("|")
            # Process PID-3 field
            if len(pid_fields) >= 4:
                pid3_field = pid_fields[3]
                pid3_reps = pid3_field.split("~")
                data["pid_3"] = pid3_reps[0].split("^")[0].strip()
                # Look for an account number in any repetition: if the 5th component is "AN"
                for rep in pid3_reps:
                    components = rep.split("^")
                    if len(components) >= 5 and components[4].upper() == "AN":
                        data["pid_3_account"] = components[0].strip()
                        break
            if len(pid_fields) >= 5:
                data["pid_4"] = pid_fields[4].strip()
            if len(pid_fields) >= 6:
                name_field = pid_fields[5].strip()
                parts = name_field.split("^")
                data["pid_5"] = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else name_field
            if len(pid_fields) >= 7:
                data["pid_6"] = pid_fields[6].strip()
            if len(pid_fields) >= 8:
                data["pid_7"] = pid_fields[7].strip()
            if len(pid_fields) >= 9:
                data["pid_8"] = pid_fields[8].strip()
            if len(pid_fields) >= 10:
                data["pid_9"] = pid_fields[9].strip()
            if len(pid_fields) >= 12:
                address_field = pid_fields[11].strip()
                parts = address_field.split("^")
                loc = {}
                if len(parts) >= 4:
                    loc["city"] = parts[2].strip()
                    loc["state"] = parts[3].strip()
                if len(parts) >= 5:
                    loc["zipcode"] = parts[4].strip()
                data["pid_11"] = loc
            if len(pid_fields) >= 14:
                data["pid_13"] = pid_fields[13].strip()
            if len(pid_fields) >= 15:
                data["pid_14"] = pid_fields[14].strip()
            if len(pid_fields) >= 19:
                data["pid_18"] = pid_fields[18].strip()
            if len(pid_fields) >= 20:
                data["pid_19"] = pid_fields[19].strip()
            if len(pid_fields) >= 22:
                data["pid_21"] = pid_fields[21].strip()
            break
    return data

def generate_fake_dob(original_dob_str):
    try:
        year = int(original_dob_str[:4])
    except Exception:
        year = 1970
    month = random.randint(1, 12)
    day = random.randint(1, calendar.monthrange(year, month)[1])
    today = datetime.today()
    if today.year - year >= 90:
        year = today.year - 90
    return datetime(year, month, day).strftime("%Y%m%d")

def generate_fake_mrn():
    return str(random.randint(10**9, 10**10 - 1))

def generate_fake_alt_patient_id():
    return chr(random.randint(65, 90)) + str(random.randint(1000, 9999))

def generate_fake_account_number(original_account: str, secret_key: str = None, use_hmac: bool = False) -> str:
    composite = original_account
    if use_hmac and secret_key:
        key_bytes = secret_key.encode('utf-8')
        composite_bytes = composite.encode('utf-8')
        hash_obj = hmac.new(key_bytes, composite_bytes, hashlib.sha256)
    else:
        hash_obj = hashlib.sha256(composite.encode('utf-8'))
    fake_num = int(hash_obj.hexdigest(), 16) % (10**11)
    return "H" + format(fake_num, '011d')

def append_deid_segment(msg: str, deid_dict: dict) -> str:
    # Append a ZDEID segment containing the JSON dump of de-identified data.
    #return msg + "\n" + "ZDEID|" + json.dumps(deid_dict)
    return msg 

def deidentify_hl7_message(msg: str, deid_dict: dict, physician_mapping: dict) -> str:
    # Note: This version leaves OBX segments unchanged.
    new_lines = []
    for line in msg.splitlines():
        if line.startswith("PID"):
            pid_fields = line.split("|")
            while len(pid_fields) < 22:
                pid_fields.append("")
            pid_fields[3] = preserve_carets(pid_fields[3], deid_dict.get("new_pid_3", pid_fields[3]))
            if deid_dict.get("new_pid_3_account"):
                account_rep = preserve_carets("dummy^^^^AN", deid_dict["new_pid_3_account"])
                pid_fields[3] += "~" + account_rep
            pid_fields[4] = preserve_carets(pid_fields[4], deid_dict.get("new_pid_4", pid_fields[4]))
            pid_fields[5] = preserve_carets(pid_fields[5], deid_dict.get("new_pid_5", pid_fields[5]))
            pid_fields[6] = preserve_carets(pid_fields[6], deid_dict.get("new_pid_6", pid_fields[6]))
            pid_fields[7] = preserve_carets(pid_fields[7], deid_dict.get("new_pid_7", pid_fields[7]))
            pid_fields[8] = preserve_carets(pid_fields[8], deid_dict.get("new_pid_8", pid_fields[8]))
            pid_fields[9] = preserve_carets(pid_fields[9], deid_dict.get("new_pid_9", pid_fields[9]))
            # Reconstruct PID-11 (address)
            new_pid_11 = deid_dict.get("new_pid_11", {})
            orig_address = pid_fields[11]
            orig_components = orig_address.split("^")
            new_components = [
                "",
                new_pid_11.get("city", ""),
                new_pid_11.get("state", ""),
                new_pid_11.get("zipcode", "")
            ]
            while len(new_components) < len(orig_components):
                new_components.append("")
            pid_fields[11] = "^".join(new_components)
            pid_fields[13] = preserve_carets(pid_fields[13], deid_dict.get("new_pid_13", pid_fields[13]))
            pid_fields[14] = preserve_carets(pid_fields[14], deid_dict.get("new_pid_14", pid_fields[14]))
            pid_fields[18] = preserve_carets(pid_fields[18], deid_dict.get("new_pid_18", pid_fields[18]))
            pid_fields[19] = preserve_carets(pid_fields[19], deid_dict.get("new_pid_19", pid_fields[19]))
            if len(pid_fields) >= 22:
                pid_fields[21] = preserve_carets(pid_fields[21], deid_dict.get("new_pid_21", pid_fields[21]))
            new_lines.append("|".join(pid_fields))
        elif line.startswith("PV1"):
            processed = process_physician_segment(line, physician_mapping)
            new_lines.append(processed)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)

def create_deidentified_dict(unique_id: str, original_data: dict, deid_physicians: list,
                             account_to_deid_map: dict,
                             secret_key: str = None, use_hmac: bool = False) -> dict:
    if original_data.get("pid_5"):
        if original_data.get("pid_8"):
            if original_data["pid_8"].upper() == "M":
                new_name = fake.name_male()
            elif original_data["pid_8"].upper() == "F":
                new_name = fake.name_female()
            else:
                new_name = fake.name()
        else:
            new_name = fake.name()
        name_parts = new_name.split()
        if len(name_parts) >= 2:
            new_pid_5 = f"{name_parts[-1]}^{name_parts[0]}"
        else:
            new_pid_5 = new_name
    else:
        new_pid_5 = ""
    new_pid_9 = new_pid_5 if original_data.get("pid_9") else ""
    new_pid_3 = generate_fake_mrn() if original_data.get("pid_3") else ""
    new_pid_7 = generate_fake_dob(original_data["pid_7"]) if original_data.get("pid_7") else ""
    new_pid_19 = fake.ssn() if original_data.get("pid_19") else ""
    if original_data.get("pid_11") and original_data["pid_11"].get("state"):
        state = original_data["pid_11"]["state"]
        new_pid_11 = {"state": state, "city": fake.city(), "zipcode": fake.zipcode()}
    else:
        new_pid_11 = {}
    new_pid_4 = generate_fake_alt_patient_id() if original_data.get("pid_4") else ""
    new_pid_6 = fake.last_name() if original_data.get("pid_6") else ""
    new_pid_13 = fake.phone_number() if original_data.get("pid_13") else ""
    new_pid_14 = fake.phone_number() if original_data.get("pid_14") else ""
    # Fix for mother-baby linkage
    if original_data.get("pid_21"):
        new_pid_18 = account_to_deid_map.get(original_data["pid_18"], original_data["pid_18"])
        # The crucial fix: Map PID-21 to the same deidentified value as the account it refers to
        new_pid_21 = account_to_deid_map.get(original_data["pid_21"], original_data["pid_21"])
    else:
        new_pid_18 = account_to_deid_map.get(original_data["pid_18"], original_data["pid_18"])
        new_pid_21 = ""
    
    new_pid_3_account = account_to_deid_map.get(original_data.get("pid_3_account", ""), "")
    

    
    sensitive_info = []
    if original_data.get("pid_5"):
        sensitive_info.append(original_data["pid_5"])
        parts = original_data["pid_5"].split()
        if len(parts) >= 2:
            sensitive_info.append(parts[0])
            sensitive_info.append(" ".join(parts[1:]))
    if original_data.get("pid_7") and len(original_data["pid_7"]) == 8:
        dob_orig = original_data["pid_7"]
        sensitive_info.append(dob_orig)
        year, month, day = dob_orig[:4], dob_orig[4:6], dob_orig[6:8]
        sensitive_info.extend([f"{year}-{month}-{day}", f"{month}-{day}-{year}", f"{day}-{month}-{year}",
                                f"{year}/{month}/{day}", f"{month}/{day}/{year}", f"{day}/{month}/{year}",
                                f"{month}/{day}", f"{calendar.month_name[int(month)]} {day}, {year}"])
    elif original_data.get("pid_7"):
        sensitive_info.append(original_data["pid_7"])
    for phone_field in ["pid_13", "pid_14"]:
        if original_data.get(phone_field):
            phone = original_data[phone_field]
            sensitive_info.append(phone)
            alt_phone = ''.join(filter(str.isdigit, phone))
            if alt_phone and alt_phone != phone:
                sensitive_info.append(alt_phone)
    for key in ["pid_19", "pid_3", "pid_4", "pid_6", "pid_9"]:
        if original_data.get(key):
            sensitive_info.append(original_data[key])
    sensitive_info = [x for x in sensitive_info if not re.match(r'^\^+$', x)]
    
    deidentified_data = {
        "unique_id": unique_id,
        "new_pid_3": new_pid_3,
        "new_pid_4": new_pid_4,
        "new_pid_5": new_pid_5,
        "new_pid_6": new_pid_6,
        "new_pid_7": new_pid_7,
        "new_pid_8": original_data.get("pid_8", ""),
        "new_pid_9": new_pid_9,
        "new_pid_11": new_pid_11,
        "new_pid_13": new_pid_13,
        "new_pid_14": new_pid_14,
        "new_pid_18": new_pid_18,
        "new_pid_19": new_pid_19,
        "new_pid_21": new_pid_21,
        "new_pid_3_account": new_pid_3_account,
        "sensitive_info": sensitive_info,
        "deid_physicians": deid_physicians
    }
    return deidentified_data

def main():
    parser = argparse.ArgumentParser(description="Process HL7 file for de-identification")
    parser.add_argument("hl7_file", help="Path to HL7 file")
    parser.add_argument("--secret", help="Secret key for HMAC", default=None)
    parser.add_argument("--use_hmac", action="store_true", help="Use HMAC for key generation")
    args = parser.parse_args()

    with open(args.hl7_file, 'r') as infile:
        content = infile.read()

    messages = re.split(r'(?=^MSH\|)', content, flags=re.MULTILINE)
    messages = [msg for msg in messages if msg.strip()]

    identity_map = {}
    account_to_deid_map = {}
    mother_to_deid_map = {}
    physician_mapping = {}  # For consistent fake physician mapping
    messages_with_details = []

    # PASS 1: Build account_to_deid_map from all messages
    for msg in messages:
        patient_data = extract_patient_data(msg)

        # Map PID-18 (account number)
        if patient_data.get("pid_18") and patient_data["pid_18"] not in account_to_deid_map:
            account_to_deid_map[patient_data["pid_18"]] = generate_fake_account_number(
                patient_data["pid_18"], args.secret, args.use_hmac
            )

        # Map PID-3 account if present
        if patient_data.get("pid_3_account") and patient_data["pid_3_account"] not in account_to_deid_map:
            account_to_deid_map[patient_data["pid_3_account"]] = generate_fake_account_number(
                patient_data["pid_3_account"], args.secret, args.use_hmac
            )
    for msg in messages:
        orig_msg = msg
        lines = msg.splitlines()
        dt = parse_hl7_date(lines[0]) if lines else datetime.min

        facility, pid_3 = extract_fields_from_message(msg)
        unique_key = generate_unique_key(facility, pid_3, args.secret, args.use_hmac) if facility and pid_3 else ""

        patient_data = extract_patient_data(msg)

        # Use pre-built map
        if patient_data.get("pid_18"):
            patient_data["pid_18"] = account_to_deid_map[patient_data["pid_18"]]
        if patient_data.get("pid_3_account"):
            patient_data["pid_3_account"] = account_to_deid_map[patient_data["pid_3_account"]]
        if patient_data.get("pid_21"):
            if patient_data["pid_21"] in account_to_deid_map:
                patient_data["pid_21"] = account_to_deid_map[patient_data["pid_21"]]
            else:
                # Fallback just in case (shouldn't be needed if pass 1 was exhaustive)
                if patient_data["pid_21"] not in mother_to_deid_map:
                    mother_to_deid_map[patient_data["pid_21"]] = generate_fake_account_number(patient_data["pid_21"], args.secret, args.use_hmac)
                patient_data["pid_21"] = mother_to_deid_map[patient_data["pid_21"]]

        if unique_key in identity_map:
            deid_dict = identity_map[unique_key]
        else:
            deid_physicians = extract_physician_fields(msg, physician_mapping)
            deid_dict = create_deidentified_dict(unique_key, patient_data, deid_physicians,
                                     account_to_deid_map,
                                     args.secret, args.use_hmac)
            identity_map[unique_key] = deid_dict

        deid_hl7 = deidentify_hl7_message(msg, deid_dict, physician_mapping)
        deid_hl7_with_segment = append_deid_segment(deid_hl7, deid_dict)

        messages_with_details.append((dt, orig_msg, deid_hl7_with_segment, unique_key, facility, pid_3, deid_dict))




    messages_with_details.sort(key=lambda x: x[0])
    with open("messages_deidentified.txt", "w") as outfile:
        for dt, orig_msg, deid_msg, unique_key, facility, pid_3, deid_dict in messages_with_details:
            # outfile.write("Original HL7 Message:\n")
            # outfile.write(orig_msg + "\n\n")
            # outfile.write("De-Identified HL7 Message:\n")
            outfile.write(deid_msg + "\n\n")
            # outfile.write("De-Identified Data JSON:\n")
            # outfile.write(json.dumps(deid_dict, indent=2) + "\n")
            # outfile.write("-" * 80 + "\n")
    print("Processing complete. Output written to 'messages_with_deid.txt'.")

if __name__ == "__main__":
    main()
