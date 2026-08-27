def run_length_encode(s):
    """문자열을 'a3b2' 같은 (문자+반복횟수) 시퀀스 문자열로 압축한다."""
    if not s:
        return ""
    
    encoded = []
    current_char = s[0]
    count = 0
    
    for char in s:
        if char == current_char:
            count += 1
        else:
            encoded.append(f"{current_char}{count}")
            current_char = char
            count = 1
    encoded.append(f"{current_char}{count}")
    return "".join(encoded)


def run_length_decode(s):
    """run_length_encode가 만든 문자열을 원래 문자열로 복원한다."""
    if not s:
        return ""
    
    decoded = []
    i = 0
    n = len(s)
    
    while i < n:
        char = s[i]
        i += 1
        j = i
        while j < n and s[j].isdigit():
            j += 1
        count = int(s[i:j])
        decoded.append(char * count)
        i = j
        
    return "".join(decoded)
