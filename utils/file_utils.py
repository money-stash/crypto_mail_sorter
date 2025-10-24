from config import BODIES


def add_ban_word(text):
    with open(BODIES, "a+") as f:
        f.write(f"\n{text}")


def remove_messages_by_snippet_match_simple(file_path: str, target_snippet: list):
    for text in target_snippet:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        blocks = []
        current_block = []

        for line in lines:
            if line.startswith("From:") and current_block:
                blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)

        filtered_blocks = []
        for block in blocks:
            snippet_lines = [line for line in block if line.startswith("Snippet:")]
            if any(text.strip() in line for line in snippet_lines):
                continue
            filtered_blocks.append(block)

        with open(file_path, "w", encoding="utf-8") as f:
            cleaned_blocks = ["".join(block).rstrip("\n") for block in filtered_blocks]
            f.write("\n\n".join(cleaned_blocks) + "\n")


def remove_messages_by_snippet_match_paranoid(file_path: str, target_snippet: list):
    for text in target_snippet:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        blocks = []
        current_block = []

        for line in lines:
            if line.startswith("Title:") and current_block:
                blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)

        filtered_blocks = []
        for block in blocks:
            body_lines = [line for line in block if line.startswith("Body:")]
            if any(text.strip() in line for line in body_lines):
                continue
            filtered_blocks.append(block)

        with open(file_path, "w", encoding="utf-8") as f:
            cleaned_blocks = ["".join(block).rstrip("\n") for block in filtered_blocks]
            f.write("\n\n".join(cleaned_blocks) + "\n")


def is_mails_archive(filename: str) -> bool:
    filename_lower = filename.lower()
    return "-mails" in filename_lower


def is_logs_archive(filename: str) -> bool:
    filename_lower = filename.lower()
    return "-logs" in filename_lower
