# Placement: infrastructure/postgres/restore_supabase_backup.ps1
# Restores a Supabase "db_cluster-*.backup.gz" into the local Docker PostgreSQL.
# Creates the mahara-postgres container (pgvector, PostgreSQL 17, port 5434) if it is missing.
# It never overwrites an existing database: pick a new -Database name to restore again.
#
#   powershell -ExecutionPolicy Bypass -File infrastructure\postgres\restore_supabase_backup.ps1 `
#       -BackupPath "$HOME\Downloads\db_cluster-29-10-2026@13-39-03.backup.gz"

param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [string]$Database = "mahara_match_backup",
    [string]$Container = "mahara-postgres",
    [int]$Port = 5434
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BackupPath)) { throw "Backup not found: $BackupPath" }
docker info --format "{{.ServerVersion}}" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker is not running. Start Docker Desktop first." }

docker inspect $Container 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating container $Container on port $Port..."
    docker run -d --name $Container --restart unless-stopped `
        -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mahara_match `
        -p "${Port}:5432" -v mahara_pgdata:/var/lib/postgresql/data pgvector/pgvector:pg17 | Out-Null
} else {
    docker start $Container | Out-Null
}
for ($i = 0; $i -lt 30; $i++) {
    docker exec $Container pg_isready -U postgres 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}
# The scratch database used by tests needs pgvector too.
docker exec $Container psql -U postgres -d mahara_match -qc "CREATE EXTENSION IF NOT EXISTS vector;"

$sql = Join-Path ([System.IO.Path]::GetTempPath()) "mahara_cluster_dump.sql"
Write-Host "Decompressing backup..."
$in = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $BackupPath))
$gzip = New-Object System.IO.Compression.GZipStream($in, [System.IO.Compression.CompressionMode]::Decompress)
$out = [System.IO.File]::Create($sql)
try { $gzip.CopyTo($out) } finally { $out.Dispose(); $gzip.Dispose(); $in.Dispose() }

try {
    docker cp $sql "${Container}:/tmp/cluster.sql"
    docker cp (Join-Path $PSScriptRoot "restore_inside.sh") "${Container}:/tmp/restore_inside.sh"
    docker exec $Container sh /tmp/restore_inside.sh /tmp/cluster.sql $Database
    if ($LASTEXITCODE -ne 0) { throw "Restore failed (see the message above)." }
} finally {
    docker exec $Container rm -f /tmp/cluster.sql /tmp/restore_inside.sh 2>$null | Out-Null
    Remove-Item -LiteralPath $sql -ErrorAction SilentlyContinue
}
Write-Host "Done. DATABASE_URL=postgresql://postgres:postgres@localhost:$Port/${Database}?sslmode=disable"
