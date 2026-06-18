import json

path = r'c:\Users\kgundavaram\fabric-tenant-settings-tracker\Tenant_Settings_Change_Tracker.ipynb'
with open(path, encoding='utf-8') as f:
    nb = json.load(f)

cw = nb['cells'][5]['source']
new_lines = []
seen_stub_comment = False

for i, line in enumerate(cw):
    # Fix 1: add ws_prev_date = None after ws_prop_changes = []
    if line == 'ws_prop_changes = []\n':
        new_lines.append(line)
        new_lines.append('ws_prev_date = None   # set inside try block; init here so downstream cells never NameError\n')
        continue

    # Fix 2: remove duplicate stub block (second occurrence)
    if "stub out temp views" in line.lower() and seen_stub_comment:
        # Skip this and the next 14 lines (duplicate block)
        dup_count = 0
        j = i
        while j < len(cw) and dup_count < 15:
            j += 1
            dup_count += 1
        # We'll skip by tracking how many to drop
        new_lines.append('    # (duplicate stub block removed)\n')
        # Actually, just skip silently by not appending
        new_lines.pop()  # remove the placeholder
        # Mark to skip
        nb['_skip_until'] = j
        continue

    if '_skip_until' in nb and i < nb['_skip_until']:
        continue

    if "stub out temp views" in line.lower():
        seen_stub_comment = True

    new_lines.append(line)

if '_skip_until' in nb:
    del nb['_skip_until']

nb['cells'][5]['source'] = new_lines
with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

nb2 = json.load(open(path, encoding='utf-8'))
cw2 = nb2['cells'][5]['source']
stub_count = sum(1 for l in cw2 if "stub out temp views" in l.lower())
has_ws_prev = any('ws_prev_date = None' in l for l in cw2)
print(f"Cell W: {len(cw2)} lines | ws_prev_date init: {has_ws_prev} | stub comment count: {stub_count}")
# Show init block
for i in range(7,14): print(f"  L{i+1}: {cw2[i].rstrip()}")
