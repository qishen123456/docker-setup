import os

file_path = r'c:\Users\LTQ\Desktop\智能问数项目_v20260330_004926(1)\1111\智能问数项目_v20260330_004926\智能问数项目_v20260330_004926\frontend\src\views\SmartAsk.vue'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check if it's a diff
if lines[0].startswith('diff --git'):
    cleaned_lines = []
    # Skip diff headers (usually 5 lines)
    start_index = 0
    for i, line in enumerate(lines):
        if line.startswith('@@'):
            start_index = i + 1
            break
    
    for line in lines[start_index:]:
        if line.startswith('+'):
            cleaned_lines.append(line[1:])
        elif line.startswith('-'):
            continue # Skip deletions
        else:
            cleaned_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    print("File cleaned successfully.")
else:
    print("File does not appear to be a diff. No action taken.")
