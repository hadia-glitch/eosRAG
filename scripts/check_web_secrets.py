"""Verify build outputs without printing any configured credential values."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
build = root/'build/web'
sys.path.insert(0, str(root/'backend'))
from config import get_settings

if not (build/'main.dart.js').exists():
    raise SystemExit('No compiled web build found')
files = [p for p in build.rglob('*') if p.is_file()]
if any(p.name.startswith('.env') for p in files):
    raise SystemExit('Environment file found in web output')
settings = get_settings()
secrets = [settings.groq_api_key, settings.supabase_service_key, settings.gemini_api_key]
found = False
for p in files:
    data = p.read_bytes()
    if any(value and len(value)>8 and value.encode() in data for value in secrets):
        found = True
if found:
    raise SystemExit('Configured server credential found in web output')
print({'environment_assets': 0, 'configured_server_credentials_found': False, 'files_checked': len(files)})
