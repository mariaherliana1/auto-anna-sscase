from config import CONFIG
from src.csv_processing import (
    process_console_csv,
    process_dashboard_csv,
    save_merged_csv,
)


def __main__():
    print(f"Starting Auto-Anna CSV merger")
    for files in CONFIG:
        print(f"> Merging files for client {files.client}")
        call_details = process_dashboard_csv(files.dashboard, files.carrier)
        call_details = process_console_csv(files.console, files.carrier, call_details)
        save_merged_csv(call_details, files.output)
    print("All files merged successfully")


__main__()
