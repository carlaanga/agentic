# Pre-vuelo (Windows PowerShell): ejecutar ANTES del taller, con buena conexión.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Modelo = $env:MODELO
if (-not $Modelo -and (Test-Path .env)) { $Modelo = (Select-String '^MODELO=' .env).Line.Split('=')[1] }
if (-not $Modelo) { $Modelo = "qwen3:4b" }

Write-Host "1/4 Comprobando Docker..."
docker compose version | Out-Null
Write-Host "2/4 Descargando imágenes..."
docker compose pull open-webui
Write-Host "3/4 Construyendo el servidor de herramientas y el agente..."
docker compose --profile cli build
Write-Host "4/4 Descargando el modelo $Modelo (2-5 GB)..."
# Reutiliza un contenedor de Ollama ya existente; crea uno solo si no hay.
$corriendo = docker ps -q -f "name=^ollama$"
if (-not $corriendo) {
    $existe = docker ps -aq -f "name=^ollama$"
    if ($existe) { docker start ollama | Out-Null }
    else {
        docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama `
            --restart unless-stopped ollama/ollama:latest | Out-Null
    }
}
docker exec ollama ollama pull $Modelo
Write-Host ""
Write-Host "Listo. El día del taller:  docker compose up -d"
Write-Host "Chat: http://localhost:3000   Herramientas: http://localhost:8030/docs"
