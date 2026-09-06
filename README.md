# Agentes de IA para informática de la biodiversidad — playground local

Un agente de IA es **un modelo + herramientas + un bucle + un criterio de parada**.
Este repositorio te deja uno funcionando en tu máquina, con Docker, en unos minutos,
y con una herramienta que ya conoces: la API de GBIF.

Todo corre en tu computador. Ningún dato sale de él.

```
  pregunta ──▶ ┌────────┐  ¿necesito una herramienta?  ┌──────────────┐
               │ MODELO │ ───────────────────────────▶ │ gbif-tools   │ ──▶ api.gbif.org
               │(ollama)│ ◀─────────────────────────── │ (contratos)  │
               └────────┘        resultado             └──────────────┘
                   │  repite hasta poder responder
                   ▼
             respuesta + TRAZA (qué llamó, con qué argumentos, qué recibió)
```

## Antes del taller: pre-vuelo (10-20 min con buena conexión)

Lo único lento es descargar el modelo (2-5 GB). Hazlo en casa o en la oficina, no en la sala.

1. Instala **Docker Desktop** (Windows, macOS) o Docker Engine + Compose (Linux):
   <https://docs.docker.com/get-docker/>. En Windows acepta activar WSL 2 si lo pide.
2. Descarga este repositorio (botón *Code → Download ZIP*, o `git clone`).
3. Abre una terminal en la carpeta y ejecuta:

   ```bash
   ./scripts/prevuelo.sh          # macOS / Linux
   .\scripts\prevuelo.ps1         # Windows PowerShell
   ```

   Si prefieres hacerlo a mano:

   ```bash
   docker compose pull open-webui
   docker compose --profile cli build
   # Ollama corre como contenedor aparte; si ya tienes uno llamado "ollama", sáltate el docker run
   docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama \
     --restart unless-stopped ollama/ollama:latest
   docker exec ollama ollama pull qwen3:4b
   ```

Requisitos mínimos: 8 GB de RAM y ~8 GB de disco libre. No hace falta GPU;
en CPU el modelo tarda entre 10 y 60 segundos por respuesta, lo cual es
perfecto para *leer la traza* con calma.

## El día del taller: arrancar (1 min)

```bash
docker compose up -d
```

Abre <http://localhost:3000>. Verás una interfaz de chat. Elige el modelo `qwen3:4b`
(arriba a la izquierda) y activa la herramienta **Herramientas GBIF** con el botón `+`
o el ícono de herramientas junto al campo de texto.

Prueba:

> ¿Cuántos registros de *Puma concolor* hay en Chile desde 2020?

Deberías ver que el modelo llama a `resolver_nombre`, luego a `contar_ocurrencias`,
y responde con una cifra y la URL de la consulta. Cambia la especie y el país por
los tuyos.

### Si la herramienta no aparece en el chat

Las versiones de Open WebUI cambian rápido. Regístrala a mano una vez:

1. Ícono de usuario (abajo a la izquierda) → **Panel de administración** → **Ajustes** → **Herramientas**.
2. **+ Añadir conexión** con URL `http://gbif-tools:8000` (así la llama el servidor de Open WebUI
   dentro de Docker: 8000 es el puerto interno del contenedor). Si la registras como herramienta
   *de usuario* en lugar de *global*, la llama tu navegador y la URL debe ser `http://localhost:8030`.
3. Guarda, y en el chat activa la herramienta con el botón `+`.

Si el modelo responde sin usar herramientas, en el chat abre *Controles* (ícono a la derecha)
→ *Parámetros avanzados* → **Function Calling** y prueba `Native` (usa el soporte nativo del
modelo) o `Default` (lo hace por prompt; funciona con cualquier modelo).

## Ver el agente por dentro: la traza

La interfaz de chat esconde el mecanismo. Para verlo entero usa el agente de línea de comandos,
que son 120 líneas de Python en [`agente/agente.py`](agente/agente.py):

```bash
docker compose run --rm agente "¿Cuántos registros de Puma concolor hay en Chile desde 2020?"
```

Salida (cifras ilustrativas: GBIF crece todos los días, la tuya será distinta):

```
[0] PREGUNTA
    ¿Cuántos registros de Puma concolor hay en Chile desde 2020?

[0] HERRAMIENTAS DISPONIBLES
    resolver_nombre, contar_ocurrencias, buscar_ocurrencias

[1] EL MODELO LLAMA A → resolver_nombre
    {"nombre": "Puma concolor"}

[1] RESULTADO DE ← resolver_nombre
    {"usageKey": 2435099, "scientificName": "Puma concolor (Linnaeus, 1771)",
     "rank": "SPECIES", "status": "ACCEPTED", "confidence": 99, "matchType": "EXACT", ...}

[2] EL MODELO LLAMA A → contar_ocurrencias
    {"taxonKey": 2435099, "pais": "CL", "anio": "2020,2026"}

[2] RESULTADO DE ← contar_ocurrencias
    {"taxonKey": 2435099, "pais": "CL", "anio": "2020,2026", "total": 1234,
     "consulta": "https://api.gbif.org/v1/occurrence/count?taxonKey=2435099&country=CL&year=2020%2C2026"}

[3] RESPUESTA FINAL
    GBIF registra 1234 ocurrencias de Puma concolor en Chile entre 2020 y 2026.
    Fuente: https://api.gbif.org/v1/occurrence/count?taxonKey=2435099&country=CL&year=2020%2C2026
```

Cada línea de la traza responde a una pregunta que ayer quedó abierta:
*¿qué condiciones mínimas permiten confiar en un resultado producido con agentes?*
Puedes confiar en lo que puedes leer y reproducir. La URL de la consulta se puede pegar
en el navegador y verificar.

## Una herramienta es un contrato

Abre <http://localhost:8030/docs>. Es la documentación automática del servidor de herramientas,
y es **exactamente lo que el modelo lee** para decidir qué llamar. Mira la descripción de
`resolver_nombre`: le dice al modelo *cuándo* usarla ("siempre antes de contar"), *qué* pasarle
("nombre científico, no común") y *qué hacer si falla* ("si matchType es NONE, dilo").

Todo eso está en [`herramientas/app.py`](herramientas/app.py) como docstrings y `description=`.
Escribir bien ese texto es una competencia nueva, y se apoya en dos que ya tienen:
diseño de APIs y estándares de datos (Darwin Core).

## Ejercicios (para la mesa redonda o para la próxima semana)

1. **Leer la traza.** Pregunta por una especie con nombre ambiguo o mal escrito
   (`Nothofagus obliqua` vs `Nothofagus oblicua`). ¿Detectas en la traza el `matchType: FUZZY`?
   ¿El modelo te lo avisó? Esto es una evaluación de competencia: quien lee la traza y
   detecta el problema, domina algo que quien solo lee la respuesta no.
2. **Romper el agente.** Pregunta por un nombre común ("puma", "zorro culpeo"). ¿Qué hace?
   ¿Qué cambiarías en la descripción de la herramienta para que se comporte mejor?
   Cámbialo en `app.py`, ejecuta `docker compose up -d --build gbif-tools` y vuelve a probar.
3. **Agregar una herramienta.** Copia `contar_ocurrencias` y crea `contar_por_pais`
   que devuelva el conteo por país para un taxón (`/occurrence/counts/countries?taxonKey=`).
   Reconstruye. El agente la descubre solo: el contrato es la interfaz.
4. **Cambiar el modelo.** Copia `.env.example` a `.env`, pon `MODELO=llama3.2:3b`,
   descarga (`docker exec ollama ollama pull llama3.2:3b`) y repite el ejercicio 1.
   ¿Cambia la fiabilidad de las llamadas? Eso es evaluación de agentes en miniatura.
5. **Discutir.** ¿Qué tarea de tu trabajo tiene la forma "repetitiva, verificable, alto volumen"?
   ¿Qué herramienta tendrías que exponer para que un agente la hiciera? ¿Quién revisa?

## ¿Y MCP?

El servidor de herramientas habla OpenAPI, que es lo que Open WebUI y el agente CLI entienden.
**MCP** (Model Context Protocol) es el estándar abierto para exactamente el mismo contrato
(nombre, descripción, esquema de parámetros), con una ventaja: cualquier asistente que hable MCP
(Claude Desktop, Claude Code, y cada vez más clientes) descubre las herramientas solo, con
`tools/list`, sin configurar nada más. La competencia no cambia: escribir bien el contrato.
Cambia el enchufe. En el taller se muestra un ejemplo completo sobre GBIF y OBIS
(*Biodiversity Explorer*), con siete herramientas MCP y una web donde se arman tableros sin programar.

## Qué hay en el repositorio

| Ruta | Qué es |
|---|---|
| `docker-compose.yml` | Herramientas y chat (el modelo corre en un contenedor de Ollama aparte) y el agente CLI |
| `herramientas/app.py` | Servidor de herramientas GBIF: tres contratos con sus descripciones |
| `agente/agente.py` | Bucle de agente mínimo con traza, sin frameworks |
| `scripts/prevuelo.*` | Descarga todo antes del taller |
| `docs/` | Notas de diseño y solución de problemas |
| `herramientas/test_app.py` | Pruebas sin red de las funciones puras: `docker compose run --rm gbif-tools python -m unittest -v` |

## Solución de problemas

- **`docker compose` no existe**: en Linux instala el plugin `docker-compose-plugin`; en
  Windows/macOS reinstala Docker Desktop.
- **El modelo tarda mucho o la máquina se congela**: usa `llama3.2:3b` (más liviano) o cierra
  otras aplicaciones. Con menos de 8 GB de RAM es difícil.
- **`ollama pull` falla o se corta**: vuelve a ejecutarlo; reanuda la descarga.
- **El modelo inventa cifras en vez de usar herramientas**: comprueba que la herramienta está
  activada en el chat (botón `+`), prueba `Function Calling: Native`, o usa el agente CLI,
  que fuerza el uso de herramientas por diseño del prompt.
- **Windows: "WSL 2 no está instalado"**: `wsl --install` en PowerShell como administrador y reinicia.
- **Puerto ocupado (3000, 8030)**: cambia el número a la izquierda de los dos puntos en
  `docker-compose.yml` (por ejemplo `"3001:8080"`).
- **Puerto 11434 ocupado**: probablemente ya tienes Ollama corriendo (contenedor o app nativa);
  este compose lo reutiliza tal cual, no necesitas lanzar otro.

## Reutilizar esto en un curso

Este repositorio está pensado como módulo de curso, no solo como demo: el modelo corre sin conexión
una vez descargado (solo las consultas a `api.gbif.org` salen), en portátiles de estudiantes, con datos
del país de cada quien. Sustituir GBIF por
la API de la infraestructura propia (SiB Colombia, BIODATA, Biodiversidata) es cambiar un archivo.
Licencia MIT: úsenlo, adáptenlo, compártanlo entre institutos.
