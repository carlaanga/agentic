#!/usr/bin/env bash
# Pre-vuelo: ejecutar ANTES del taller, con buena conexión. Descarga todo.
set -e
cd "$(dirname "$0")/.."
MODELO="${MODELO:-$(grep -s '^MODELO=' .env | cut -d= -f2)}"
MODELO="${MODELO:-qwen3:4b}"

echo "1/4 Comprobando Docker..."
docker compose version >/dev/null || { echo "Falta Docker Compose. Instala Docker Desktop: https://docs.docker.com/get-docker/"; exit 1; }

echo "2/4 Descargando imágenes (Open WebUI)..."
docker compose pull open-webui

echo "3/4 Construyendo el servidor de herramientas y el agente..."
docker compose --profile cli build

echo "4/4 Descargando el modelo $MODELO (esto es lo lento: 2-5 GB)..."
# Reutiliza un contenedor de Ollama ya existente; crea uno solo si no hay.
if [ -z "$(docker ps -q -f name=^ollama$)" ]; then
  if [ -n "$(docker ps -aq -f name=^ollama$)" ]; then
    docker start ollama
  else
    docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama \
      --restart unless-stopped ollama/ollama:latest
  fi
fi
docker exec ollama ollama pull "$MODELO"

echo
echo "Listo. El día del taller solo hace falta:  docker compose up -d"
echo "Chat:         http://localhost:3000"
echo "Herramientas: http://localhost:8030/docs"
