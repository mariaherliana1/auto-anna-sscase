from typing import Optional

import pandas as pd

from src.CallDetail import CallDetail
from src.utils import parse_jakarta_datetime, convert_to_jakarta_time_iso, parse_phone_number, call_hash
import math


def process_dashboard_csv(
    file_path: str, carrier: str, call_details: Optional[dict[str, CallDetail]] = None
) -> dict[str, CallDetail]:
    if call_details is None:
        call_details = {}

    print(f"- Reading dashboard file {file_path}...")
    df1 = pd.read_csv(file_path, low_memory=False).astype(str)
    for index, row in df1.iterrows():
        call_detail = CallDetail(
            sequence_id=row["Sequence ID"],
            user_name=row["User name"],
            call_from=row["Call from"],
            call_to=row["Call to"],
            call_type=row["Call type"],
            dial_start_at=row["Dial begin time"],
            dial_answered_at=row["Call begin time"],
            dial_end_at=row["Call end time"],
            ringing_time=row["Ringing time"],
            call_duration=row["Call duration"],
            call_memo=row["Call memo"],
            call_charge="0",
            carrier=carrier,
        )
        key = call_detail.hash_key()
        if key in call_details:
            # If the call is already in the dictionary, update it with the information from the dashboard file
            existing_call_detail = call_details[key]
            existing_call_detail.user_name = row["User name"]
            existing_call_detail.call_memo = row["Call memo"]
        else:
            call_details[call_detail.hash_key()] = call_detail
    return call_details


def process_console_csv(
    file_path: str, carrier: str, call_details: dict[str, CallDetail]
) -> dict[str, CallDetail]:
    df2 = pd.read_csv(file_path, low_memory=False).astype(str)

    # Call type normalization mapping
    call_type_mapping = {
        "OUTGOING_CALL": "Outbound call",
        "OUTGOING_CALL_ABSENCE": "Outbound call (No answer)",
    }

    for index, row in df2.iterrows():
        # Normalize phone numbers before processing
        normalized_call_from = parse_phone_number(row["used_number"])
        normalized_call_to = parse_phone_number(row["number"])

        # Check if the call is already in the call_details dictionary
        key = call_hash(normalized_call_from, normalized_call_to, parse_jakarta_datetime(row["dial_starts_at"], row["pbx_region"]))

        call_type = call_type_mapping.get(row["call_type"], row["call_type"])

        if key in call_details:
            # If the call is already in the dictionary, update it with the information from the console file
            call_detail = call_details[key]
            call_detail.call_type = call_type
            call_detail.dial_answered_at = parse_jakarta_datetime(row["dial_answered_at"], row["pbx_region"])
            call_detail.dial_end_at = parse_jakarta_datetime(row["dial_ends_at"], row["pbx_region"])
            call_detail.ringing_time = row["all_duration_of_call_sec_str"]
            call_detail.call_duration = row["duration_of_call_sec_str"]
            call_detail.call_memo = ""
            call_detail.call_charge = row["discount"]
        else:
            # If the call is not in the dictionary, check for sequence_id
            sequence_id = row["call_id"]  # Assuming call_id is the sequence_id in the console file
            if not any(call_detail.sequence_id == sequence_id for call_detail in call_details.values()):
                # If the sequence_id does not exist in call_details, add it with a user name of "-"
                call_detail = CallDetail(
                    sequence_id=sequence_id,
                    user_name="-",
                    call_from=normalized_call_from,
                    call_to=normalized_call_to,
                    call_type=call_type,
                    dial_start_at=parse_jakarta_datetime(row["dial_starts_at"], row["pbx_region"]),
                    dial_answered_at=parse_jakarta_datetime(row["dial_answered_at"], row["pbx_region"]),
                    dial_end_at=parse_jakarta_datetime(row["dial_ends_at"], row["pbx_region"]),
                    ringing_time=row["all_duration_of_call_sec_str"],
                    call_duration=row["duration_of_call_sec_str"],
                    call_memo="",
                    call_charge=row["discount"],
                    carrier=carrier,
                )
                call_details[key] = call_detail
    return call_details


def process_merged_csv(
    file_path: str, call_details: dict[str, CallDetail]
) -> dict[str, CallDetail]:
    """Reads a merged file and loads it to memory.
    Username, Call from, Call to, Call type, Dial starts at, Dial answered at, Dial ends at,
    Ringing time, Call duration,Call memo,Call charge
    """
    print(f"- Reading {file_path} file...")
    df3 = pd.read_csv(file_path, low_memory=False).astype(str)
    print("- Processing merged CSV file...")
    for index, row in df3.iterrows():
        call_detail = CallDetail(
            sequence_id=row.get["call_id"] or row.get["Sequence ID"],
            user_name=row["User name"],
            call_from=row["Call from"],
            call_to=row["Call to"],
            call_type=row["Call type"],
            dial_start_at=row["Dial starts at"],
            dial_answered_at=row["Dial answered at"],
            dial_end_at=row["Dial ends at"],
            ringing_time=row["Ringing time"],
            call_duration=row["Call duration"],
            call_memo=row["Call memo"],
            call_charge=row["Call charge"],
            carrier=carrier,
        )
        call_details[call_detail.hash_key()] = call_detail
    return call_details

def round_up_duration(call_duration: str) -> int:
    try:
        #print(f"Processing call duration: {call_duration}")
        
        if ':' in call_duration:
            h, m, s = map(int, call_duration.split(':'))
            total_minutes = h * 60 + m + math.ceil(s / 60)
        else:
            total_minutes = math.ceil(int(call_duration) / 60)  # Assume it's in seconds
        
        return total_minutes
    except Exception as e:
        print(f"Error parsing call duration: {call_duration}, Error: {e}")
        return 0


def save_merged_csv(call_details: dict[str, CallDetail], output_path: str) -> None:
    print("- Saving merged CSV file...")
    call_details_list = []
    for key, value in call_details.items():
        call_dict = value.to_dict()
        call_dict["Round up duration"] = round_up_duration(call_dict["Call duration"])
        call_details_list.append(call_dict)
    
    df = pd.DataFrame(call_details_list)
    df.to_csv(output_path, index=False)