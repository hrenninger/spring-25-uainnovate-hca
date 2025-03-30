import re
import json
import hashlib
import hmac
import argparse
import random
import calendar
from datetime import datetime
from faker import Faker

fake = Faker()

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
                pid_3 = pid_fields[3].split("^")[0]
            break
    return facility, pid_3

def extract_patient_data(msg: str) -> dict:
    data = {
        "pid_3": "",   # MRN (PID-3)
        "pid_4": "",   # Alternate Patient ID (PID-4)
        "pid_5": "",   # Patient Name (PID-5)
        "pid_6": "",   # Mother's Maiden Name (PID-6)
        "pid_7": "",   # Date of Birth (PID-7)
        "pid_8": "",   # Sex (PID-8)
        "pid_9": "",   # Patient Alias (PID-9)
        "pid_11": {},  # Patient Address (PID-11) as a dict (city, state, zipcode)
        "pid_13": "",  # Home Phone (PID-13)
        "pid_14": "",  # Business Phone (PID-14)
        "pid_18": "",  # Account Number (PID-18)
        "pid_19": "",  # SSN (PID-19)
        "pid_21": ""   # Mother's Identifier (PID-21)
    }
    lines = msg.splitlines()
    for line in lines:
        if line.startswith("PID"):
            pid_fields = line.split("|")
            if len(pid_fields) >= 4:
                data["pid_3"] = pid_fields[3].split("^")[0].strip()
            if len(pid_fields) >= 5:
                data["pid_4"] = pid_fields[4].strip()
            if len(pid_fields) >= 6:
                name_field = pid_fields[5].strip()
                name_parts = name_field.split("^")
                if len(name_parts) >= 2:
                    data["pid_5"] = f"{name_parts[1]} {name_parts[0]}"
                else:
                    data["pid_5"] = name_field
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
                address_parts = address_field.split("^")
                loc = {}
                if len(address_parts) >= 4:
                    loc["city"] = address_parts[2].strip()
                    loc["state"] = address_parts[3].strip()
                if len(address_parts) >= 5:
                    loc["zipcode"] = address_parts[4].strip()
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
    days_in_month = calendar.monthrange(year, month)[1]
    day = random.randint(1, days_in_month)
    today = datetime.today()
    age = today.year - year
    if age >= 90:
        year = today.year - 90
    fake_dob = datetime(year, month, day)
    return fake_dob.strftime("%Y%m%d")

def generate_fake_mrn():
    return str(random.randint(10**9, 10**10 - 1))

def generate_fake_alt_patient_id():
    letter = chr(random.randint(ord('A'), ord('Z')))
    return letter + str(random.randint(1000, 9999))

def generate_fake_account_number(original_account: str, secret_key: str = None, use_hmac: bool = False) -> str:
    composite = original_account
    if use_hmac and secret_key:
        key_bytes = secret_key.encode('utf-8')
        composite_bytes = composite.encode('utf-8')
        hash_obj = hmac.new(key_bytes, composite_bytes, hashlib.sha256)
    else:
        hash_obj = hashlib.sha256(composite.encode('utf-8'))
    hash_int = int(hash_obj.hexdigest(), 16)
    fake_num = hash_int % (10**11)
    return "H" + format(fake_num, '011d')

def create_deidentified_dict(unique_id: str, original_data: dict, secret_key: str = None, use_hmac: bool = False) -> dict:
    # Generate de-identified values using HL7 field names.
    if original_data.get("pid_5"):
        if original_data.get("pid_8"):
            if original_data["pid_8"].upper() == "M":
                new_pid_5 = fake.name_male()
            elif original_data["pid_8"].upper() == "F":
                new_pid_5 = fake.name_female()
            else:
                new_pid_5 = fake.name()
        else:
            new_pid_5 = fake.name()
    else:
        new_pid_5 = ""
    
    new_pid_9 = new_pid_5 if original_data.get("pid_9") else ""
    new_pid_3 = generate_fake_mrn() if original_data.get("pid_3") else ""
    new_pid_7 = generate_fake_dob(original_data["pid_7"]) if original_data.get("pid_7") else ""
    new_pid_19 = fake.ssn() if original_data.get("pid_19") else ""
    
    if original_data.get("pid_11") and original_data["pid_11"].get("state"):
        state = original_data["pid_11"]["state"]
        new_pid_11 = {
            "state": state,
            "city": fake.city(),
            "zipcode": fake.zipcode()
        }
    else:
        new_pid_11 = {}
    
    new_pid_4 = generate_fake_alt_patient_id() if original_data.get("pid_4") else ""
    new_pid_6 = fake.last_name() if original_data.get("pid_6") else ""
    new_pid_13 = fake.phone_number() if original_data.get("pid_13") else ""
    new_pid_14 = fake.phone_number() if original_data.get("pid_14") else ""
    
    # For account numbers and mother association:
    # If a pid_21 is present in the original message, populate new_pid_21;
    # otherwise, leave new_pid_21 as an empty string.
    if original_data.get("pid_21"):
        new_pid_18 = original_data["pid_18"]
        new_pid_21 = original_data["pid_21"]
    else:
        new_pid_18 = original_data["pid_18"]
        new_pid_21 = ""
    
    # Build sensitive_info with alternate formats, excluding pid_18.
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
        year = dob_orig[:4]
        month = dob_orig[4:6]
        day = dob_orig[6:8]
        sensitive_info.append(f"{year}-{month}-{day}")
        sensitive_info.append(f"{month}-{day}-{year}")
        sensitive_info.append(f"{day}-{month}-{year}")
        sensitive_info.append(f"{year}/{month}/{day}")
        sensitive_info.append(f"{month}/{day}/{year}")
        sensitive_info.append(f"{day}/{month}/{year}")
        sensitive_info.append(f"{month}/{day}")
        sensitive_info.append(f"{calendar.month_name[int(month)]} {day}, {year}")
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
        "sensitive_info": sensitive_info
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
    messages_with_details = []

    for msg in messages:
        lines = msg.splitlines()
        if lines:
            msh_fields = lines[0].split("|")
            if len(msh_fields) >= 7:
                date_str = msh_fields[6]
                dt = parse_hl7_date(date_str)
            else:
                dt = datetime.min
        else:
            dt = datetime.min

        facility, pid_3 = extract_fields_from_message(msg)
        unique_key = generate_unique_key(facility, pid_3, args.secret, args.use_hmac) if facility and pid_3 else ""

        patient_data = extract_patient_data(msg)

        # Map the patient's own account number (PID-18)
        if patient_data.get("pid_18"):
            if patient_data["pid_18"] not in account_to_deid_map:
                account_to_deid_map[patient_data["pid_18"]] = generate_fake_account_number(patient_data["pid_18"], args.secret, args.use_hmac)
            patient_data["pid_18"] = account_to_deid_map[patient_data["pid_18"]]

        # Map the mother's identifier (PID-21), if present.
        if patient_data.get("pid_21"):
            if patient_data["pid_21"] not in mother_to_deid_map:
                mother_to_deid_map[patient_data["pid_21"]] = generate_fake_account_number(patient_data["pid_21"], args.secret, args.use_hmac)
            patient_data["pid_21"] = mother_to_deid_map[patient_data["pid_21"]]

        if unique_key in identity_map:
            deid_dict = identity_map[unique_key]
        else:
            deid_dict = create_deidentified_dict(unique_key, patient_data, args.secret, args.use_hmac)
            identity_map[unique_key] = deid_dict

        messages_with_details.append((dt, msg, unique_key, facility, pid_3, deid_dict))

    messages_with_details.sort(key=lambda x: x[0])

    with open("messages_with_deid.txt", "w") as outfile:
        for dt, msg, unique_key, facility, pid_3, deid_dict in messages_with_details:
            outfile.write(f"Unique Key: {unique_key}\n")
            outfile.write("Original HL7 Message:\n")
            outfile.write(msg + "\n")
            outfile.write("De-Identified Data:\n")
            outfile.write(json.dumps(deid_dict, indent=2) + "\n")
            outfile.write("-" * 80 + "\n")

    print("Processing complete. Output written to 'messages_with_deid.txt'.")


if __name__ == "__main__":
    main()
