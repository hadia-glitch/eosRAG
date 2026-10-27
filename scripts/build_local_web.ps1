$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$publicConfig = @{}
Get-Content -LiteralPath (Join-Path $projectRoot '.env') | ForEach-Object {
  if ($_ -match '^(API_BASE_URL|SUPABASE_URL|SUPABASE_ANON_KEY)=(.*)$') {
    $publicConfig[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
  }
}
$localApi = $publicConfig['API_BASE_URL']
if (-not $localApi) { $localApi = 'http://127.0.0.1:8000' }
& (Join-Path $PSScriptRoot 'build_web.ps1') -ApiBaseUrl $localApi -SupabaseUrl $publicConfig['SUPABASE_URL'] -SupabaseAnonKey $publicConfig['SUPABASE_ANON_KEY'] -SkipPubGet -LocalPreview
