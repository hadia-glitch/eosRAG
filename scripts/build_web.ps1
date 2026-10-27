param(
  [Parameter(Mandatory=$true)][string]$ApiBaseUrl,
  [Parameter(Mandatory=$true)][string]$SupabaseUrl,
  [Parameter(Mandatory=$true)][string]$SupabaseAnonKey,
  [switch]$SkipPubGet,
  [switch]$LocalPreview
)
$ErrorActionPreference = 'Stop'
$apiUri = [Uri]$ApiBaseUrl
$loopbackPreview = $LocalPreview -and $apiUri.Scheme -eq 'http' -and $apiUri.Host -in @('localhost', '127.0.0.1', '[::1]')
if ($apiUri.Scheme -ne 'https' -and -not $loopbackPreview) { throw 'Production API URL requires HTTPS; local preview may use loopback HTTP only' }
if (-not $SkipPubGet) {
  & flutter pub get --enforce-lockfile
  if ($LASTEXITCODE -ne 0) { throw 'Flutter dependency resolution failed' }
}
& flutter build web --release --no-pub --no-web-resources-cdn "--dart-define=API_BASE_URL=$ApiBaseUrl" "--dart-define=SUPABASE_URL=$SupabaseUrl" "--dart-define=SUPABASE_ANON_KEY=$SupabaseAnonKey"
if ($LASTEXITCODE -ne 0) { throw 'Flutter web build failed' }
$privateAssets = Get-ChildItem -LiteralPath 'build/web' -Recurse -Force -File | Where-Object { $_.Name -like '.env*' }
if ($privateAssets) { throw 'Unexpected environment asset in web build' }
