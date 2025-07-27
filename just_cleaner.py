import os
import chardet

from cleaners.paranoid_ban_words_cleaner import remove_messages_paranoid
from cleaners.simple_ban_words_cleaner import remove_messages_simple


def save_result(file_balance, full_path):
    with open("result.txt", "a", encoding="utf-8") as f:
        str_file_balance = str(file_balance).replace("-", "")
        f.write(f"{str_file_balance} | {full_path}\n")


def main():
    folder_path = "dirty_logs/"
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.endswith(".txt"):
                full_path = os.path.join(root, filename)

                try:
                    with open(full_path, "rb") as raw_f:
                        raw_data = raw_f.read()
                        detected = chardet.detect(raw_data)
                        encoding = detected["encoding"] or "utf-8"
                        text = raw_data.decode(encoding, errors="replace")

                    lines = text.splitlines()
                    lines = [
                        line
                        for line in lines
                        if not (
                            (
                                ("/\tTRUE" in line or "/\tFALSE" in line)
                                and len(line) > 50
                            )
                            or ".google.com" in line
                            or "mail.google.com" in line
                        )
                    ]
                    text = "\n".join(lines)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(text)

                    lines = text.splitlines()

                except Exception as ex:
                    print(f"Error while reading file: {full_path}: {ex}")
                    continue

                if any("body:" in line.lower() for line in lines):
                    try:
                        remove_messages_paranoid(full_path)

                    except Exception as ex:
                        print(f"Error while proccessing body: {full_path}: {ex}")
                        continue
                if any("snippet:" in line.lower() for line in lines):
                    try:
                        remove_messages_simple(full_path)

                    except Exception as ex:
                        print(f"Error while proccessing snippet: {full_path}: {ex}")
                        continue


if __name__ == "__main__":
    main()
