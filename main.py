import os

# from cleaners.paranoid_cleaner import remove_messages_paranoid
# from cleaners.simple_cleaner import remove_messages_simple

from cleaners.paranoid_ban_words_cleaner import remove_messages_paranoid
from cleaners.simple_ban_words_cleaner import remove_messages_simple


def main():
    folder_path = "dirty_logs/"
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            full_path = os.path.join(folder_path, filename)

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except:
                continue

            if any("body:" in line.lower() for line in lines):
                try:
                    remove_messages_paranoid(full_path)
                except:
                    pass

            if any("snippet:" in line.lower() for line in lines):
                try:
                    remove_messages_simple(full_path)
                except:
                    pass


if __name__ == "__main__":
    main()
