import os

# from cleaners.paranoid_cleaner import remove_messages_paranoid
# from cleaners.simple_cleaner import remove_messages_simple

from cleaners.paranoid_ban_words_cleaner import remove_messages_paranoid
from cleaners.simple_ban_words_cleaner import remove_messages_simple
from text_utils import process_withdrawals_from_file


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
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except:
                continue

            if any("body:" in line.lower() for line in lines):
                try:
                    remove_messages_paranoid(full_path)
                    file_balance = process_withdrawals_from_file(
                        file_path=full_path, checker_name="paranoid"
                    )
                    if file_balance == None:
                        continue
                    save_result(file_balance, full_path)

                except:
                    pass

            if any("snippet:" in line.lower() for line in lines):
                try:
                    remove_messages_simple(full_path)
                    file_balance = process_withdrawals_from_file(
                        file_path=full_path, checker_name="simple"
                    )
                    if file_balance == None:
                        continue
                    save_result(file_balance, full_path)

                except:
                    pass


if __name__ == "__main__":
    main()
