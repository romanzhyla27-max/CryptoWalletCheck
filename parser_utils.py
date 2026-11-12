import re
import csv


def extract_valid_wallets(manual_text: str, file_path: str | None) -> list[str]:
    """Extracts and validates unique EVM wallet addresses from text input and a .txt file."""
    raw_content = manual_text or ""

    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content += "\n" + f.read()

    # Regex to find all standard 42-character EVM addresses (0x + 40 hex chars)
    found_addresses = re.findall(r"0x[a-fA-F0-9]{40}", raw_content)

    # Remove duplicates while preserving original order
    unique_wallets = list(dict.fromkeys(found_addresses))
    return unique_wallets


def export_rows_to_csv(file_path: str, rows: list[tuple]) -> None:
    """Exports table rows into a CSV file."""
    headers = ["Wallet Address", "Network", "Native Balance", "Tokens (USD)", "Total (USD)"]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)