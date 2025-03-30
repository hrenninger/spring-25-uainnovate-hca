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

def parse_hl7_date(date_str):
    """
    Parse an HL7 date/time string.
    HL7 dates are often in the format YYYYMMDDHHMMSS (or a shorter version).
    This function attempts to parse the first 14 characters if available.
    """
    try:
        if len(date_str) >= 14:
            return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
        elif len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        return datetime.min
    return datetime.min

def generate_unique_key(facility: str, mrn: str, secret_key: str = None, use_hmac: bool = False) -> str:
    """
    Generate a unique key based on the facility and MRN combination.
    """
    composite = f"{facility}-{mrn}"
    if use_hmac and secret_key:
        key_bytes = secret_key.encode('utf-8')
        composite_bytes = composite.encode('utf-8')
        hash_obj = hmac.new(key_bytes, composite_bytes, hashlib.sha256)
    else:
        hash_obj = hashlib.sha256(composite.encode('utf-8'))
    return hash_obj.hexdigest()

def extract_fields_from_message(msg: str):
    """
    Extract the Facility from the MSH segment and the MRN from the first PID segment.
    """
    facility = None
    mrn = None
    lines = msg.splitlines()
    if lines:
        msh_fields = lines[0].split("|")
        if len(msh_fields) >= 4:
            facility = msh_fields[3]
    for line in lines:
        if line.startswith("PID"):
            pid_fields = line.split("|")
            if len(pid_fields) >= 4:
                mrn = pid_fields[3].split("^")[0]
            break
    return facility, mrn

def extract_patient_data(msg: str) -> dict:
    """
    Extract patient data from the HL7 message.
    Returns a dictionary with keys:
    name, mrn, alt_patient_id, mothers_maiden_name, dob, sex,
    patient_alias, location, home_phone, business_phone, account_number, ssn.
    """
    data = {
        "name": "",
        "mrn": "",
        "alt_patient_id": "",
        "mothers_maiden_name": "",
        "dob": "",
        "sex": "",
        "patient_alias": "",
        "location": {},
        "home_phone": "",
        "business_phone": "",
        "account_number": "",
        "ssn": ""
    }
    lines = msg.splitlines()
    for line in lines:
        if line.startswith("PID"):
            pid_fields = line.split("|")
            # PID-3: Primary Patient ID (MRN)
            if len(pid_fields) >= 4:
                data["mrn"] = pid_fields[3].split("^")[0].strip()
            # PID-4: Alternate Patient ID
            if len(pid_fields) >= 5:
                data["alt_patient_id"] = pid_fields[4].strip()
            # PID-5: Patient Name (format: Last^First)
            if len(pid_fields) >= 6:
                name_field = pid_fields[5].strip()
                name_parts = name_field.split("^")
                if len(name_parts) >= 2:
                    data["name"] = f"{name_parts[1]} {name_parts[0]}"  # First Last
                else:
                    data["name"] = name_field
            # PID-6: Mother's Maiden Name
            if len(pid_fields) >= 7:
                data["mothers_maiden_name"] = pid_fields[6].strip()
            # PID-7: Date of Birth
            if len(pid_fields) >= 8:
                data["dob"] = pid_fields[7].strip()
            # PID-8: Administrative Sex
            if len(pid_fields) >= 9:
                data["sex"] = pid_fields[8].strip()
            # PID-9: Patient Alias
            if len(pid_fields) >= 10:
                data["patient_alias"] = pid_fields[9].strip()
            # PID-11: Patient Address (format: Street^Other^City^State^Zip^Country)
            if len(pid_fields) >= 12:
                address_field = pid_fields[11].strip()
                address_parts = address_field.split("^")
                loc = {}
                if len(address_parts) >= 4:
                    loc["city"] = address_parts[2].strip()
                    loc["state"] = address_parts[3].strip()
                if len(address_parts) >= 5:
                    loc["zipcode"] = address_parts[4].strip()
                data["location"] = loc
            # PID-13: Home Phone
            if len(pid_fields) >= 14:
                data["home_phone"] = pid_fields[13].strip()
            # PID-14: Business Phone
            if len(pid_fields) >= 15:
                data["business_phone"] = pid_fields[14].strip()
            # PID-18: Account Number
            if len(pid_fields) >= 19:
                data["account_number"] = pid_fields[18].strip()
            # PID-19: SSN
            if len(pid_fields) >= 20:
                data["ssn"] = pid_fields[19].strip()
            break  # Only process the first PID segment
    return data

def generate_fake_dob(original_dob_str):
    """
    Generate a fake date of birth within the same year as the original.
    Assumes original_dob_str is in the format YYYYMMDD.
    """
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
    """
    Generate a fake MRN as a 10-digit number string.
    """
    return str(random.randint(10**9, 10**10 - 1))

def generate_fake_alt_patient_id():
    """
    Generate a fake alternate patient ID in the format 'H' followed by 4 digits.
    """
    return "H" + str(random.randint(1000, 9999))

def generate_fake_account_number():
    """
    Generate a fake account number in the format 'H' followed by 11 digits (with leading zeros if necessary).
    """
    return "H" + format(random.randint(0, 99999999999), '011d')

def create_deidentified_dict(unique_id: str, original_data: dict) -> dict:
    """
    Create a dictionary holding the new, de-identified patient data.
    Uses gender-specific name generation if a sex field is provided.
    Adds a separate patient_alias field which is set to the fake name if the original message included a PID-9.
    Generates new fake values for alternate patient ID, mother's maiden name, phone numbers, and account number
    only if they were originally present.
    Also builds a sensitive_info list that includes alternate formats for DOB, phone numbers, and name components.
    """
    # Generate fake name only if original name exists.
    if original_data.get("name"):
        if "sex" in original_data and original_data["sex"]:
            if original_data["sex"].upper() == "M":
                new_name = fake.name_male()
            elif original_data["sex"].upper() == "F":
                new_name = fake.name_female()
            else:
                new_name = fake.name()
        else:
            new_name = fake.name()
    else:
        new_name = ""
    
    # Set patient_alias to fake name only if PID-9 is present.
    new_patient_alias = new_name if original_data.get("patient_alias") else ""
    
    new_mrn = generate_fake_mrn() if original_data.get("mrn") else ""
    new_dob = generate_fake_dob(original_data["dob"]) if original_data.get("dob") else ""
    new_ssn = fake.ssn() if original_data.get("ssn") else ""
    
    if original_data.get("location") and original_data["location"].get("state"):
        state = original_data["location"].get("state")
        new_location = {
            "state": state,
            "city": fake.city(),
            "zipcode": fake.zipcode()
        }
    else:
        new_location = {}
    
    # Generate new fake values for alternate patient id, mother's maiden name,
    # home phone, business phone, and account number if originally present.
    new_alt_patient_id = generate_fake_alt_patient_id() if original_data.get("alt_patient_id") else ""
    new_mothers_maiden_name = fake.last_name() if original_data.get("mothers_maiden_name") else ""
    new_home_phone = fake.phone_number() if original_data.get("home_phone") else ""
    new_business_phone = fake.phone_number() if original_data.get("business_phone") else ""
    new_account_number = generate_fake_account_number() if original_data.get("account_number") else ""
    
    # Build sensitive_info with additional alternate formats.
    sensitive_info = []
    # For name: add full name and split into first and last names if possible.
    if original_data.get("name"):
        sensitive_info.append(original_data["name"])
        parts = original_data["name"].split()
        if len(parts) >= 2:
            sensitive_info.append(parts[0])  # first name
            sensitive_info.append(" ".join(parts[1:]))  # last name(s)
    # For DOB: add the original, YYYY-MM-DD, and MM/DD/YYYY formats.
    if original_data.get("dob") and len(original_data["dob"]) == 8:
        dob_orig = original_data["dob"]
        sensitive_info.append(dob_orig)
        year = dob_orig[:4]
        month = dob_orig[4:6]
        day = dob_orig[6:8]
        sensitive_info.append(f"{year}-{month}-{day}")
        sensitive_info.append(f"{month}/{day}/{year}")
    elif original_data.get("dob"):
        sensitive_info.append(original_data["dob"])
    # For phone numbers: add the original and a digits-only version.
    for phone_field in ["home_phone", "business_phone"]:
        if original_data.get(phone_field):
            phone = original_data[phone_field]
            sensitive_info.append(phone)
            alt_phone = ''.join(filter(str.isdigit, phone))
            if alt_phone and alt_phone != phone:
                sensitive_info.append(alt_phone)
    # Add remaining fields as-is if they exist.
    for key in ["ssn", "mrn", "alt_patient_id", "mothers_maiden_name", "account_number", "patient_alias"]:
        if original_data.get(key):
            sensitive_info.append(original_data[key])
    
    deidentified_data = {
        "unique_id": unique_id,
        "new_name": new_name,
        "patient_alias": new_patient_alias,
        "new_mrn": new_mrn,
        "new_dob": new_dob,
        "new_location": new_location,
        "new_ssn": new_ssn,
        "new_alt_patient_id": new_alt_patient_id,
        "new_mothers_maiden_name": new_mothers_maiden_name,
        "new_home_phone": new_home_phone,
        "new_business_phone": new_business_phone,
        "new_account_number": new_account_number,
        "sensitive_info": sensitive_info
    }
    return deidentified_data

def main():
    parser = argparse.ArgumentParser(
        description="Process an HL7 file to extract Facility and MRN, generate unique keys, and sort messages."
    )
    parser.add_argument("hl7_file", help="Path to the HL7 file to process")
    parser.add_argument("--secret", help="Optional secret key for HMAC", default=None)
    parser.add_argument("--use_hmac", action="store_true", help="Flag to use HMAC for key generation")
    args = parser.parse_args()
    
    with open(args.hl7_file, 'r') as infile:
        content = infile.read()
    
    # Split file into individual messages (each message starts with "MSH|")
    messages = re.split(r'(?=^MSH\|)', content, flags=re.MULTILINE)
    messages = [msg for msg in messages if msg.strip()]
    
    # A mapping from unique_id to de-identified data to ensure consistency across entries.
    identity_map = {}
    
    messages_with_details = []
    for msg in messages:
        # Extract the date/time from MSH-7 for sorting.
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
        
        # Extract Facility and MRN for key generation.
        facility, mrn = extract_fields_from_message(msg)
        unique_key = ""
        if facility and mrn:
            unique_key = generate_unique_key(facility, mrn, secret_key=args.secret, use_hmac=args.use_hmac)
        
        # Extract additional patient data from the HL7 message.
        patient_data = extract_patient_data(msg)
        
        # Reuse de-identified data if this unique key has already been processed.
        if unique_key in identity_map:
            deid_dict = identity_map[unique_key]
        else:
            deid_dict = create_deidentified_dict(unique_key, patient_data)
            identity_map[unique_key] = deid_dict
        
        messages_with_details.append((dt, msg, unique_key, facility, mrn, deid_dict))
    
    # Sort messages by date/time (oldest to newest).
    messages_with_details.sort(key=lambda x: x[0])
    
    # Write output file with each message prefixed by its unique key and de-identified mapping.
    with open("messages_with_deid.txt", "w") as outfile:
        for dt, msg, unique_key, facility, mrn, deid_dict in messages_with_details:
            outfile.write(f"Unique Key: {unique_key}\n")
            outfile.write("Original HL7 Message:\n")
            outfile.write(msg + "\n")
            outfile.write("De-Identified Data:\n")
            outfile.write(json.dumps(deid_dict, indent=2) + "\n")
            outfile.write("-" * 80 + "\n")
    
    print("Processing complete. Output written to 'messages_with_deid.txt'.")

if __name__ == "__main__":
    main()
