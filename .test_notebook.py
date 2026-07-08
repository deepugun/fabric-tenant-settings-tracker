import json, ast, sys, types

NB = "Tenant_Settings_Change_Tracker.ipynb"
nb = json.load(open(NB, encoding="utf-8"))
code_cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"]

# ---------------------------------------------------------------------------
# TEST 1 — Syntax check every code cell
# ---------------------------------------------------------------------------
print("=== TEST 1: Syntax validation of all code cells ===")
syntax_ok = True
for i, src in code_cells:
    try:
        ast.parse(src)
        print(f"  Cell index {i:>2}: OK ({len(src.splitlines())} lines)")
    except SyntaxError as e:
        syntax_ok = False
        print(f"  Cell index {i:>2}: SYNTAX ERROR -> {e}")
print("Result:", "PASS" if syntax_ok else "FAIL")

# ---------------------------------------------------------------------------
# TEST 2 — Mock-execute the service-principal auth block from Cell 2
#          (fake mssparkutils + fake requests) to prove the token flow works
# ---------------------------------------------------------------------------
print("\n=== TEST 2: Service-principal auth flow (mocked) ===")

captured = {}

class FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
    def json(self):
        return self._payload

class FakeRequests:
    def post(self, url, data=None, **kw):
        captured["post_url"] = url
        captured["post_data"] = data
        return FakeResp({"access_token": "FAKE.SP.TOKEN"})
    def get(self, url, headers=None, **kw):
        captured["get_url"] = url
        captured["get_headers"] = headers
        return FakeResp({"tenantSettings": [{"settingName": "A"}, {"settingName": "B"}]})

class FakeCreds:
    def getSecret(self, vault, name):
        captured["kv"] = (vault, name)
        return "FAKE-CLIENT-SECRET"

fake_msu = types.SimpleNamespace(credentials=FakeCreds())

# Config values that Cell 1 would normally define
g = {
    "TENANT_ID": "11111111-1111-1111-1111-111111111111",
    "CLIENT_ID": "22222222-2222-2222-2222-222222222222",
    "KEY_VAULT_URL": "https://demo.vault.azure.net/",
    "SECRET_NAME": "sp-secret",
    "requests": FakeRequests(),
    "mssparkutils": fake_msu,
}

# Extract Cell 2 source and strip the import lines (we inject fakes instead)
cell2_src = next(src for i, src in code_cells if "client_credentials" in src)
lines = [ln for ln in cell2_src.splitlines()
         if not ln.strip().startswith(("import ", "from "))]
exec("\n".join(lines), g)

ok = True
def check(name, cond):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    ok = ok and cond

check("Secret pulled from Key Vault (url, name)", captured.get("kv") == ("https://demo.vault.azure.net/", "sp-secret"))
check("Token endpoint = tenant-scoped v2.0", captured.get("post_url") == "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/oauth2/v2.0/token")
check("grant_type = client_credentials", captured.get("post_data", {}).get("grant_type") == "client_credentials")
check("client_id passed", captured.get("post_data", {}).get("client_id") == "22222222-2222-2222-2222-222222222222")
check("client_secret from KV used", captured.get("post_data", {}).get("client_secret") == "FAKE-CLIENT-SECRET")
check("scope = fabric .default", captured.get("post_data", {}).get("scope") == "https://api.fabric.microsoft.com/.default")
check("token variable set from response", g.get("token") == "FAKE.SP.TOKEN")
check("Admin API called with Bearer SP token", captured.get("get_headers") == {"Authorization": "Bearer FAKE.SP.TOKEN"})
check("Admin API URL correct", captured.get("get_url") == "https://api.fabric.microsoft.com/v1/admin/tenantsettings")
check("raw_settings parsed", g.get("raw_settings") == [{"settingName": "A"}, {"settingName": "B"}])

print("Result:", "PASS" if ok else "FAIL")
print("\nOVERALL:", "PASS" if (syntax_ok and ok) else "FAIL")
sys.exit(0 if (syntax_ok and ok) else 1)
