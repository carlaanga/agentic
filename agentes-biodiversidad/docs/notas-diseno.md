# Notas de diseño

## Por qué estas piezas

- **Ollama** porque es la forma más simple de servir un modelo abierto en local, en los tres
  sistemas operativos, y expone una API de chat con herramientas.
- **Open WebUI** porque da la experiencia "chat" que la gente espera, con soporte de servidores
  de herramientas OpenAPI. Es la parte que más cambia entre versiones; por eso el README tiene
  el registro manual como plan B.
- **Un servidor de herramientas propio (FastAPI)** en lugar de un plugin dentro de la interfaz,
  porque así el contrato es un archivo Python que se puede leer, versionar y reutilizar desde
  cualquier otro cliente (el agente CLI, un notebook, otra institución).
- **Un agente CLI sin frameworks** porque el objetivo pedagógico es ver el bucle. LangChain,
  CrewAI y similares son útiles después, cuando ya se entiende qué esconden.

## Por qué un modelo pequeño

`qwen3:4b` corre en CPU con 8 GB de RAM. Su llamada a herramientas no es perfecta, y eso es
deliberado: los fallos aparecen en la traza y dan material para el ejercicio de evaluación.
Con 16 GB o GPU, `qwen3:8b` es notablemente más fiable. Verifica las etiquetas exactas de los
modelos en <https://ollama.com/library> antes de enviar el pre-vuelo: cambian cada pocos meses.

## Seguridad y datos

- Nada sale de la máquina salvo las consultas a `api.gbif.org`, que son datos abiertos.
- `WEBUI_AUTH=false` es aceptable en un portátil personal; no expongas los puertos en una red
  compartida sin activar autenticación.
- Si se sustituye GBIF por una API institucional con datos sensibles (localidades de especies
  amenazadas), el mismo diseño aplica: el modelo solo ve lo que la herramienta decide devolver.
  La herramienta es el punto de control, no el modelo.
- Inyección de prompt: cualquier texto que el modelo lea (resultados de herramientas, documentos)
  puede contener instrucciones. En este playground los resultados vienen de GBIF; al conectar
  literatura o páginas web, tratar el contenido como datos, nunca como órdenes.

## Cómo extenderlo

1. Añadir una función a `herramientas/app.py` con `operation_id`, `summary` y docstring claros.
2. `docker compose up -d --build gbif-tools`.
3. Nada más: el agente CLI relee `/openapi.json` en cada ejecución y Open WebUI al recargar.
