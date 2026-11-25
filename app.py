import json
from flask import Flask, render_template_string, request, redirect, url_for, flash

import metodos

app = Flask(__name__)
app.secret_key = "demo-couchdb"


# ══════════════════════════════════════════════
#  UTILIDADES
# ══════════════════════════════════════════════
def convertir_valor(texto):
    """Intenta interpretar el valor como JSON (número, lista, objeto, true/false).
    Si no se puede, queda como texto. Así cada campo puede tener un tipo distinto."""
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def avisar(texto, es_error=False):
    """Muestra una alerta: verde si salió bien, roja si es un error."""
    flash(texto, "error" if es_error else "ok")


def doc_desde_formulario():
    """Arma el documento con los pares campo/valor que el usuario escribió."""
    campos = request.form.getlist("campo")
    valores = request.form.getlist("valor")
    doc = {}
    for c, v in zip(campos, valores):
        c = c.strip()
        if c:
            doc[c] = convertir_valor(v.strip())
    return doc


# ══════════════════════════════════════════════
#  RUTAS
# ══════════════════════════════════════════════
# ── Inicio: listar / buscar ──
@app.route("/")
def inicio():
    campo = request.args.get("campo", "").strip()
    valor = request.args.get("valor", "").strip()
    if campo and valor:
        docs = metodos.buscar_docs(campo, convertir_valor(valor))
    else:
        docs = metodos.listar_docs()
    return render_template_string(
        PLANTILLA, docs=docs, info=metodos.info_bd(),
        campo=campo, valor=valor, editando=None, json=json)


# ── Create ──
@app.route("/crear", methods=["POST"])
def crear():
    doc = doc_desde_formulario()
    if not doc:
        avisar("El documento está vacío.", True)
    else:
        resp = metodos.crear_doc(doc)
        avisar(f"POST /{metodos.DB_NAME} → {resp}", "error" in resp)
    return redirect(url_for("inicio"))


# ── Update ──
@app.route("/editar/<doc_id>", methods=["GET", "POST"])
def editar(doc_id):
    if request.method == "POST":
        rev = request.form["rev"]
        try:
            doc = json.loads(request.form["json"])
        except ValueError:
            avisar("JSON inválido.", True)
            return redirect(url_for("editar", doc_id=doc_id))
        doc.pop("_id", None)
        doc.pop("_rev", None)
        codigo, resp = metodos.actualizar_doc(doc_id, rev, doc)
        avisar(f"PUT /{metodos.DB_NAME}/{doc_id}?rev=... → {codigo} {resp}", codigo >= 400)
        return redirect(url_for("inicio"))
    doc = metodos.obtener_doc(doc_id)
    editable = {k: v for k, v in doc.items() if k not in ("_id", "_rev")}
    return render_template_string(
        PLANTILLA, docs=[], info=metodos.info_bd(), campo="", valor="",
        editando=doc, editable=editable, json=json)


# ── Delete ──
@app.route("/eliminar/<doc_id>/<rev>", methods=["POST"])
def eliminar(doc_id, rev):
    codigo, resp = metodos.eliminar_doc(doc_id, rev)
    avisar(f"DELETE /{metodos.DB_NAME}/{doc_id} → {codigo} {resp}", codigo >= 400)
    return redirect(url_for("inicio"))


# ── Datos de ejemplo (estructuras distintas a propósito) ──
@app.route("/ejemplos", methods=["POST"])
def ejemplos():
    muestras = [
        {"tipo": "receta", "nombre": "Tortilla de papas", "tiempo_min": 30,
         "ingredientes": ["papas", "huevos", "cebolla"]},
        {"tipo": "receta", "nombre": "Ensalada César", "vegetariana": False,
         "calorias": 420, "autor": {"nombre": "Ana", "pais": "Argentina"}},
        {"tipo": "nota", "texto": "Comprar harina", "etiquetas": ["super", "urgente"]},
    ]
    for m in muestras:
        metodos.crear_doc(m)
    avisar("3 documentos de ejemplo creados: fijate que ninguno tiene los mismos campos.")
    return redirect(url_for("inicio"))


# ══════════════════════════════════════════════
#  PLANTILLA HTML
# ══════════════════════════════════════════════
PLANTILLA = """
<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demo CouchDB</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:900px;margin:20px auto;padding:0 12px;background:#f4f5f7;color:#222}
  h1{margin-bottom:0} .sub{color:#666;margin-top:4px}
  .box{background:#fff;border-radius:8px;padding:14px;margin:12px 0;box-shadow:0 1px 3px #0002}
  .msg{background:#e8f5e9;border-left:8px solid #2e7d32;color:#1b5e20;padding:16px 18px;margin:12px 0;font-family:monospace;font-size:17px;font-weight:600;border-radius:6px;word-break:break-all}
  .msg.error{background:#ffebee;border-left-color:#c62828;color:#b71c1c}
  pre{background:#1e1e1e;color:#9cdcfe;padding:10px;border-radius:6px;overflow-x:auto;font-size:13px}
  input,textarea{padding:6px;border:1px solid #bbb;border-radius:4px;font-size:14px}
  textarea{width:100%;height:220px;font-family:monospace;box-sizing:border-box}
  button,.btn{padding:6px 12px;border:0;border-radius:4px;color:#fff;cursor:pointer;font-size:14px;text-decoration:none;display:inline-block}
  .verde{background:#2e7d32}.azul{background:#1565c0}.rojo{background:#c62828}.gris{background:#616161}
  .fila{display:flex;gap:6px;margin-bottom:6px} .fila input{flex:1;min-width:0}
</style></head><body>

<h1>Demo CouchDB</h1>
<p class="sub">Base: <b>{{ info.get('db_name','?') }}</b> · documentos: <b>{{ info.get('doc_count','?') }}</b></p>

{% with m = get_flashed_messages(with_categories=true) %}{% for cat, x in m %}<div class="msg {{ cat }}">{{ x }}</div>{% endfor %}{% endwith %}

{% if editando %}
<div class="box">
  <h3>Editar documento <code>{{ editando._id }}</code></h3>
  <p>Revisión actual (<code>_rev</code>): <code>{{ editando._rev }}</code></p>
  <form method="post">
    <input type="hidden" name="rev" value="{{ editando._rev }}">
    <textarea name="json">{{ json.dumps(editable, indent=2, ensure_ascii=False) }}</textarea><br><br>
    <button class="azul">Guardar cambios</button>
    <a class="btn gris" href="{{ url_for('inicio') }}">Cancelar</a>
  </form>
</div>
{% else %}

<div class="box">
  <h3>Crear documento</h3>
  <p class="sub">Cada documento puede tener los campos que quieras. Los valores pueden ser texto, números, <code>true</code>, listas <code>["a","b"]</code> u objetos <code>{"x":1}</code>.</p>
  <form method="post" action="{{ url_for('crear') }}">
    <div id="campos">
      <div class="fila"><input name="campo" placeholder="campo" value="tipo"><input name="valor" placeholder="valor"></div>
      <div class="fila"><input name="campo" placeholder="campo" value="nombre"><input name="valor" placeholder="valor"></div>
    </div>
    <button type="button" class="gris" onclick="agregar()">+ campo</button>
    <button class="verde">Guardar en CouchDB</button>
  </form>
  <form method="post" action="{{ url_for('ejemplos') }}" style="margin-top:8px">
    <button class="azul">Cargar 3 ejemplos con estructuras distintas</button>
  </form>
</div>

<div class="box">
  <h3>Buscar (consulta Mango <code>_find</code>)</h3>
  <form method="get" class="fila">
    <input name="campo" placeholder="campo" value="{{ campo }}">
    <input name="valor" placeholder="valor" value="{{ valor }}">
    <button class="azul">Buscar</button>
    <a class="btn gris" href="{{ url_for('inicio') }}">Todos</a>
  </form>
</div>

<h3>Documentos ({{ docs|length }})</h3>
{% for d in docs %}
<div class="box">
  <pre>{{ json.dumps(d, indent=2, ensure_ascii=False) }}</pre>
  <a class="btn azul" href="{{ url_for('editar', doc_id=d._id) }}">Editar</a>
  <form method="post" action="{{ url_for('eliminar', doc_id=d._id, rev=d._rev) }}" style="display:inline"
        onsubmit="return confirm('¿Eliminar?')"><button class="rojo">Eliminar</button></form>
</div>
{% else %}<p>No hay documentos todavía.</p>{% endfor %}

{% endif %}

<script>
function agregar(){
  const f=document.createElement('div');f.className='fila';
  f.innerHTML='<input name="campo" placeholder="campo"><input name="valor" placeholder="valor">';
  document.getElementById('campos').appendChild(f);
}
</script>
</body></html>
"""


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("Creando BD:", metodos.crear_bd())
    app.run(debug=True)