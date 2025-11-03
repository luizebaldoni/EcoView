# PowerShell script to run migrations for default, brise and pavimentos
if (-not $env:DJANGO_SETTINGS_MODULE) { $env:DJANGO_SETTINGS_MODULE = 'config.settings' }

Write-Host "Running migrations for default DB"
python manage.py migrate --database=default

# Check via python -c whether the aliases exist in settings.DATABASES
$hasBrise = python -c "from django.conf import settings; import json; print('brise' in settings.DATABASES)" 2>$null
if ($hasBrise -and $hasBrise.Trim().ToLower() -eq 'true') {
    Write-Host "Running migrations for brise"
    python manage.py migrate --database=brise
} else {
    Write-Host "No 'brise' database configured; skipping"
}

$hasPav = python -c "from django.conf import settings; import json; print('pavimentos' in settings.DATABASES)" 2>$null
if ($hasPav -and $hasPav.Trim().ToLower() -eq 'true') {
    Write-Host "Running migrations for pavimentos"
    python manage.py migrate --database=pavimentos
} else {
    Write-Host "No 'pavimentos' database configured; skipping"
}