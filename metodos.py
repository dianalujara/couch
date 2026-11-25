import requests
from db_config import COUCH_URL

# ══════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════
DB_NAME = "recetario"
DB_URL = f"{COUCH_URL}/{DB_NAME}"


# ══════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════
def crear_bd():
    """PUT /recetario  → crea la BD (412 si ya existe, no pasa nada)."""
    r = requests.put(DB_URL)
    return r.status_code, r.json()


def info_bd():
    """GET /recetario  → metadatos (cantidad de documentos, tamaño, etc.)."""
    return requests.get(DB_URL).json()


# ══════════════════════════════════════════════
#  CRUD
# ══════════════════════════════════════════════
# ── Create ──
def crear_doc(doc):
    """POST /recetario  → CouchDB genera el _id y el _rev."""
    r = requests.post(DB_URL, json=doc)
    return r.json()


# ── Read ──
def listar_docs():
    """GET /recetario/_all_docs?include_docs=true  → todos los documentos."""
    r = requests.get(f"{DB_URL}/_all_docs", params={"include_docs": "true"})
    filas = r.json().get("rows", [])
    return [f["doc"] for f in filas if not f["id"].startswith("_design")]


def obtener_doc(doc_id):
    """GET /recetario/<id>  → un documento."""
    return requests.get(f"{DB_URL}/{doc_id}").json()



def buscar_docs(campo, valor):
    """Busca documentos mediante Mango, incluidos ingredientes en listas."""
    if campo == "ingredientes":
        if isinstance(valor, list):
            ingredientes = valor
        else:
            ingredientes = [
                ingrediente.strip()
                for ingrediente in str(valor).split(",")
                if ingrediente.strip()
            ]

        if len(ingredientes) == 1:
            condicion = {"$elemMatch": {"$eq": ingredientes[0]}}
        else:
            condicion = {"$all": ingredientes}

        consulta = {
            "selector": {
                "ingredientes": condicion
            }
        }
    else:
        consulta = {"selector": {campo: valor}}

    r = requests.post(f"{DB_URL}/_find", json=consulta)
    r.raise_for_status()
    return r.json().get("docs", [])



# ── Update ──
def actualizar_doc(doc_id, rev, doc):
    """PUT /recetario/<id>?rev=<rev>  → exige la revisión actual (MVCC)."""
    doc["_id"] = doc_id
    doc["_rev"] = rev
    r = requests.put(f"{DB_URL}/{doc_id}", json=doc)
    return r.status_code, r.json()


# ── Delete ──
def eliminar_doc(doc_id, rev):
    """DELETE /recetario/<id>?rev=<rev>."""
    r = requests.delete(f"{DB_URL}/{doc_id}", params={"rev": rev})
    return r.status_code, r.json()