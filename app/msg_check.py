FILE = 'string_constants.py'


def check(string: str):
    if string.lower().strip() == "/cancel" or string.lower().strip() == "отмена":
        return 1
    with open(FILE, encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if line.find(string) != -1:
                f.close()
                return -1
        f.close()
        return 0
