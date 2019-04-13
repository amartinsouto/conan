import re

MD5_LENGTH=32

def is_md5sum(value):
    if len(value) is not MD5_LENGTH:
        return False
    md5 = re.findall(r"([a-fA-F\d]{32})", value)
    if len(md5) is 1:
        return True
    else:
        return False
