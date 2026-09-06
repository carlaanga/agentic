"""
Servidor de herramientas GBIF para agentes de IA.

Cada función expuesta aquí es una *herramienta*: un contrato que el modelo
puede leer (nombre, descripción, parámetros) y decidir invocar. El texto de
las descripciones no es documentación para humanos: es lo que el modelo lee
para decidir cuándo y cómo llamar a la herramienta. Escribirlo bien es una
competencia nueva.

El esquema OpenAPI se genera solo en /openapi.json y es el mismo que
Open WebUI y agente/agente.py consumen.
"""

from datetime import date
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

GBIF = "https://api.gbif.org/v1"

app = FastAPI(
    title="Herramientas GBIF",
    version="0.1.0",
    description=(
        "Herramientas para consultar la infraestructura GBIF: resolver nombres "
        "científicos y contar o listar registros de ocurrencia."
    ),
)

# Los modelos pequeños a veces escriben el país en español. Aceptamos ambos.
PAISES = {
    "argentina": "AR", "bolivia": "BO", "brasil": "BR", "brazil": "BR",
    "chile": "CL", "colombia": "CO", "costa rica": "CR", "cuba": "CU",
    "ecuador": "EC", "el salvador": "SV", "guatemala": "GT", "honduras": "HN",
    "méxico": "MX", "mexico": "MX", "nicaragua": "NI", "panamá": "PA",
    "panama": "PA", "paraguay": "PY", "perú": "PE", "peru": "PE",
    "república dominicana": "DO", "uruguay": "UY", "venezuela": "VE",
    "españa": "ES", "estados unidos": "US",
}


def a_iso(pais: Optional[str]) -> Optional[str]:
    if not pais:
        return None
    p = pais.strip()
    if len(p) == 2:
        return p.upper()
    return PAISES.get(p.lower(), p)


def normalizar_anio(anio: Optional[str]) -> Optional[str]:
    """Acepta '2020', '2020,2026' o '2020,*' ("desde 2020"). GBIF no entiende '*': lo cambiamos por el año actual."""
    if not anio:
        return None
    a = anio.strip().replace(" ", "")
    if a.endswith(",*"):
        a = f"{a[:-2]},{date.today().year}"
    if a.startswith("*,"):
        a = f"1600,{a[2:]}"
    return a


def gbif_get(path: str, params: dict) -> dict | int | list:
    params = {k: v for k, v in params.items() if v is not None}
    try:
        r = httpx.get(f"{GBIF}{path}", params=params, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error consultando GBIF: {e}")
    return r.json()


class Taxon(BaseModel):
    usageKey: Optional[int] = Field(None, description="Identificador del taxón en GBIF (taxonKey). Úsalo en las demás herramientas.")
    scientificName: Optional[str] = None
    canonicalName: Optional[str] = None
    rank: Optional[str] = None
    status: Optional[str] = Field(None, description="ACCEPTED, SYNONYM, DOUBTFUL...")
    confidence: Optional[int] = Field(None, description="0-100. Bajo 90 conviene avisar al usuario.")
    matchType: Optional[str] = Field(None, description="EXACT, FUZZY, HIGHERRANK o NONE. NONE significa que no se encontró.")
    kingdom: Optional[str] = None
    family: Optional[str] = None
    acceptedUsageKey: Optional[int] = None


@app.get(
    "/especies/resolver",
    operation_id="resolver_nombre",
    summary="Resolver un nombre científico a un taxón GBIF",
    response_model=Taxon,
)
def resolver_nombre(
    nombre: str = Query(
        ...,
        description="Nombre científico tal como lo escribió el usuario, por ejemplo 'Puma concolor' o 'Nothofagus'. No uses nombres comunes.",
    ),
):
    """
    Convierte un nombre científico en un identificador de taxón de GBIF (usageKey).

    Llama SIEMPRE a esta herramienta antes de contar o buscar registros:
    las demás herramientas necesitan el usageKey, no el nombre.
    Revisa matchType y confidence: si matchType es NONE o confidence es bajo,
    díselo al usuario en vez de inventar un resultado.
    """
    datos = gbif_get("/species/match", {"name": nombre, "verbose": "false"})
    return Taxon(**datos)


class Conteo(BaseModel):
    taxonKey: int
    pais: Optional[str]
    anio: Optional[str]
    total: int
    consulta: str = Field(description="URL exacta consultada, para citar la fuente.")


@app.get(
    "/ocurrencias/contar",
    operation_id="contar_ocurrencias",
    summary="Contar registros de ocurrencia en GBIF",
    response_model=Conteo,
)
def contar_ocurrencias(
    taxonKey: int = Query(..., description="usageKey obtenido con resolver_nombre."),
    pais: Optional[str] = Query(None, description="País, código ISO de dos letras (CL, CO, UY, AR, MX...). También acepta el nombre en español."),
    anio: Optional[str] = Query(None, description="Año o rango: '2020' (solo ese año), '2020,2026' (rango) o '2020,*' (desde 2020 hasta hoy). Si el usuario dice 'desde X', usa 'X,*'."),
    con_coordenadas: Optional[bool] = Query(None, description="Solo si el usuario pide registros georreferenciados (con coordenadas). Si no lo pide, no lo envíes."),
):
    """
    Devuelve cuántos registros de ocurrencia tiene GBIF para un taxón,
    opcionalmente filtrados por país y año. Es un conteo exacto de la base
    de datos, no una estimación.
    """
    iso = a_iso(pais)
    anio_gbif = normalizar_anio(anio)
    params = {"taxonKey": taxonKey, "country": iso, "year": anio_gbif}
    if con_coordenadas:
        # /occurrence/count no acepta hasCoordinate; /occurrence/search con limit=0 acepta todos los filtros.
        params["hasCoordinate"] = True
        params["limit"] = 0
        total = gbif_get("/occurrence/search", params)["count"]
        ruta = "/occurrence/search"
    else:
        total = gbif_get("/occurrence/count", params)
        ruta = "/occurrence/count"
    limpios = {k: v for k, v in params.items() if v is not None}
    url = httpx.URL(f"{GBIF}{ruta}", params=limpios)
    return Conteo(taxonKey=taxonKey, pais=iso, anio=anio_gbif, total=int(total), consulta=str(url))


class Registro(BaseModel):
    gbifID: Optional[str] = None
    scientificName: Optional[str] = None
    eventDate: Optional[str] = None
    country: Optional[str] = None
    stateProvince: Optional[str] = None
    decimalLatitude: Optional[float] = None
    decimalLongitude: Optional[float] = None
    basisOfRecord: Optional[str] = None
    institutionCode: Optional[str] = None
    datasetKey: Optional[str] = None


class Busqueda(BaseModel):
    total: int
    mostrados: int
    registros: list[Registro]
    consulta: str


@app.get(
    "/ocurrencias/buscar",
    operation_id="buscar_ocurrencias",
    summary="Listar algunos registros de ocurrencia",
    response_model=Busqueda,
)
def buscar_ocurrencias(
    taxonKey: int = Query(..., description="usageKey obtenido con resolver_nombre."),
    pais: Optional[str] = Query(None, description="País, código ISO de dos letras o nombre en español."),
    anio: Optional[str] = Query(None, description="Año o rango: '2020', '2020,2026' o '2020,*' (desde 2020)."),
    limite: int = Query(5, ge=1, le=20, description="Cuántos registros devolver (máximo 20)."),
):
    """
    Devuelve una muestra de registros individuales con fecha, lugar,
    coordenadas e institución. Úsala cuando el usuario quiera ver ejemplos,
    no cuando solo quiera un número (para eso usa contar_ocurrencias).
    """
    params = {"taxonKey": taxonKey, "country": a_iso(pais), "year": normalizar_anio(anio), "limit": limite}
    datos = gbif_get("/occurrence/search", params)
    regs = []
    for r in datos.get("results", []):
        regs.append(Registro(**{k: (str(v) if k == "gbifID" and v is not None else v) for k, v in r.items() if k in Registro.model_fields}))
    limpios = {k: v for k, v in params.items() if v is not None}
    url = httpx.URL(f"{GBIF}/occurrence/search", params=limpios)
    return Busqueda(total=datos.get("count", 0), mostrados=len(regs), registros=regs, consulta=str(url))


@app.get("/salud", include_in_schema=False)
def salud():
    return {"ok": True}
