import json

path = r'c:\Users\kgundavaram\fabric-tenant-settings-tracker\Tenant_Settings_Change_Tracker.ipynb'
with open(path, encoding='utf-8') as f:
    nb = json.load(f)

cw = nb['cells'][5]['source']
new_lines = []
for line in cw:
    new_lines.append(line)
    if 'To enable, set WORKSPACE_DRIFT_ENABLED' in line:
        stub = [
            "    # Stub out temp views so downstream cells don't NameError on missing views\n",
            "    spark.sql(\"\"\"\n",
            "        CREATE OR REPLACE TEMP VIEW today_workspaces AS\n",
            "        SELECT '' AS snapshot_date, '' AS workspace_id, '' AS display_name,\n",
            "               '' AS ws_type, '' AS state, '' AS capacity_id,\n",
            "               '' AS default_storage_format, '' AS domain_id, '' AS tags\n",
            "        WHERE 1=0\"\"\")\n",
            "    spark.sql(\"\"\"\n",
            "        CREATE OR REPLACE TEMP VIEW today_net_policies AS\n",
            "        SELECT '' AS snapshot_date, '' AS workspace_id, '' AS inbound_public,\n",
            "               '' AS outbound_public, '' AS outbound_connections,\n",
            "               '' AS outbound_gateways, '' AS outbound_git\n",
            "        WHERE 1=0\"\"\")\n",
            "    spark.sql(\"CREATE OR REPLACE TEMP VIEW v_ws_prev  AS SELECT * FROM today_workspaces\")\n",
            "    spark.sql(\"CREATE OR REPLACE TEMP VIEW v_net_prev AS SELECT * FROM today_net_policies\")\n",
        ]
        new_lines.extend(stub)

nb['cells'][5]['source'] = new_lines
with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

nb2 = json.load(open(path, encoding='utf-8'))
cw2 = nb2['cells'][5]['source']
found = sum(1 for l in cw2 if "stub out" in l.lower() or "WHERE 1=0" in l)
print(f"Cell W: {len(cw2)} lines  |  stub view lines found: {found}")
