#!/usr/bin/env bash
set -euo pipefail
: "${API_BASE_URL:?Set the HTTPS backend URL}"
: "${SUPABASE_URL:?Set the public Supabase URL}"
: "${SUPABASE_ANON_KEY:?Set the public publishable/anon key}"
if [[ "$API_BASE_URL" != https://* ]]; then
  echo "Production API_BASE_URL must use HTTPS" >&2
  exit 1
fi
if ! command -v flutter >/dev/null 2>&1; then
  git clone --depth 1 --branch 3.44.1 https://github.com/flutter/flutter.git /tmp/neoguard-flutter
  export PATH="/tmp/neoguard-flutter/bin:$PATH"
fi
flutter config --no-analytics
flutter pub get --enforce-lockfile
flutter build web --release --no-web-resources-cdn \
  --dart-define="API_BASE_URL=$API_BASE_URL" \
  --dart-define="SUPABASE_URL=$SUPABASE_URL" \
  --dart-define="SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY"
if find build/web -type f -name '.env*' | grep -q .; then
  echo "Unexpected environment asset in web build" >&2
  exit 1
fi
