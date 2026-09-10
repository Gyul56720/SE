with open('novel/style.py', 'r') as f:
    lines = f.readlines()

with open('novel/style.py', 'w') as f:
    for line in lines:
        if line.startswith('ACTIVE = '):
            f.write('ACTIVE = "manga"\n')
        else:
            f.write(line)
