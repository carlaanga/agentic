"""
Un agente en 120 líneas: modelo + herramientas + bucle + criterio de parada.

No hay magia. El modelo recibe la pregunta y la lista de herramientas;
si decide llamar a una, nosotros la ejecutamos (una petición HTTP al servidor
de herramientas), le devolvemos el resultado y volvemos a preguntarle.
Se detiene cuando responde sin pedir herramientas o cuando agota los pasos.

Todo lo que pasa se imprime como TRAZA. Leer la traza es la competencia.

Uso:
    python agente.py "¿Cuántos registros de Puma concolor hay en Chile desde 2020?"
"""

import json
import os
import sys
import textwrap

import httpx

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
HERRAMIENTAS = os.environ.get("HERRAMIENTAS_URL", "http://localhost:8000")
MODELO = os.environ.get("MODELO", "qwen3:4b")
MAX_PASOS = int(os.environ.get("MAX_PASOS", "6"))

SISTEMA = textwrap.dedent("""
    Eres un asistente para informática de la biodiversidad. Respondes en español.
    Para cualquier dato sobre especies o registros usa las herramientas; nunca
    inventes cifras ni identificadores. Antes de contar o buscar registros
    resuelve el nombre con resolver_nombre y usa el usageKey que devuelve.
    Si la resolución tiene matchType NONE o confidence bajo, dilo.
    Al final cita la URL de consulta que devuelven las herramientas.
""").strip()


def cargar_herramientas() -> tuple[list[dict], dict]:
    """Lee /openapi.json del servidor y lo convierte al formato de herramientas del modelo.

    Así el contrato vive en UN solo lugar (herramientas/app.py) y lo mismo que ve
    Open WebUI es lo que ve este script.
    """
    spec = httpx.get(f"{HERRAMIENTAS}/openapi.json", timeout=10).json()
    tools, rutas = [], {}
    for ruta, metodos in spec["paths"].items():
        op = metodos.get("get")
        if not op:
            continue
        nombre = op["operationId"]
        props, requeridos = {}, []
        for p in op.get("parameters", []):
            esquema = {k: v for k, v in p["schema"].items() if k in ("type", "description", "enum")}
            # OpenAPI 3.1 escribe opcionales como anyOf [tipo, null]; simplificamos.
            if "type" not in esquema:
                for alt in p["schema"].get("anyOf", []):
                    if alt.get("type") != "null":
                        esquema["type"] = alt["type"]
            esquema["description"] = p.get("description", "")
            props[p["name"]] = esquema
            if p.get("required"):
                requeridos.append(p["name"])
        tools.append({
            "type": "function",
            "function": {
                "name": nombre,
                "description": (op.get("description") or op.get("summary", "")).strip(),
                "parameters": {"type": "object", "properties": props, "required": requeridos},
            },
        })
        rutas[nombre] = ruta
    return tools, rutas


def ejecutar(nombre: str, args: dict, rutas: dict) -> str:
    r = httpx.get(f"{HERRAMIENTAS}{rutas[nombre]}", params=args, timeout=60)
    return r.text  # el modelo recibe el JSON tal cual


def traza(paso: int, etiqueta: str, cuerpo: str) -> None:
    print(f"\n[{paso}] {etiqueta}")
    print(textwrap.indent(cuerpo.strip(), "    "))


def main(pregunta: str) -> None:
    tools, rutas = cargar_herramientas()
    mensajes = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": pregunta}]
    traza(0, "PREGUNTA", pregunta)
    traza(0, "HERRAMIENTAS DISPONIBLES", ", ".join(rutas))

    for paso in range(1, MAX_PASOS + 1):
        resp = httpx.post(
            f"{OLLAMA}/api/chat",
            json={"model": MODELO, "messages": mensajes, "tools": tools, "stream": False,
                  "options": {"temperature": 0}},
            timeout=300,
        ).json()
        msg = resp["message"]
        mensajes.append(msg)
        llamadas = msg.get("tool_calls") or []

        if not llamadas:  # criterio de parada: el modelo respondió
            traza(paso, "RESPUESTA FINAL", msg.get("content", ""))
            return

        for c in llamadas:
            fn, args = c["function"]["name"], c["function"]["arguments"]
            traza(paso, f"EL MODELO LLAMA A → {fn}", json.dumps(args, ensure_ascii=False))
            resultado = ejecutar(fn, args, rutas)
            traza(paso, f"RESULTADO DE ← {fn}", resultado[:800] + ("…" if len(resultado) > 800 else ""))
            mensajes.append({"role": "tool", "content": resultado, "tool_name": fn})

    traza(MAX_PASOS, "DETENIDO", "Se agotaron los pasos sin respuesta final. Esto también es un resultado: revisa la traza.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
