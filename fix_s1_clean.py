import json

path = r'c:\Users\kgundavaram\fabric-tenant-settings-tracker\Tenant_Settings_Change_Tracker.ipynb'
with open(path, encoding='utf-8') as f:
    nb = json.load(f)

cw = nb['cells'][5]['source']

# Remove duplicate ws_prev_date = None lines - keep only first
seen_ws_prev = False
new_lines = []
for line in cw:
    if 'ws_prev_date = None' in line:
        if seen_ws_prev:
            continue  # skip duplicate
        seen_ws_prev = True
    new_lines.append(line)

# Also remove duplicate stub block - keep lines up to and including first v_net_prev assignment, remove second block
final_lines = []
stub_sql_count = 0
i = 0
while i < len(new_lines):
    line = new_lines[i]
    if 'CREATE OR REPLACE TEMP VIEW today_workspaces AS' in line:
        stub_sql_count += 1
        if stub_sql_count > 2:  # already have 2 (today_workspaces + today_net_policies), skip extras
            # skip this and next lines until closing """
            while i < len(new_lines) and '"""' not in new_lines[i] or new_lines[i].strip() == '"""':
                if new_lines[i].endswith('""")\n') or '"""' in new_lines[i]:
                    i += 1
                    break
                i += 1
            continue
    final_lines.append(line)
    i += 1

nb['cells'][5]['source'] = final_lines
with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

nb2 = json.load(open(path, encoding='utf-8'))
cw2 = nb2['cells'][5]['source']
ws_prev_count = sum(1 for l in cw2 if 'ws_prev_date = None' in l)
stub_count = sum(1 for l in cw2 if 'stub out' in l.lower())
print(f"Cell W: {len(cw2)} lines | ws_prev_date init lines: {ws_prev_count} | stub comment count: {stub_count}")
for i in range(7, 16): print(f"  L{i+1}: {cw2[i].rstrip()}")
