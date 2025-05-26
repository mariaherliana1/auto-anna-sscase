from src.utils import parse_phone_number, parse_iso_datetime, parse_time_duration, parse_call_memo, classify_number
from src.idn_area_codes import EMERGENCY_NUMBERS, INTERNATIONAL_PHONE_PREFIXES
import math
from src.utils import call_hash, classify_number, format_datetime_as_human_readable, format_timedelta, format_username, parse_call_memo, parse_iso_datetime, parse_phone_number
from src.international_rates import INTERNATIONAL_RATES

class CallDetail:
    def __init__(
        self,
        sequence_id: str,
        user_name: str,
        call_from: str,
        call_to: str,
        call_type: str,
        dial_start_at: str,
        dial_answered_at: str,
        dial_end_at: str,
        ringing_time: str,
        call_duration: str,
        call_memo: str,
        call_charge: str,
        carrier: str,
    ):
        self.sequence_id = sequence_id
        self.user_name = user_name
        self.call_from = parse_phone_number(call_from)  # Normalizing here
        self.call_to = parse_phone_number(call_to)      # Normalizing here
        self.call_type = call_type
        self.dial_start_at = parse_iso_datetime(dial_start_at)
        self.dial_answered_at = (
            parse_iso_datetime(dial_answered_at) if dial_answered_at != "-" else None
        )
        self.dial_end_at = parse_iso_datetime(dial_end_at)
        self.ringing_time = parse_time_duration(ringing_time)
        self.call_duration = parse_time_duration(call_duration)
        self.call_memo = parse_call_memo(call_memo)
        self.carrier = carrier
        self.number_type = classify_number(self.call_to, self.call_type, self.call_from, self.call_to)
        self.call_charge = self.calculate_call_charge()

    def calculate_per_minute_charge(self, rate: float) -> str:
        minutes = math.ceil(self.call_duration.total_seconds() / 60)
        return str(minutes * rate)

    def calculate_per_second_charge(self, rate: float) -> str:
        return str(self.call_duration.total_seconds() * rate)

    def calculate_call_charge(self) -> str:
        number_type = self.number_type  

        # Incoming call not calculated
        if self.call_type == "Incoming call" and str(self.call_to) in {
            "2130422260",  # naluri
            "2130422288",  # atomy
            "2150981444",  # setlary
            "2023019",     # kclub
            "3613007222", "85592067714", "30000055",  # atlasbeachfest
            "2130012288",  # dermies
            "2130916225",  # bodyfactory
            "3616208838", "2130419840",  # lotusasia
            "2130916222",  # yourmoon
            "88978012549", # kozystay
            "81197800082",  # akasa
            "2130422280", #toffeedev
            "2023016", "2150981419", #madev
            "2023015", #moladin collection
            "2131141038", #moladin CS
            "2150981488", #moladin CSCX
            "2131141039", #moladin RC
            "2130419825", #micehub
            "85592164071", #snj
            "2150320015", #cakap
            "2130012288", #dermies
            "2130200946", "2150913445", #erablue
            "2150913470", "85592164047", #mceasy
            "2023020", #orico
            "2023018", "2130422264", "2150981404", #travelbook
            "81377177190", "22245", "22246", "22247", "22248", "22249", #upperwest
            "85873982744", "2150913456", #yappika
        }:
            return "0"

        if self.call_type in ["Internal Call", "Internal Call (No answer)", "Monitoring"]:
            return "0"

        if self.number_type == "Internal Call":
            return "0"

        S2C_RATES = {
            "30000077": ("per_minute", 450), #naluri
            "30000109": ("per_second", 20), #atomy
            "30000097": ("per_minute", 1350), #setlary
            "30000186": ("per_minute", 1350), #lotusasia
            "30000185": ("per_minute", 1350), #lotusasia
            "30000328": ("per_minute", 1350), #bodyfactory
            "30000175": ("per_minute", 1325), #toffeedev
        }

        rate_info = S2C_RATES.get(str(self.call_to))
        if rate_info:
            mode, rate = rate_info
            if mode == "per_minute":
                return self.calculate_per_minute_charge(rate)
            elif mode == "per_second":
                return self.calculate_per_second_charge(rate)

        SCAN_TO_CALL_NOT_CHARGEABLE = {
            "30000060", # Paragon
            "30000058", # Upperwest
            # Add others only if they should return 0
        }

        if self.call_type == "Answering machine":
            if self.number_type == "scancall":
                # Continue to calculate based on `call_to`
                if str(self.call_to) in SCAN_TO_CALL_NOT_CHARGEABLE:
                    return "0"

                # If none matched, you might want to decide whether to charge default or return 0
                return "0"  # or handle default scan call?

            else:
                # General answering machine not scan call
                return "0"

        PER_SECOND_OUTBOUND_RATES = {
            "2150320015": 12, #cakap
            "2130200946": 12, #erablue
            "2150913445": 12, #erablue
            "50913445": 12, #erablue
            "2150913470": 12, #mceasy
            "50913470": 12, #mceasy
            "85592164047": 12, #mceasy
            "2023020": 8, #orico
            "85873982744": 12, #yappika
            "2150913456": 12, #yappika
            "50913456": 12, #yappika
        }

        if self.call_type == "Outbound call":
            per_second_rate = PER_SECOND_OUTBOUND_RATES.get(str(self.call_from))
            if per_second_rate:
                if self.number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
                    self.number_type not in EMERGENCY_NUMBERS.values() and \
                    self.number_type not in INTERNATIONAL_PHONE_PREFIXES.values():
                    # Normal domestic call → apply special per second rate
                    return self.calculate_per_second_charge(per_second_rate)
                else:
                    # Premium/international call → ignore per second rate, calculate based on number_type rules later
                    pass  # fall through to next rules

        # Premium call for Setlary
        if str(self.call_from) == "2150981444":  # Setlary premium outbound
            if number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
               number_type not in EMERGENCY_NUMBERS.values() and \
               number_type not in INTERNATIONAL_PHONE_PREFIXES.values():
                return self.calculate_per_second_charge(25)
            else:
                duration_in_minutes = self.call_duration.total_seconds() / 60
                return str(math.ceil(duration_in_minutes) * 1300)

        #Moladin - rate 600
        if str(self.call_from) in {
        "2131141038", #CS
        "2150981488", #CSCX
        "2131141039", #RC
        }:
            if number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
               number_type not in EMERGENCY_NUMBERS.values() and \
               number_type not in INTERNATIONAL_PHONE_PREFIXES.values():
                return self.calculate_per_minute_charge(600)

        # Rate 900
        if str(self.call_from) in {
            "2023019",  # kclub
            "2023018",  # travelbook
            "81197800082",  # akasa
            "2023016", "2150981419", #madev
            "2023015", #moladin collection
            "81377177190", "22245", "22246", "22247", "22248", "22249", #upperwest
        }:
            if number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
               number_type not in EMERGENCY_NUMBERS.values() and \
               number_type not in INTERNATIONAL_PHONE_PREFIXES.values():
                return self.calculate_per_minute_charge(900)

        # Paragon
        if str(self.call_from) == "50913440" or str(self.call_to) == "50913440": 
            if number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
               number_type not in EMERGENCY_NUMBERS.values() and \
               number_type not in INTERNATIONAL_PHONE_PREFIXES.values(): 
                return self.calculate_per_minute_charge(1450)
            elif number_type == "Answering machine" and str(str.self.call_to) == "50913440":
                return self.calculate_per_minute_charge(1450)

        # Inbound outbound for Naluri / Benings
        if str(self.call_from) in {"2150981400", "8001503377", "2150981455", "2150913442"}:
            if number_type not in {"Premium Call", "Toll-Free", "Split Charge"} and \
               number_type not in EMERGENCY_NUMBERS.values() and \
               number_type not in INTERNATIONAL_PHONE_PREFIXES.values():
                return self.calculate_per_minute_charge(1500)
        # Siemens(440)
        elif str(self.call_to) in {"2150981400", "8001503377", "2150981455", "2150913442", "2150981440"}:
            # For call_to, no need to check number_type, always calculate
            return self.calculate_per_minute_charge(1500)
        elif number_type == "Asnwering machine" and self.(call_to) in {"2150981400", "8001503377", "2150981455", "2150913442", "2150981440"}:
            return self.calculate_per_minute_charge(1500)

        # International and premium number handling
        if number_type in ["Premium Call", "Toll-Free", "Split Charge"] or number_type in EMERGENCY_NUMBERS.values():
            return self.calculate_per_minute_charge(1700)

        rate_map = INTERNATIONAL_RATES.get(self.carrier, {})

        if number_type in rate_map:
            return self.calculate_per_minute_charge(rate_map[number_type])

        # Default charge
        return self.calculate_per_minute_charge(720)

    def to_dict(self) -> dict:
        return {
            "Sequence ID": self.sequence_id,
            "User name": format_username(self.user_name),
            "Call from": self.call_from,
            "Call to": self.call_to,
            "Call type": self.call_type,
            "Number type": classify_number(self.call_to, self.call_type, self.call_from, self.call_to),
            "Dial starts at": format_datetime_as_human_readable(self.dial_start_at),
            "Dial answered at": format_datetime_as_human_readable(
                self.dial_answered_at
            ),
            "Dial ends at": format_datetime_as_human_readable(self.dial_end_at),
            "Ringing time": format_timedelta(self.ringing_time),
            "Call duration": format_timedelta(self.call_duration),
            "Call memo": self.call_memo,
            "Call charge": self.call_charge,
        }

    def hash_key(self) -> str:
        return call_hash(self.call_from, self.call_to, self.dial_start_at)