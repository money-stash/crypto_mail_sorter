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

            with open(full_path, "r") as f:
                line = f.readline()
                if "paranoid_checker" in line:
                    remove_messages_paranoid(full_path)
                elif "Simple Checker" in line:
                    remove_messages_simple(full_path)


if __name__ == "__main__":
    main()
