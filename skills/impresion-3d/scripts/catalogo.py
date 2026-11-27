#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Panel del taller: las ideas y piezas del usuario y en qué paso está cada una.

Lleva un índice (`taller-3d/catalogo.json` en la carpeta de trabajo) con una entrada por idea o pieza
y arma `panel.html`, una página que se abre con el navegador desde la carpeta de trabajo. Cada
tarjeta muestra el recorrido (Idea → Diseño → Lista para imprimir → Impresa → En la tienda), lo que
sigue, la vista, la impresora, los datos y enlaces a los archivos. Arriba, "Para hacer" (ideas y
piezas en proceso); abajo, las terminadas por mes. Tiene buscador y filtros. Las imágenes se cargan
desde la carpeta de cada pieza: no hace falta traerlas.

Las carpetas de las piezas llevan la impresora para la que se hicieron:
impresiones/AAAA-MM-DD_nombre_impresora/ (los diseños sin impresora, disenos/AAAA-MM-DD_nombre/).

Uso:
  # Nombre de la carpeta de una pieza nueva y de su G-code y proyecto (.gcode y .3mf)
  python3 catalogo.py carpeta --nombre "Soporte para router" --impresora "Ender-3 V3 Plus" [--tipo diseno]
  #   → {"carpeta": "impresiones/2026-11-21_soporte-para-router_ender-3-v3-plus",
  #      "archivo": "soporte-para-router_ender-3-v3-plus"}

  # Agregar o actualizar una pieza (cada vez que se guarda, se lamina, se imprime o se publica)
  python3 catalogo.py agregar --catalogo catalogo.json \\
      --carpeta impresiones/2026-11-21_soporte-para-router_ender-3-v3-plus --impresora "Ender-3 V3 Plus" \\
      --nombre "Soporte para router" [--tipo impresion|diseno] [--material PETG] [--color negro] \\
      [--informe-gcode informe_gcode.json] [--informe-stl informe_stl.json] [--producto publicacion.json] \\
      [--archivos pieza.stl pieza.py vista.png informe.md] [--imagen vista.png] \\
      [--estado disenada|laminada|impresa|en_tienda] [--nota "..."] [--url-tienda https://...] [--id-tienda 123] [--estado-publicacion borrador] [--moneda ARS] \\
      [--origen stl_propio|stl_descargado --fuente https://... --licencia "CC BY"]

  # Anotar una idea para más adelante (y quitarla si el usuario la descarta)
  python3 catalogo.py idea --catalogo catalogo.json --nombre "Soporte para la tele" [--nota "..."] [--impresora X]
  python3 catalogo.py quitar-idea --catalogo catalogo.json --carpeta ideas/2026-11-21_soporte-para-la-tele

  # Cuando una idea se hace pieza: agregar la pieza con --de-idea ideas/AAAA-MM-DD_nombre (la idea pasa a la pieza)

  # Anotar lo que dice la tienda (estado_productos del conector taller3d-tienda, guardado en estados.json):
  # publicada o borrador se anota sola; en la papelera o borrado, se pregunta y, con el OK, --sacar <carpeta>
  python3 catalogo.py estados-tienda --catalogo catalogo.json --estados estados.json [--sacar impresiones/...]

  # Sumar las piezas que ya estaban: listado de device_list_dir (recursive=true) de la carpeta de trabajo
  python3 catalogo.py desde-listado --catalogo catalogo.json --listado listado.json

  # Armar la página (y, una sola vez, reemplazar el catalogo.html de antes de la 0.1.13 por un acceso al panel)
  python3 catalogo.py html --catalogo catalogo.json --salida panel.html [--titulo "Panel del taller"]
  python3 catalogo.py redireccion --salida catalogo.html

  # Resumen en texto: --corto da una línea para el comienzo de la conversación
  python3 catalogo.py resumen --catalogo catalogo.json [--buscar texto] [--corto]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

TIPOS = {"idea": "Idea", "impresion": "Impresión", "diseno": "Diseño"}
ESTADOS = {
    "idea": "Idea",
    "disenada": "Diseñada",
    "laminada": "Lista para imprimir",
    "impresa": "Impresa",
    "en_tienda": "En la tienda (borrador)",
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
RE_CARPETA = re.compile(r"^(impresiones|disenos|ideas)/(\d{4}-\d{2}-\d{2})_([^/]+)$")
# El recorrido de una idea hasta la tienda, y los grupos del panel
PASOS = [("idea", "Idea"), ("disenada", "Diseño"), ("laminada", "Lista para imprimir"), ("impresa", "Impresa"),
         ("en_tienda", "En la tienda")]
GRUPOS = {"pendiente": "Pendientes", "en_proceso": "En proceso", "terminada": "Terminadas"}
G_CODE = (".gcode", ".gco", ".gcode.3mf")
IMAGENES = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cargar(ruta: Path) -> dict:
    if ruta.exists() and ruta.read_text(encoding="utf-8").strip():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if not isinstance(datos, dict) or not isinstance(datos.get("piezas"), list):
            raise SystemExit(f"{ruta} no tiene el formato del catálogo.")
        return datos
    return {"version": 1, "piezas": []}


def guardar(ruta: Path, catalogo: dict) -> None:
    catalogo["actualizado"] = _ahora()
    catalogo["piezas"].sort(key=lambda p: (p.get("fecha") or "", p.get("carpeta") or ""), reverse=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalizar_carpeta(carpeta: str) -> str:
    c = str(carpeta).replace("\\", "/").strip().strip("/")
    partes = [p for p in c.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." for p in partes):
        raise SystemExit(f"Carpeta inválida: {carpeta!r} (tiene que ser relativa a la carpeta de trabajo).")
    return "/".join(partes)


def carpeta_de_pieza(tipo: str, nombre: str, impresora: str | None = None, fecha: str | None = None) -> str:
    """impresiones/AAAA-MM-DD_nombre_impresora (o disenos/...): la impresora va al final, después de un '_'."""
    base = f"{fecha or time.strftime('%Y-%m-%d')}_{comun.slug(nombre)}"
    if impresora:
        base += f"_{comun.slug(impresora, 'impresora')}"
    return f"{'disenos' if tipo == 'diseno' else 'impresiones'}/{base}"


def archivo_de_pieza(nombre: str, impresora: str | None = None) -> str:
    """Nombre del G-code y del proyecto de Orca: nombre_impresora (sin extensión)."""
    return comun.slug(nombre) + (f"_{comun.slug(impresora, 'impresora')}" if impresora else "")


def partes_de_carpeta(carpeta: str) -> tuple[str | None, str, str | None]:
    """(fecha, nombre, impresora) de una carpeta de pieza. Los nombres usan guiones; la impresora va
    después del segundo '_' (desde la 0.1.12; las carpetas anteriores no la tienen)."""
    m = RE_CARPETA.match(carpeta)
    base = m.group(3) if m else carpeta.rsplit("/", 1)[-1]
    nombre, _, impresora = base.partition("_")
    return (m.group(2) if m else None), nombre, (impresora or None)


def nombre_desde_carpeta(carpeta: str) -> str:
    texto = re.sub(r"[-_]+", " ", partes_de_carpeta(carpeta)[1]).strip()
    return texto[:1].upper() + texto[1:] if texto else carpeta


def url_segura(url: str | None) -> str | None:
    if not url:
        return None
    u = urlparse(str(url).strip())
    return u.geturl() if u.scheme in ("http", "https") and u.netloc else None


def _leer_json(ruta: str | None) -> dict:
    if not ruta:
        return {}
    datos = comun.cargar_json(ruta)
    return datos if isinstance(datos, dict) else {}


def datos_de_informes(gcode: dict, stl: dict, producto: dict) -> dict:
    """Lo que interesa del catálogo, sacado de los informes de los otros scripts."""
    d: dict = {}
    if stl.get("medidas_mm"):
        d["medidas_mm"] = [round(float(x), 1) for x in stl["medidas_mm"]][:3]
    if gcode:
        est = gcode.get("estimaciones") or {}
        if est.get("segundos"):
            d["segundos"] = int(est["segundos"])
            d["tiempo"] = comun.formato_duracion(est["segundos"])
        if est.get("gramos"):
            d["gramos"] = round(float(est["gramos"]), 1)
        costo = gcode.get("costo") or {}
        if costo.get("total"):
            d["costo"] = {"total": costo["total"], "moneda": costo.get("moneda")}
        if gcode.get("material"):
            d["material"] = gcode["material"]
        if gcode.get("estado"):
            d["revision"] = gcode["estado"]
        d["estado"] = "laminada"
    if isinstance(producto.get("producto"), dict):       # publicacion.json (0.1.30) trae el producto adentro
        d["publicacion"] = publicacion_de(producto)
        producto = producto["producto"]
        if producto.get("regular_price"):
            d["precio"] = {"valor": producto["regular_price"]}
            if d["publicacion"]["precio"].get("moneda"):
                d["precio"]["moneda"] = d["publicacion"]["precio"]["moneda"]
        # Armar la publicación no es tenerla en la tienda: eso lo dice su estado (borrador o publicada).
    elif producto:                                       # producto.json de antes de la 0.1.30
        if producto.get("regular_price"):
            d["precio"] = {"valor": producto["regular_price"]}
        d["estado"] = "en_tienda"
    return d


# Dónde está la publicación de una pieza: armada acá (vista previa), cargada como borrador o ya publicada.
ESTADOS_PUBLICACION = {"vista_previa": "Vista previa, sin cargar en la tienda", "borrador": "Borrador en la tienda",
                       "publicada": "Publicada"}
VISTA_PUBLICACION = "producto/vista-previa.html"


def publicacion_de(pub: dict) -> dict:
    """Lo que el panel muestra de una publicación, sacado de publicacion.json (producto_tienda.py)."""
    producto = pub.get("producto") or {}
    pr = pub.get("precio") or {}
    canal = (pr.get("canales") or {}).get(pr.get("canal")) or {}
    fotos = [f for f in pub.get("fotos") or [] if isinstance(f, str)]
    d = {"titulo": str(producto.get("name") or ""), "vista": VISTA_PUBLICACION, "fotos": len(fotos),
         "fotos_reales": int(pub.get("fotos_reales") or 0),
         "precio": {"valor": producto.get("regular_price") or None, "moneda": pr.get("moneda"),
                    "con_iva": bool(pr.get("con_iva"))}}
    if fotos:                                            # relativa a la carpeta de la pieza (las reales van con ../)
        primera = fotos[0]
        d["foto"] = primera[3:] if primera.startswith("../") else f"producto/{primera}"
    if "error" not in canal and canal.get("ganancia") is not None:
        d["ganancia"] = {"valor": canal["ganancia"], "margen_pct": canal.get("margen_real_pct")}
    if producto.get("sku"):
        d["sku"] = str(producto["sku"])
    return d


def estado_publicacion(pieza: dict) -> str | None:
    """vista_previa, borrador o publicada; None si la pieza no tiene publicación armada."""
    pub = pieza.get("publicacion")
    if not isinstance(pub, dict):
        return None
    if pub.get("estado") in ("borrador", "publicada"):
        return pub["estado"]
    return "borrador" if pieza.get("id_tienda") else "vista_previa"      # con número en la tienda, ya está cargada


# Lo que dice la tienda de cada producto (estado_productos del conector taller3d-tienda, 0.1.41). Publicada o borrador
# se anota sola: es lo que el usuario hizo en su tienda. En la papelera o borrado no se toca sin preguntarle.
SIN_PUBLICAR = ("draft", "pending", "private", "future")
FUERA_DE_LA_TIENDA = ("trash", "borrado")


def _id_tienda(p: dict) -> int | None:
    v = p.get("id_tienda")
    if isinstance(v, str) and v.strip().isdigit():
        v = int(v.strip())
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def etiqueta_estado(p: dict) -> str:
    """El paso de la pieza en palabras; en la tienda, si está publicada o en borrador."""
    if p.get("estado") == "en_tienda":
        return "En la tienda (publicada)" if estado_publicacion(p) == "publicada" else ESTADOS["en_tienda"]
    return ESTADOS.get(p.get("estado"), str(p.get("estado")))


def sacar_de_la_tienda(p: dict) -> None:
    """El producto ya no está en la tienda (lo borraron): la publicación vuelve a vista previa, sin número, y la
    pieza vuelve al paso que tiene sin la tienda."""
    p.pop("id_tienda", None)
    p.pop("url_tienda", None)
    if isinstance(p.get("publicacion"), dict):
        p["publicacion"]["estado"] = "vista_previa"
    p["en_tienda"] = False
    if p.get("estado") == "en_tienda":
        archivos = [str(a).lower() for a in p.get("archivos") or []]
        p["estado"] = ("impresa" if p.get("impresa") or any(es_foto_impresa(a) for a in archivos) else
                       "laminada" if any(a.endswith(G_CODE) for a in archivos) else "disenada")


def aplicar_estados_tienda(catalogo: dict, estados: dict, sacar: list[str] | None = None) -> dict:
    """Anota en el panel lo que dice la tienda. Devuelve los cambios, lo que hay que preguntar y lo que se sacó."""
    productos = estados.get("productos") if isinstance(estados, dict) else None
    if not isinstance(productos, list):
        raise SystemExit("No entiendo la respuesta de estado_productos: le falta «productos».")
    por_id = {x["id"]: x for x in productos
              if isinstance(x, dict) and isinstance(x.get("id"), int) and not isinstance(x.get("id"), bool)}
    sacar = {normalizar_carpeta(c) for c in sacar or []}
    salida = {"cambios": [], "para_preguntar": [], "sacadas": [], "revisadas": 0, "enlaces": 0}
    for p in catalogo["piezas"]:
        pid = _id_tienda(p)
        x = por_id.get(pid) if pid else None
        if x is None:
            continue
        salida["revisadas"] += 1
        status, antes = x.get("status"), estado_publicacion(p)
        nombre = p.get("nombre") or p.get("carpeta")
        if status in FUERA_DE_LA_TIENDA:
            como = "en la papelera" if status == "trash" else "borrado"
            if p.get("carpeta") in sacar:
                sacar_de_la_tienda(p)
                p["actualizado"] = _ahora()
                salida["sacadas"].append({"carpeta": p["carpeta"], "nombre": nombre, "id": pid, "estado": como})
            else:
                salida["para_preguntar"].append({"carpeta": p["carpeta"], "nombre": nombre, "id": pid, "estado": como})
            continue
        if status == "publish":
            ahora, enlace = "publicada", url_segura(x.get("enlace"))
        elif status in SIN_PUBLICAR:
            ahora, enlace = "borrador", url_segura(x.get("enlace_admin"))
        else:
            continue
        cambio = False
        if antes is not None and ahora != antes:         # sin publicación armada en el panel, solo el enlace
            p["publicacion"]["estado"] = ahora
            salida["cambios"].append({"carpeta": p["carpeta"], "nombre": nombre, "id": pid, "antes": antes,
                                      "ahora": ahora, "en_la_tienda": x.get("estado") or status})
            cambio = True
        if enlace and p.get("url_tienda") != enlace:     # publicada: la página del producto; borrador: el admin
            p["url_tienda"] = enlace
            salida["enlaces"] += 1
            cambio = True
        if cambio:
            p["actualizado"] = _ahora()
    return salida


def contar_estados(r: dict) -> str:
    """Lo que hizo estados-tienda, en una o dos líneas."""
    def donde(c: dict) -> str:
        return "está en la papelera de la tienda" if c["estado"] == "en la papelera" else "ya no está en la tienda"
    partes = [f"«{c['nombre']}»: " + ("publicada en la tienda" if c["ahora"] == "publicada" else "volvió a borrador")
              for c in r["cambios"]]
    partes += [f"saqué del panel «{c['nombre']}» ({c['id']}): {donde(c)}" for c in r["sacadas"]]
    texto = "; ".join(partes) + "." if partes else f"Sin cambios: revisé {r['revisadas']} productos de la tienda."
    if r["para_preguntar"]:
        texto += " Preguntar: " + "; ".join(f"«{c['nombre']}» ({c['id']}) {donde(c)}" for c in r["para_preguntar"]) + "."
    return texto[:1].upper() + texto[1:]


def agregar(catalogo: dict, carpeta: str, de_idea: str | None = None, **campos) -> dict:
    """Agrega o actualiza una pieza (o idea). Con de_idea, la idea anotada pasa a esta pieza."""
    carpeta = normalizar_carpeta(carpeta)
    pieza = next((p for p in catalogo["piezas"] if p.get("carpeta") == carpeta), None)
    if pieza is None:
        fecha, _, impresora = partes_de_carpeta(carpeta)
        es_idea = carpeta.startswith("ideas/")
        pieza = {
            "carpeta": carpeta,
            "tipo": "idea" if es_idea else "diseno" if carpeta.startswith("disenos/") else "impresion",
            "nombre": nombre_desde_carpeta(carpeta),
            "fecha": fecha or time.strftime("%Y-%m-%d"),
            "estado": "idea" if es_idea else "disenada",
            "archivos": [],
        }
        if impresora:
            pieza["impresora"] = impresora
        catalogo["piezas"].append(pieza)
    for clave, valor in campos.items():
        if valor in (None, "", [], {}):
            continue
        if clave == "archivos":
            nuevos = [normalizar_carpeta(a) for a in valor]
            pieza["archivos"] = sorted(set(pieza.get("archivos", [])) | set(nuevos))
        elif clave in ("url_tienda", "fuente"):              # solo direcciones http(s)
            segura = url_segura(valor)
            if segura:
                pieza[clave] = segura
        elif clave == "origen" and valor not in ORIGENES:
            raise SystemExit(f"Origen desconocido: {valor} ({', '.join(ORIGENES)}).")
        elif clave == "tipo" and valor not in TIPOS:
            raise SystemExit(f"Tipo desconocido: {valor} (impresion o diseno).")
        elif clave == "estado" and valor not in ESTADOS:
            raise SystemExit(f"Estado desconocido: {valor} ({', '.join(ESTADOS)}).")
        elif clave == "estado":
            pieza["estado"] = valor
            if valor in ("impresa", "en_tienda"):
                pieza[valor] = True                       # se recuerda aunque después cambie el estado
        else:
            pieza[clave] = valor
    if de_idea:
        _pasar_idea(catalogo, pieza, de_idea, nombre_dado="nombre" in campos and bool(campos["nombre"]))
    if pieza.get("precio") and "moneda" not in pieza["precio"]:
        moneda = (pieza.get("costo") or {}).get("moneda")
        if moneda:
            pieza["precio"]["moneda"] = moneda
    pieza["actualizado"] = _ahora()
    return pieza


def _pasar_idea(catalogo: dict, pieza: dict, carpeta_idea: str, nombre_dado: bool) -> None:
    carpeta_idea = normalizar_carpeta(carpeta_idea)
    idea = next((p for p in catalogo["piezas"] if p.get("carpeta") == carpeta_idea and p.get("tipo") == "idea"), None)
    if idea is None or idea is pieza:
        return
    catalogo["piezas"].remove(idea)
    if idea.get("nombre") and not nombre_dado:
        pieza["nombre"] = idea["nombre"]
    if idea.get("nota") and not pieza.get("nota"):
        pieza["nota"] = idea["nota"]
    pieza["idea_fecha"] = idea.get("fecha")


def agregar_idea(catalogo: dict, nombre: str, nota: str | None = None, impresora: str | None = None,
                 fecha: str | None = None) -> dict:
    carpeta = f"ideas/{fecha or time.strftime('%Y-%m-%d')}_{comun.slug(nombre, 'idea')}"
    return agregar(catalogo, carpeta, nombre=nombre, nota=nota, impresora=impresora)


def quitar_idea(catalogo: dict, carpeta: str) -> bool:
    """Saca una idea que el usuario descartó. Las piezas no se sacan: tienen archivos."""
    carpeta = normalizar_carpeta(carpeta)
    idea = next((p for p in catalogo["piezas"] if p.get("carpeta") == carpeta), None)
    if idea is None:
        return False
    if idea.get("tipo") != "idea":
        raise SystemExit(f"{carpeta} no es una idea: las piezas no se sacan del panel.")
    catalogo["piezas"].remove(idea)
    return True


# La foto de la pieza impresa: foto.jpg (o foto-2.jpg…) en la carpeta de la pieza. Otras fotos (la de referencia
# de una pieza generada desde una foto, por ejemplo) no la marcan como impresa.
RE_FOTO_IMPRESA = re.compile(r"^foto(?:-\d+)?\.(?:jpe?g|png|webp)$")


def es_foto_impresa(archivo) -> bool:
    a = str(archivo).replace("\\", "/").lower()
    return "/" not in a and bool(RE_FOTO_IMPRESA.match(a))


def hechos(p: dict) -> set[str]:
    """Pasos del recorrido que ya se cumplieron."""
    if p.get("tipo") == "idea" or p.get("estado") == "idea":
        return {"idea"}
    estado = p.get("estado") or "disenada"
    archivos = [str(a).lower() for a in p.get("archivos") or []]
    h = {"idea", "disenada"}
    foto = any(es_foto_impresa(a) for a in archivos)
    if p.get("impresa") or estado == "impresa" or foto:
        h |= {"laminada", "impresa"}
    if estado in ("laminada", "impresa", "en_tienda") or any(a.endswith(G_CODE) for a in archivos):
        h.add("laminada")
    if p.get("en_tienda") or estado == "en_tienda":
        h.add("en_tienda")
    return h


def grupo_de(p: dict) -> str:
    """pendiente (idea), en_proceso o terminada. Imprimirla antes de publicarla es opcional (0.1.39): una pieza
    publicada en la tienda está terminada aunque no esté impresa; se imprime cuando la compren."""
    h = hechos(p)
    if h == {"idea"}:
        return "pendiente"
    return "terminada" if "impresa" in h or estado_publicacion(p) == "publicada" else "en_proceso"


def siguiente(p: dict) -> str | None:
    """Lo que falta hacer, en una frase (None si está terminada)."""
    h = hechos(p)
    if h == {"idea"}:
        return "Diseñarla: /taller-3d:pieza (lista para imprimir) o /taller-3d:diseno (solo el modelo)."
    if "laminada" not in h:
        return "Dejarla lista para imprimir en tu impresora: /taller-3d:pieza."
    if "impresa" not in h:
        estado = estado_publicacion(p)
        if estado == "publicada":
            return None
        if estado == "borrador" or "en_tienda" in h:
            return "Revisar el borrador en tu tienda y publicarlo. Imprimirla puede esperar a que te la compren."
        if estado == "vista_previa":
            return ("Ver cómo queda su publicación (en Publicaciones) y cargarla en la tienda con «Publicar»: queda como "
                    "borrador. O imprimirla antes.")
        return ("Imprimirla: pasá el G-code a la impresora (abrí el .3mf para verla en Orca) y después "
                "contale a Claude cómo salió.")
    return None


def quien_sigue(p: dict) -> str | None:
    """A quién le toca el paso que sigue: "claude" (se lo pedís y lo hace), "vos" (imprimirla o publicarla) o None."""
    h = hechos(p)
    if h == {"idea"} or "laminada" not in h:
        return "claude"
    return "vos" if siguiente(p) else None


def _en_una_linea(texto, largo: int = 80) -> str:
    """Un nombre para meter en un pedido: una sola línea, sin caracteres de control y corto."""
    limpio = re.sub(r"[\x00-\x1f\x7f\u2028\u2029«»]+", " ", str(texto or ""))
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return limpio if len(limpio) <= largo else limpio[:largo - 1].rstrip() + "…"


ABRIR_EN_ORCA = "Abrila en Orca"
PUBLICAR = "Publicar"
# El botón de arriba del panel: las fotos no se pueden mandar desde la página, se adjuntan en el chat.
PEDIDO_FOTO = "Quiero una pieza a partir de una foto: te la adjunto en el chat."
# Otro botón de arriba: un STL que el usuario ya tiene (suyo o bajado) sigue el mismo circuito, sin modelar.
PEDIDO_STL = "Quiero hacer una pieza con un STL que ya tengo: te lo adjunto en el chat o te digo dónde está."
# De dónde salió el modelo de una pieza (lo que no es "diseñada acá" se muestra en la tarjeta).
ORIGENES = {"diseno": "Diseñada por Claude", "stl_propio": "STL tuyo", "stl_descargado": "STL de internet",
            "foto": "Desde una foto"}
# Los botones que arrancan una pieza: el panel les suma la impresora elegida arriba («Impresora: «X».») o, con
# «Que me pregunte Claude», «Preguntame en qué impresora.». Con una sola impresora no suman nada.
CON_IMPRESORA = {"Diseñala", "Dejala lista para imprimir"}
# El servidor MCP local que abre Orca (instalador/abrir_orca.py), como lo nombra la página del panel en la app.
SERVIDOR_ORCA = "host:taller3d-orca"
# El que carga la publicación en la tienda, siempre como borrador (instalador/tienda_mcp.py).
SERVIDOR_TIENDA = "host:taller3d-tienda"
RE_PROYECTO = re.compile(r"^(?:impresiones|disenos)/\d{4}-\d{2}-\d{2}_[^/\\]+/[^/\\]+\.3mf$")


def proyecto_de(p: dict) -> str | None:
    """El proyecto de Orca (.3mf) de la pieza, relativo a la carpeta de trabajo: el que abre "Abrila en Orca"."""
    for archivo in p.get("archivos") or []:
        ruta = f"{p.get('carpeta')}/{archivo}"
        if (isinstance(archivo, str) and not archivo.lower().endswith(".gcode.3mf") and RE_PROYECTO.match(ruta)
                and ".." not in ruta.split("/") and not re.search(r"[\x00-\x1f\x7f]", ruta)):
            return ruta
    return None


def acciones(p: dict) -> list[tuple[str, str]]:
    """Los botones de la tarjeta: (etiqueta, pedido a Claude). El pedido nombra la pieza y su carpeta.

    El nombre va en una sola línea y recortado: puede venir de un modelo bajado de internet, y el pedido le llega
    a Claude como si lo escribiera el usuario. La orden es el verbo del botón; el nombre y la carpeta son datos."""
    carpeta = _en_una_linea(p["carpeta"], 160)
    nombre = _en_una_linea(p.get("nombre")) or carpeta
    cual = f"«{nombre}» ({carpeta})"
    h = hechos(p)
    if h == {"idea"}:
        return [("Diseñala", f"Desde el panel: diseñá la idea {cual} y dejala lista para imprimir."),
                ("Solo el modelo", f"Desde el panel: hacé solo el modelo 3D de la idea {cual}, sin laminar.")]
    botones = []
    if "laminada" not in h:
        botones.append(("Dejala lista para imprimir", f"Desde el panel: dejá {cual} lista para imprimir."))
    elif "impresa" not in h:
        botones += [(ABRIR_EN_ORCA, f"Desde el panel: abrí {cual} en Orca para que la vea."),
                    ("Ya la imprimí", f"Desde el panel: ya imprimí {cual}. Marcala como impresa y preguntame cómo salió.")]
    # «Publicar» no espera a la impresión (0.1.39): hay piezas que el usuario sabe que andan, o un STL que ya probó.
    # Queda en la tarjeta hasta que la pieza está en la tienda (0.1.40): sin publicación, la arma; con la publicación
    # armada (vista previa), la carga como borrador, igual que «Cargala como borrador» de Publicaciones.
    publicacion = estado_publicacion(p)
    if "en_tienda" not in h and not publicacion:
        if "impresa" in h:
            pedido = f"Desde el panel: armá la publicación de {cual} para la tienda."
        elif "laminada" in h:
            pedido = f"Desde el panel: armá la publicación de {cual} para la tienda, sin imprimirla antes."
        else:
            pedido = (f"Desde el panel: armá la publicación de {cual} para la tienda, sin imprimirla antes. "
                      "Laminala solo para sacar el tiempo, los gramos y el costo.")
        botones.append((PUBLICAR, pedido))
    elif "en_tienda" not in h and publicacion == "vista_previa":
        botones.append((PUBLICAR, f"Desde el panel: cargá como borrador en la tienda la publicación de {cual}."))
    elif "impresa" in h:
        botones.append(("Revisá el precio", f"Desde el panel: revisá el precio de {cual}."))
    return botones


def _rutas_del_listado(listado) -> list[str]:
    if isinstance(listado, dict):
        entradas = listado.get("entries") or []
        return [str(e.get("name", "")) for e in entradas if isinstance(e, dict) and e.get("type") == "file"]
    if isinstance(listado, list):
        return [str(x.get("name", "")) if isinstance(x, dict) else str(x) for x in listado]
    return []


def desde_listado(catalogo: dict, listado) -> list[str]:
    """Suma las carpetas de piezas que hay en el listado y todavía no están. Devuelve las nuevas."""
    por_carpeta: dict[str, list[str]] = {}
    for ruta in _rutas_del_listado(listado):
        r = ruta.replace("\\", "/").strip("/")
        m = re.match(r"^((?:impresiones|disenos)/\d{4}-\d{2}-\d{2}_[^/]+)/(.+)$", r)
        if m:
            por_carpeta.setdefault(m.group(1), []).append(m.group(2))
    existentes = {p.get("carpeta") for p in catalogo["piezas"]}
    nuevas = []
    for carpeta, archivos in sorted(por_carpeta.items()):
        estado = "disenada"
        if any(a.lower().endswith((".gcode", ".gco", ".gcode.3mf")) for a in archivos):
            estado = "laminada"
        en_producto = {a.lower() for a in archivos if a.lower().startswith("producto/")}
        armada = bool(en_producto & {"producto/publicacion.json", VISTA_PUBLICACION})
        if en_producto and not armada:                    # producto.json de antes de la 0.1.30
            estado = "en_tienda"
        impresa = any(es_foto_impresa(a) for a in archivos)   # una foto de la pieza impresa
        if carpeta in existentes:
            pieza = agregar(catalogo, carpeta, archivos=archivos, impresa=impresa or None)
        else:
            pieza = agregar(catalogo, carpeta, archivos=archivos, estado=estado, impresa=impresa or None)
            nuevas.append(carpeta)
        if armada and not isinstance(pieza.get("publicacion"), dict):
            pieza["publicacion"] = {"vista": VISTA_PUBLICACION} if VISTA_PUBLICACION in en_producto else {}
    return nuevas


def imagen_de(pieza: dict) -> str | None:
    """Una foto real si la hay; si no, la foto de producto de Blender; si no, la vista; si no, la ilustrativa."""
    if pieza.get("imagen"):
        return pieza["imagen"]
    archivos = pieza.get("archivos") or []
    imagenes = [a for a in archivos if a.lower().endswith(IMAGENES)]
    for criterio in (es_foto_impresa,
                     lambda a: a.lower().endswith("producto-1-principal.jpg"),
                     lambda a: a.lower() == "vista.png",
                     lambda a: "/" not in a and a.lower().startswith("vista"),
                     lambda a: a.lower().endswith("foto_producto.png")):
        elegida = next((a for a in imagenes if criterio(a)), None)
        if elegida:
            return elegida
    return "vista.png" if not archivos else (imagenes[0] if imagenes else None)


def _imagen_publicada(src) -> str | None:
    """En la página de claude.ai, solo imágenes propias de la página (ruta relativa) o datos de imagen."""
    if not isinstance(src, str) or not src:
        return None
    if src.startswith("data:image/"):
        return src
    if re.match(r"^[a-z][a-z0-9+.-]*:", src, re.I) or src.startswith(("/", "\\")) or ".." in src.split("/"):
        return None
    return src


def _href(carpeta: str, archivo: str) -> str:
    return "/".join(quote(p) for p in f"{carpeta}/{archivo}".split("/"))


_numero = comun.numero_es


def _plata(dato: dict | None) -> str | None:
    if not dato:
        return None
    valor = dato.get("total", dato.get("valor"))
    if valor in (None, ""):
        return None
    return comun.plata(valor, dato.get("moneda") or "") or f"{dato.get('moneda') or ''} {valor}".strip()


ESTILO = """
:root{--papel:#F5F1E8;--tinta:#1A1A1E;--suave:#4A4740;--borde:#D9D3C7;--acento:#E8590C}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:32px 24px 8px;max-width:1200px;margin:0 auto}
h1{margin:0;font-size:34px;letter-spacing:-.02em}
.sub{margin:6px 0 0;color:var(--suave)}
.controles{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 4px}
.controles input{flex:1 1 260px;min-height:44px;padding:8px 14px;border:1.5px solid var(--tinta);border-radius:10px;font:inherit;background:#fff}
.controles button{min-height:44px;padding:8px 14px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;font:inherit;cursor:pointer}
.controles button[aria-pressed="true"]{background:var(--tinta);color:#fff}
main{max-width:1200px;margin:0 auto;padding:8px 24px 48px}
h2{margin:28px 0 12px;font-size:20px}
.grilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
article{background:#fff;border:1.5px solid var(--tinta);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.imagen{aspect-ratio:4/3;background:#EFEAE0;display:flex;align-items:center;justify-content:center;border-bottom:1.5px solid var(--tinta)}
.imagen img{width:100%;height:100%;object-fit:contain}
.sin{color:var(--suave);font-size:14px}
.cuerpo{padding:12px 14px 14px;display:flex;flex-direction:column;gap:8px}
h3{margin:0;font-size:18px;line-height:1.25}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:13px;padding:2px 8px;border-radius:6px;border:1px solid var(--borde);background:var(--papel)}
.chip.estado{background:var(--acento);border-color:var(--tinta);color:var(--tinta)}
dl{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:0;font-size:14px}
dt{color:var(--suave)}dd{margin:0}
.archivos{display:flex;flex-wrap:wrap;gap:6px;font-size:13px}
.archivos a{color:var(--tinta);padding:2px 8px;border:1px solid var(--tinta);border-radius:6px;text-decoration:none;font-family:ui-monospace,Consolas,monospace}
.archivos a:hover{background:var(--papel)}
.nota{font-size:14px;color:var(--suave);margin:0}
.ubicacion{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--suave);word-break:break-all}
footer{max-width:1200px;margin:0 auto;padding:0 24px 32px;color:var(--suave);font-size:13px}
.vacio{padding:40px 0;color:var(--suave)}
.contadores{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0;padding:0;list-style:none}
.contadores li{padding:6px 12px;border:1.5px solid var(--tinta);border-radius:10px;background:#fff;font-size:15px}
.contadores strong{font-size:20px;margin-right:4px}
.camino{display:flex;gap:3px;margin:0;padding:0;list-style:none;font-size:11px;line-height:1.2}
.camino li{flex:1;padding-top:6px;border-top:5px solid var(--borde);color:var(--suave);text-align:center}
.camino li.hecho{border-top-color:var(--tinta);color:var(--tinta)}
.camino li.actual{border-top-color:var(--acento);font-weight:700}
.sigue{margin:0;font-size:14px;padding:6px 8px;border-left:4px solid var(--acento);background:var(--papel)}
.terminada{margin:0;font-size:14px;color:var(--suave)}
.imagen.vacia{aspect-ratio:auto;padding:18px 12px}
.sigue.vos{border-left-color:var(--tinta)}
.taller{margin:16px 0 0;background:#fff;border:1.5px solid var(--tinta);border-radius:14px;padding:10px 14px}
.taller summary{cursor:pointer;font-weight:700;min-height:28px}
.taller ul{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:8px}
.taller li{display:grid;grid-template-columns:22px 1fr;gap:4px 8px;align-items:start;font-size:14px}
.taller li button{grid-column:2;justify-self:start;min-height:36px;padding:4px 12px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;font:inherit;font-size:13px;cursor:pointer}
.taller form.dato{grid-column:2;display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.taller form.dato input{width:7em;min-height:36px;padding:4px 8px;border:1.5px solid var(--tinta);border-radius:8px;font:inherit;background:#fff}
.taller form.dato input.palabra{width:12em}
.taller .marca{font-weight:700;text-align:center}
.taller .falta .marca{color:#B3261E}.taller .revisar .marca{color:var(--acento)}
.idea .imagen{background:var(--papel)}
.idea .imagen span{font-size:15px;color:var(--suave)}
.acciones{display:flex;flex-wrap:wrap;gap:6px}
.acciones button,form.idea button,.desde-foto button{min-height:40px;padding:6px 12px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;color:var(--tinta);font:inherit;font-size:14px;cursor:pointer}
.acciones button:first-child,form.idea button{background:var(--tinta);color:#fff}
.acciones button:disabled,form.idea button:disabled,.desde-foto button:disabled{opacity:.55;cursor:progress}
.acciones .solo-claude{display:none}
.acciones a.boton{display:inline-flex;align-items:center;min-height:40px;padding:6px 12px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;color:var(--tinta);font-size:14px;text-decoration:none}
.acciones a.boton:first-child{background:var(--tinta);color:#fff}
.estado-publi{margin:0;font-size:14px;font-weight:600}
.estado-publi::before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;border:1.5px solid var(--tinta);background:#fff}
.estado-publi.borrador::before{background:var(--acento)}
.estado-publi.publicada::before{background:var(--tinta)}
body.con-claude .acciones .solo-claude{display:inline-block}
.aviso{margin:0;font-size:13px;color:var(--suave)}
.aviso:empty{display:none}
.modo{margin:12px 0 0;font-size:14px;color:var(--suave)}
form.idea{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}
.desde-foto{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:10px 0 0}
.desde-foto span{font-size:14px;color:var(--suave)}
.impresora{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:14px 0 0;font-size:15px}
.impresora label{font-weight:700}
.impresora select{min-height:40px;padding:6px 10px;border:1.5px solid var(--tinta);border-radius:10px;font:inherit;background:#fff;color:var(--tinta)}
.impresora span{font-size:14px;color:var(--suave)}
form.idea input{flex:1 1 240px;min-height:44px;padding:8px 14px;border:1.5px solid var(--tinta);border-radius:10px;font:inherit;background:#fff}
.archivos span{padding:2px 8px;border:1px solid var(--borde);border-radius:6px;font-family:ui-monospace,Consolas,monospace}
[hidden]{display:none!important}
@media print{.controles,.acciones,form.idea,.desde-foto,div.impresora{display:none}article{break-inside:avoid}}
"""

GUION = """
(function(){
  var buscar=document.getElementById('buscar'),filtro='todo';
  var botones=document.querySelectorAll('[data-filtro]');
  function aplicar(){
    var q=(buscar.value||'').toLowerCase().trim();
    document.querySelectorAll('section[data-seccion]').forEach(function(s){
      var visibles=0;
      s.querySelectorAll('article').forEach(function(a){
        var ok=(filtro==='todo'||a.getAttribute('data-grupo')===filtro)
          &&(!q||a.getAttribute('data-texto').indexOf(q)>=0);
        a.hidden=!ok; if(ok){visibles++;}
      });
      s.hidden=visibles===0;
    });
  }
  buscar.addEventListener('input',aplicar);
  botones.forEach(function(b){b.addEventListener('click',function(){
    filtro=b.getAttribute('data-filtro');
    botones.forEach(function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
    aplicar();
  });});
  document.querySelectorAll('.imagen img').forEach(function(i){i.addEventListener('error',function(){
    var s=document.createElement('span');s.className='sin';s.textContent='Sin vista';i.replaceWith(s);
  });});

  // Botones: en claude.ai le mandan el pedido a Claude (despierta al chat); si no, lo copian para pegarlo.
  var modo=document.getElementById('modo'),com=null;
  function lugar(el){return el.closest('article')||el.closest('details')||el.closest('header');}
  function avisar(el,texto){var a=lugar(el).querySelector('.aviso');if(a){a.textContent=texto;}}
  var adjuntos={stl:'el STL (o decile en qué carpeta está)'};
  function adjunto(el){return adjuntos[el.getAttribute('data-adjuntar')]||'la foto (si tenés varias de distintos ángulos, mejor)';}
  function foto(el){return el.hasAttribute('data-adjuntar')?' y adjuntá '+adjunto(el):'';}
  function copiar(el,texto){
    function mostrar(){avisar(el,'Copiá este pedido y pegalo en el chat con Claude'+foto(el)+': '+texto);}
    try{navigator.clipboard.writeText(texto).then(function(){
      avisar(el,'Pedido copiado: pegalo en el chat con Claude'+foto(el)+'.');},mostrar);}catch(e){mostrar();}
  }
  var motivos={consent_required:'falta que permitas que el panel le escriba a Claude por vos',
    claude_unavailable:'no hay un chat de Claude que lo reciba ahora',rate_limited:'fueron muchos seguidos; esperá un momento',
    forbidden:'solo vos podés pedirle cosas a Claude desde tu panel'};
  function pedir(el,texto){
    if(!com){copiar(el,texto);return;}
    el.disabled=true;avisar(el,'Enviando a Claude…');
    com.canSendToClaude().then(function(estado){
      if(estado!=='available'){el.disabled=false;copiar(el,texto);return;}
      return com.anchorFor(lugar(el)).then(function(ancla){return com.sendToClaude({anchor:ancla,text:texto});})
        .then(function(){avisar(el,el.hasAttribute('data-adjuntar')?
                'Enviado. Ahora, en el chat con Claude, adjuntá '+adjunto(el)+'.':
                'Enviado. Claude lo hace y te contesta en el chat.');},
              function(err){var c=err&&err.code;
                avisar(el,'No se envió: '+(motivos[c]||'algo falló ('+(c||'error')+')')+'. Si querés, pegalo en el chat: '+texto);});
    }).catch(function(){copiar(el,texto);}).then(function(){el.disabled=false;});
  }
  // "Abrila en Orca": si la app de Claude deja que la página use el servidor local taller3d-orca de la PC, Orca se
  // abre sin pasar por el chat; si no (navegador, celular, sin el servidor), el pedido va a Claude como los demás.
  var SERVIDOR_ORCA='host:taller3d-orca',orca=null;     // = SERVIDOR_ORCA de catalogo.py
  function abrirEnOrca(el,ruta,texto){
    if(!orca){pedir(el,texto);return;}
    el.disabled=true;avisar(el,'Abriendo Orca en tu PC…');
    orca.callTool(SERVIDOR_ORCA,'abrir_en_orca',{ruta:ruta},{cache:false}).then(function(r){
      var p=r&&r.payload;avisar(el,(p&&p.mensaje)||'Listo: se abre Orca con la pieza.');el.disabled=false;
    },function(err){
      var c=err&&err.code,p=err&&err.result&&err.result.structuredContent;el.disabled=false;
      if(c==='tool_error'){avisar(el,'No la abrí: '+((p&&p.mensaje)||'Orca no la pudo abrir.'));}
      else if(c==='cancelled'){avisar(el,'No la abrí: no lo confirmaste en la app de Claude.');}
      else if(c==='server_unavailable'||c==='upstream_error'||c==='rate_limited'){
        avisar(el,'No sé si se abrió: la app no contestó. Si no aparece Orca, tocá de nuevo.');}
      else{orca=null;pedir(el,texto);}          // nunca llegó a la PC: se lo pido a Claude
    });
  }
  // "Cargala como borrador": si la app de Claude deja que la página use el servidor local taller3d-tienda de la PC,
  // el producto se carga en la tienda (siempre como borrador) sin pasar por el chat, y después se le avisa a Claude
  // para que lo anote en el panel; si no (navegador, celular, sin el servidor), el pedido va a Claude.
  var SERVIDOR_TIENDA='host:taller3d-tienda',tienda=null;  // = SERVIDOR_TIENDA de catalogo.py
  function enlazar(el,url,texto){
    var a=lugar(el).querySelector('.aviso');if(!a||(url||'').indexOf('https://')!==0){return;}
    var l=document.createElement('a');l.href=url;l.target='_blank';l.rel='noopener noreferrer';l.textContent=texto;
    a.appendChild(document.createTextNode(' '));a.appendChild(l);
  }
  function cargarEnTienda(el,carpeta,texto,anotar){
    if(!tienda){pedir(el,texto);return;}
    el.disabled=true;avisar(el,'Cargando en tu tienda, como borrador…');
    tienda.callTool(SERVIDOR_TIENDA,'cargar_borrador',{carpeta:carpeta},{cache:false}).then(function(r){
      var p=(r&&r.payload)||{};el.disabled=false;
      avisar(el,p.mensaje||'Listo: quedó como borrador en tu tienda.');
      enlazar(el,p.enlace_admin,'Abrir el borrador');
      if(p.cargado&&anotar&&com){com.canSendToClaude().then(function(estado){
        if(estado!=='available'){return;}
        return com.anchorFor(lugar(el)).then(function(ancla){return com.sendToClaude({anchor:ancla,text:anotar});});
      }).catch(function(){});}
    },function(err){
      var c=err&&err.code,p=err&&err.result&&err.result.structuredContent;el.disabled=false;
      if(c==='tool_error'){avisar(el,'No la cargué: '+((p&&p.mensaje)||'la tienda no la aceptó.'));}
      else if(c==='cancelled'){avisar(el,'No la cargué: no lo confirmaste en la app de Claude.');}
      else if(c==='server_unavailable'||c==='upstream_error'||c==='rate_limited'){
        avisar(el,'No sé si se cargó: la app no contestó. Fijate en tu tienda antes de tocar de nuevo.');}
      else{tienda=null;pedir(el,texto);}         // nunca llegó a la PC: se lo pido a Claude
    });
  }
  // La impresora de arriba: los botones que arrancan una pieza (data-impresora) le dicen a Claude en cuál. La
  // elegida se recuerda en este navegador si se puede; si ya no está entre las opciones, queda la que puso Claude.
  var selector=document.getElementById('impresora'),CLAVE='taller3d.impresora';
  if(selector&&selector.tagName==='SELECT'){
    try{var guardada=window.localStorage.getItem(CLAVE);
      if(guardada!==null&&[].some.call(selector.options,function(o){return o.value===guardada;})){selector.value=guardada;}
    }catch(e){}
    selector.addEventListener('change',function(){try{window.localStorage.setItem(CLAVE,selector.value);}catch(e){}});
  }else{selector=null;}
  function conImpresora(el,texto){
    if(!selector||!el.hasAttribute('data-impresora')){return texto;}
    return texto+(selector.value?' Impresora: «'+selector.value+'».':' Preguntame en qué impresora.');
  }
  document.querySelectorAll('[data-pedido]').forEach(function(b){
    b.addEventListener('click',function(){
      var ruta=b.getAttribute('data-orca'),carpeta=b.getAttribute('data-tienda');
      if(ruta){abrirEnOrca(b,ruta,b.getAttribute('data-pedido'));}
      else if(carpeta){cargarEnTienda(b,carpeta,b.getAttribute('data-pedido'),b.getAttribute('data-anotar'));}
      else{pedir(b,conImpresora(b,b.getAttribute('data-pedido')));}
    });
  });
  if(window.claude&&typeof window.claude.use==='function'&&document.querySelector('[data-orca]')){
    window.claude.use('mcp').then(function(m){
      if(!m){return;}
      return m.listTools(SERVIDOR_ORCA).then(function(r){   // fuera de la app de escritorio no aparece
        if(((r&&r.servers)||[]).some(function(s){return s.server===SERVIDOR_ORCA;})){orca=m;}
      });
    }).catch(function(){});
  }
  if(window.claude&&typeof window.claude.use==='function'&&document.querySelector('[data-tienda]')){
    window.claude.use('mcp').then(function(m){
      if(!m){return;}
      return m.listTools(SERVIDOR_TIENDA).then(function(r){
        if(((r&&r.servers)||[]).some(function(s){return s.server===SERVIDOR_TIENDA;})){tienda=m;}
      });
    }).catch(function(){});
  }
  document.querySelectorAll('[data-comentar]').forEach(function(b){b.addEventListener('click',function(){
    if(com){com.openComposer({element:lugar(b)}).catch(function(){});}
  });});
  // «Tu taller»: los datos con número (un monto, un porcentaje) se completan acá y recién ahí se mandan.
  document.querySelectorAll('form.dato').forEach(function(f){f.addEventListener('submit',function(ev){
    ev.preventDefault();
    var vacio=[].some.call(f.querySelectorAll('input'),function(i){return !i.value.trim();});
    if(vacio){avisar(f,'Completá el dato y tocá de nuevo.');return;}
    var texto=[].map.call(f.querySelectorAll('.t,input'),function(n){
      return n.tagName==='INPUT'?n.value.trim():n.textContent;}).join('');
    pedir(f.querySelector('button'),texto);
  });});
  var idea=document.getElementById('idea');
  if(idea){idea.addEventListener('submit',function(ev){
    ev.preventDefault();var campo=idea.querySelector('input'),t=campo.value.trim();
    if(t){pedir(idea.querySelector('button'),'Desde el panel: anotá esta idea para más adelante: '+t);campo.value='';}
  });}
  function sinClaude(texto){modo.textContent=texto||'Los botones copian el pedido para que lo pegues en el chat con Claude.';}
  if(window.claude&&typeof window.claude.use==='function'){
    window.claude.use('comments').then(function(c){
      if(!c){sinClaude();return;}
      return c.canSendToClaude().then(function(estado){
        com=c;document.body.classList.toggle('con-claude',estado==='available');
        if(estado==='available'){sinClaude('Los botones le piden las cosas a Claude, que las hace en el chat.');}
        else if(estado==='no_session'){sinClaude('Ahora no hay un chat de Claude escuchando: pedí /panel en el chat del taller. Mientras, los botones copian el pedido.');}
        else{sinClaude();}
      });
    }).catch(function(){sinClaude();});
  }else{sinClaude();}
})();
"""


def _tarjeta(p: dict, modo: str = "archivo", imagenes: dict | None = None) -> str:
    """modo archivo: panel.html en la carpeta de trabajo (vistas y archivos por ruta relativa).
    modo claude: la página de claude.ai, sin acceso a la PC (las imágenes vienen en `imagenes`, carpeta → ruta)."""
    e = html.escape
    carpeta = str(p["carpeta"])
    nombre = str(p.get("nombre") or carpeta)
    es_idea = p.get("tipo") == "idea"
    if modo == "claude":
        src = _imagen_publicada((imagenes or {}).get(carpeta))
    else:
        imagen = None if es_idea else imagen_de(p)
        src = _href(carpeta, imagen) if imagen else None
    if es_idea:
        img = '<span>Idea anotada, sin diseño todavía</span>'
    elif src:
        img = f'<img src="{e(src)}" alt="{e("Vista de " + nombre)}" loading="lazy">'
    else:
        img = '<span class="sin">Sin vista</span>'
    chips = [f'<span class="chip">{e(TIPOS.get(p.get("tipo"), "Pieza"))}</span>']
    if p.get("material"):
        material = p["material"] + (f' {p["color"]}' if p.get("color") else "")
        chips.append(f'<span class="chip">{e(material)}</span>')
    if p.get("origen") in ORIGENES and p["origen"] != "diseno":
        licencia = f' · {_en_una_linea(p["licencia"], 40)}' if p.get("licencia") else ""
        chips.append(f'<span class="chip">{e(ORIGENES[p["origen"]] + licencia)}</span>')
    h = hechos(p)
    ultimo = max((i for i, (clave, _) in enumerate(PASOS) if clave in h), default=0)
    camino = "".join(f'<li class="{"hecho" if clave in h else ""}{" actual" if i == ultimo else ""}"'
                     f'{" aria-current=\"step\"" if i == ultimo else ""}>{e(etiqueta)}</li>'
                     for i, (clave, etiqueta) in enumerate(PASOS))
    sigue = siguiente(p)
    quien = {"vos": "Te toca", "claude": "Le toca a Claude"}.get(quien_sigue(p) or "", "Sigue")
    if sigue:
        paso = f'<p class="sigue {e(quien_sigue(p) or "")}"><strong>{quien}:</strong> {e(sigue)}</p>'
    elif "impresa" not in h:                             # publicada sin imprimirla antes
        paso = '<p class="terminada">En la tienda, sin imprimir: cuando te la compren, el G-code ya está listo.</p>'
    else:
        paso = '<p class="terminada">Terminada.</p>'
    filas = []
    if p.get("impresora"):
        filas.append(("Impresora", p["impresora"]))
    if p.get("medidas_mm"):
        filas.append(("Medidas", " × ".join(_numero(x) for x in p["medidas_mm"]) + " mm"))
    if p.get("tiempo"):
        filas.append(("Tiempo", p["tiempo"]))
    if p.get("gramos"):
        filas.append(("Filamento", f'{_numero(p["gramos"])} g'))
    if _plata(p.get("costo")):
        filas.append(("Costo", _plata(p["costo"])))
    if _plata(p.get("precio")):
        filas.append(("Precio", _plata(p["precio"])))
    if p.get("revision"):
        filas.append(("Revisión", {"aprobado": "aprobada", "advertencia": "con avisos"}.get(p["revision"], p["revision"])))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>" for k, v in filas)
    archivos = [a for a in (p.get("archivos") or []) if not a.lower().endswith(IMAGENES) and "/" not in a
                or a.lower().endswith((".gcode", ".gco", ".gcode.3mf"))]
    if modo == "claude":                                 # los archivos están en la PC: solo el nombre
        enlaces = "".join(f'<span>{e(a.rsplit("/", 1)[-1])}</span>' for a in archivos[:8])
    else:
        enlaces = "".join(f'<a href="{e(_href(carpeta, a))}">{e(a.rsplit("/", 1)[-1])}</a>' for a in archivos[:8])
    tienda = url_segura(p.get("url_tienda")) if isinstance(p.get("url_tienda"), str) else None
    if tienda:                                           # se revisa también acá: el índice se puede tocar a mano
        enlaces += f'<a href="{e(tienda)}" rel="noopener noreferrer">en la tienda</a>'
    # En claude.ai, "Abrila en Orca" lleva su .3mf (relativo a la carpeta de trabajo, sin rutas de la PC): la página
    # le pide a la app de Claude que lo abra con el servidor local taller3d-orca; si no puede, se lo pide a Claude.
    proyecto = proyecto_de(p) if modo == "claude" else None
    # «Publicar» de una pieza sin laminar también arranca un laminado: lleva la impresora de arriba.
    publicacion = estado_publicacion(p)
    # Con la publicación armada, «Publicar» la carga como borrador: en claude.ai lleva la carpeta, como «Cargala como
    # borrador» de Publicaciones, para que la página la cargue con taller3d-tienda sin pasar por el chat (0.1.40).
    cargar = ""
    if modo == "claude" and publicacion == "vista_previa":
        cual = f"«{_en_una_linea(nombre) or _en_una_linea(carpeta, 160)}» ({_en_una_linea(carpeta, 160)})"
        anotar = ("Desde el panel: el conector de la tienda cargó como borrador la publicación de " + cual +
                  ". Anotalo en el panel.")
        cargar = f' data-tienda="{e(_en_una_linea(carpeta, 160))}" data-anotar="{e(anotar)}"'
    botones = "".join(f'<button type="button" data-pedido="{e(pedido)}"'
                      + (f' data-orca="{e(proyecto)}"' if proyecto and etiqueta == ABRIR_EN_ORCA else "")
                      + (cargar if etiqueta == PUBLICAR else "")
                      + (" data-impresora" if etiqueta in CON_IMPRESORA
                         or etiqueta == PUBLICAR and "laminada" not in h and not publicacion else "")
                      + f'>{e(etiqueta)}</button>' for etiqueta, pedido in acciones(p))
    botones += '<button type="button" class="solo-claude" data-comentar>Otra cosa…</button>'
    fecha = p.get("fecha") or ""
    texto = " ".join(str(x) for x in (nombre, p.get("material"), p.get("color"), p.get("impresora"), p.get("nota"),
                                      carpeta) if x).lower()
    clase = ' class="idea"' if es_idea else ""
    ubicacion = f"anotada el {fecha}" if es_idea else f"{carpeta} · {fecha}"
    return f"""<article{clase} data-tipo="{e(p.get('tipo') or '')}" data-grupo="{e(grupo_de(p))}" data-texto="{e(texto)}">
<div class="imagen{'' if src and not es_idea else ' vacia'}">{img}</div>
<div class="cuerpo">
<h3>{e(nombre)}</h3>
<ol class="camino" aria-label="Recorrido">{camino}</ol>
{paso}
<div class="acciones">{botones}</div>
<p class="aviso" role="status" aria-live="polite"></p>
<div class="chips">{''.join(chips)}</div>
{f'<dl>{dl}</dl>' if dl else ''}
{f'<p class="nota">{e(str(p["nota"]))}</p>' if p.get("nota") else ''}
{f'<div class="archivos">{enlaces}</div>' if enlaces else ''}
<div class="ubicacion">{e(ubicacion)}</div>
</div>
</article>"""


def _publicacion(p: dict, modo: str = "archivo", imagenes: dict | None = None) -> str:
    """La tarjeta de una publicación: foto, título, precio, ganancia, dónde está y los botones para verla,
    cargarla o cambiarla. Los pedidos van como los de las piezas: el verbo es la orden, el nombre y la carpeta, datos."""
    e = html.escape
    pub = p.get("publicacion") if isinstance(p.get("publicacion"), dict) else {}
    carpeta = str(p["carpeta"])
    nombre = str(p.get("nombre") or carpeta)
    titulo = str(pub.get("titulo") or nombre)
    estado = estado_publicacion(p) or "vista_previa"
    if modo == "claude":
        src = _imagen_publicada((imagenes or {}).get(carpeta))
    else:
        foto = pub.get("foto") if isinstance(pub.get("foto"), str) and ".." not in pub["foto"].split("/") else None
        foto = foto or imagen_de(p)
        src = _href(carpeta, foto) if foto else None
    img = (f'<img src="{e(src)}" alt="{e("Foto de " + titulo)}" loading="lazy">' if src
           else '<span class="sin">Sin foto</span>')
    precio = pub.get("precio") if isinstance(pub.get("precio"), dict) else (p.get("precio") or {})
    filas = []
    if _plata(precio):
        filas.append(("Precio", _plata(precio) + (" con IVA" if precio.get("con_iva") else "")))
    ganancia = pub.get("ganancia") if isinstance(pub.get("ganancia"), dict) else None
    if ganancia and _plata({"valor": ganancia.get("valor"), "moneda": precio.get("moneda")}):
        margen = ganancia.get("margen_pct")
        filas.append(("Ganancia", _plata({"valor": ganancia["valor"], "moneda": precio.get("moneda")})
                      + (f" ({_numero(margen)} %)" if margen is not None else "")))
    if pub.get("fotos"):
        reales = int(pub.get("fotos_reales") or 0)
        filas.append(("Fotos", f'{pub["fotos"]} ' + ("ilustrativas" if not reales else
                                                     "reales" if reales >= pub["fotos"] else f"({reales} reales)")))
    filas.append(("Pieza", nombre))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>" for k, v in filas)
    cual = f"«{_en_una_linea(nombre) or _en_una_linea(carpeta, 160)}» ({_en_una_linea(carpeta, 160)})"
    botones = []
    vista = pub.get("vista") if pub.get("vista") == VISTA_PUBLICACION else None
    if modo == "claude":
        botones.append(f'<button type="button" data-pedido="{e("Desde el panel: mostrame cómo queda la publicación de " + cual + ".")}">Ver cómo queda</button>')
    elif vista:
        botones.append(f'<a class="boton" href="{e(_href(carpeta, vista))}">Ver cómo queda</a>')
    if estado == "vista_previa":
        # En claude.ai lleva la carpeta: si la app deja que la página use taller3d-tienda, el producto se carga sin
        # pasar por el chat y después se le avisa a Claude para que lo anote; si no, el pedido va a Claude.
        cargar = ""
        if modo == "claude":
            anotar = ("Desde el panel: el conector de la tienda cargó como borrador la publicación de " + cual +
                      ". Anotalo en el panel.")
            cargar = f' data-tienda="{e(_en_una_linea(carpeta, 160))}" data-anotar="{e(anotar)}"'
        botones.append(f'<button type="button" data-pedido="{e("Desde el panel: cargá como borrador en la tienda la publicación de " + cual + ".")}"{cargar}>Cargala como borrador</button>')
    botones.append(f'<button type="button" data-pedido="{e("Desde el panel: quiero cambiar la publicación de " + cual + ". Preguntame qué.")}">Cambiar precio o texto</button>')
    tienda = url_segura(p.get("url_tienda")) if isinstance(p.get("url_tienda"), str) else None
    if tienda:
        botones.append(f'<a class="boton" href="{e(tienda)}" rel="noopener noreferrer">Abrir en la tienda</a>')
    texto = " ".join(str(x) for x in (titulo, nombre, carpeta, "publicación") if x).lower()
    return f"""<article class="publi" data-tipo="publicacion" data-grupo="publicacion" data-texto="{e(texto)}">
<div class="imagen{'' if src else ' vacia'}">{img}</div>
<div class="cuerpo">
<h3>{e(titulo)}</h3>
<p class="estado-publi {e(estado)}">{e(ESTADOS_PUBLICACION[estado])}</p>
<div class="acciones">{''.join(botones)}</div>
<p class="aviso" role="status" aria-live="polite"></p>
<dl>{dl}</dl>
<div class="ubicacion">{e(carpeta)}/producto</div>
</div>
</article>"""


def _taller(estado: list[dict] | None) -> str:
    """La caja "Tu taller": qué está listo para calcular costos y precios, y lo que falta, con su botón."""
    if not estado:
        return ""
    e = html.escape
    marcas = {"listo": "✓", "revisar": "!", "falta": "✗"}
    pendientes = [i for i in estado if i.get("estado") != "listo"]

    def boton(frase: str) -> str:
        # Con "…" en la frase (un monto, un porcentaje), el panel pide el dato y recién ahí lo manda: si no, a Claude
        # le llegaría «me costó $…» sin el número.
        if "…" not in frase:
            return f'<button type="button" data-pedido="{e(frase)}">Decíselo a Claude</button>'
        partes = frase.split("…")

        def campo(n: int) -> str:
            # Un número si va después de "$" o antes de "%" o "minutos"; si no, una palabra («monotributista»).
            numero = partes[n].rstrip().endswith("$") or partes[n + 1].lstrip().startswith(("%", "minutos", "min "))
            modo, clase = ("decimal", "") if numero else ("text", 'class="palabra" ')
            return (f'<input type="text" inputmode="{modo}" autocomplete="off" required {clase}'
                    f'aria-label="Dato {n + 1}">')
        campos = "".join(f'<span class="t">{e(t)}</span>' + (campo(n) if n < len(partes) - 1 else "")
                         for n, t in enumerate(partes))
        return f'<form class="dato">{campos}<button type="submit">Decíselo a Claude</button></form>'

    filas = "".join(
        f'<li class="{e(i.get("estado") or "")}"><span class="marca" aria-hidden="true">{marcas.get(i.get("estado"), "·")}</span>'
        f'<span><strong>{e(str(i.get("tema") or ""))}:</strong> {e(str(i.get("texto") or ""))}</span>'
        + (boton(str(i["frase"])) if i.get("frase") else "")
        + "</li>" for i in estado)
    titulo = ("Tu taller: todo listo para calcular costos y precios" if not pendientes else
              f"Tu taller: {len(pendientes)} dato{'s' if len(pendientes) != 1 else ''} para costos y precios")
    return (f'<details class="taller"{" open" if pendientes else ""}><summary>{e(titulo)}</summary>'
            f'<ul>{filas}</ul><p class="aviso" role="status" aria-live="polite"></p></details>')


def _selector(impresoras: list[dict] | None) -> str:
    """Arriba del panel, la impresora para lo que se pida (de comun.impresoras_para_elegir): los botones que arrancan
    una pieza le dicen a Claude en cuál. Con una sola no hay nada que elegir: dice cuál es."""
    e = html.escape
    lista = [(comun.una_linea(i.get("nombre")), i) for i in impresoras or [] if isinstance(i, dict)]
    lista = [(n, i) for n, i in lista if n]
    if not lista:
        return ""

    def texto(nombre, i):
        return nombre + ("" if i.get("preparada") else " · sin preparar")
    if len(lista) == 1:
        return f'<p class="impresora">Imprime en: <strong>{e(texto(*lista[0]))}</strong></p>'
    opciones = "".join(f'<option value="{e(n)}"{" selected" if i.get("defecto") else ""}>{e(texto(n, i))}</option>'
                       for n, i in lista)
    return ('<div class="impresora"><label for="impresora">Imprimir en</label>'
            f'<select id="impresora">{opciones}<option value="">Que me pregunte Claude</option></select>'
            '<span>La usan los botones que arrancan una pieza. La que elegís en la ventana de Orca no le llega a '
            'Claude.</span></div>')


def generar_html(catalogo: dict, titulo: str = "Panel del taller", modo: str = "archivo",
                 imagenes: dict | None = None, estado_taller: list[dict] | None = None,
                 impresoras: list[dict] | None = None) -> str:
    """modo archivo: panel.html para abrir desde la carpeta de trabajo; los botones copian el pedido.
    modo claude: la página que Claude publica en claude.ai y se abre al costado del chat; los botones le mandan
    el pedido a Claude. `imagenes`: carpeta de la pieza → ruta de su foto entre los archivos de la página.
    `impresoras` (de comun.impresoras_para_elegir): el selector de impresora de arriba."""
    e = html.escape
    if modo not in ("archivo", "claude"):
        raise ValueError(f"Modo desconocido: {modo}")
    piezas = [p for p in catalogo.get("piezas") or [] if isinstance(p, dict) and p.get("carpeta")]
    piezas = sorted(piezas, key=lambda p: (str(p.get("fecha") or ""), str(p.get("carpeta"))), reverse=True)
    # Para hacer: primero lo más avanzado (listas para imprimir, después diseños, al final las ideas)
    por_hacer = sorted((p for p in piezas if grupo_de(p) != "terminada"), key=_avance, reverse=True)
    terminadas = [p for p in piezas if grupo_de(p) == "terminada"]
    secciones = []
    if por_hacer:
        secciones.append(("hacer", "Para hacer", [_tarjeta(p, modo, imagenes) for p in por_hacer]))
    publicaciones = [p for p in piezas if estado_publicacion(p)]
    if publicaciones:                                    # cómo queda cada producto en la tienda, y dónde está
        secciones.append(("publicaciones", "Publicaciones", [_publicacion(p, modo, imagenes) for p in publicaciones]))
    for pieza in terminadas:
        clave = (pieza.get("fecha") or "")[:7]
        if not secciones or secciones[-1][0] != clave:
            try:
                etiqueta = f"Terminadas · {MESES[int(clave[5:7]) - 1]} {clave[:4]}"
            except (ValueError, IndexError):
                etiqueta = "Terminadas · sin fecha"
            secciones.append((clave, etiqueta, []))
        secciones[-1][2].append(_tarjeta(pieza, modo, imagenes))
    cuerpo = "\n".join(
        f'<section data-seccion="{e(clave)}"><h2>{e(etiqueta)}</h2><div class="grilla">\n' + "\n".join(tarjetas)
        + "\n</div></section>" for clave, etiqueta, tarjetas in secciones)
    if not piezas:
        cuerpo = ('<p class="vacio">Todavía no hay ideas ni piezas. Cada vez que Claude anote una idea o guarde una pieza, '
                  'aparece acá.</p>')
    cuenta = {g: sum(1 for p in piezas if grupo_de(p) == g) for g in GRUPOS}
    contadores = "".join(f"<li><strong>{cuenta[g]}</strong>{e(t.lower())}</li>" for g, t in GRUPOS.items())
    actualizado = (catalogo.get("actualizado") or _ahora())[:16].replace("T", " ")
    filtros = [("todo", "Todo")] + list(GRUPOS.items()) + ([("publicacion", "Publicaciones")] if publicaciones else [])
    botones = "".join(f'<button type="button" data-filtro="{f}" aria-pressed="{"true" if f == "todo" else "false"}">'
                      f'{e(t)}</button>' for f, t in filtros)
    # En claude.ai manda la política del sitio; una propia bloquearía el puente con Claude.
    politica = "" if modo == "claude" else (
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src * data: file:; '
        'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">\n')
    if modo == "claude":
        pie = ("Lo publica Claude cada vez que cambia algo, y se actualiza solo. Los archivos siguen en tu PC, en la "
               "carpeta de cada pieza. Es privado: lo ves solo vos, salvo que lo compartas.")
    else:
        pie = ("Lo arma taller-3d cada vez que Claude anota una idea o guarda una pieza. Abrilo desde tu carpeta de "
               "trabajo: las vistas y los archivos se cargan de la carpeta de cada pieza. Los botones copian el "
               "pedido para que lo pegues en el chat con Claude.")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{politica}<title>{e(titulo)}</title>
<style>{ESTILO}</style>
</head>
<body>
<header>
<h1>{e(titulo)}</h1>
<p class="sub">Tus ideas y piezas, y en qué paso está cada una · actualizado el {e(actualizado)}</p>
<ul class="contadores" aria-label="Resumen">{contadores}</ul>
<div class="controles">
<label for="buscar" hidden>Buscar</label>
<input id="buscar" type="search" placeholder="Buscar por nombre, impresora, material o nota" aria-label="Buscar por nombre, impresora, material o nota">
{botones}
</div>
<form class="idea" id="idea" autocomplete="off">
<label for="nueva-idea" hidden>Anotar una idea</label>
<input id="nueva-idea" type="text" maxlength="300" placeholder="Anotá una idea: «un soporte para la tele»" aria-label="Anotar una idea">
<button type="submit">Anotar idea</button>
</form>
{_selector(impresoras)}
<div class="desde-foto"><button type="button" data-pedido="{e(PEDIDO_FOTO)}" data-impresora data-adjuntar>Pieza desde una foto</button>
<button type="button" data-pedido="{e(PEDIDO_STL)}" data-impresora data-adjuntar="stl">Pieza desde un STL</button>
<span>Con una foto, copia algo que tenés. Con un STL tuyo o bajado, lo deja listo para imprimir y publicar. El archivo se adjunta en el chat.</span></div>
<p class="aviso" role="status" aria-live="polite"></p>
{_taller(estado_taller)}
<p class="modo" id="modo">{"Buscando el chat con Claude…" if modo == "claude" else "Los botones copian el pedido para que lo pegues en el chat con Claude."}</p>
</header>
<main>
{cuerpo}
</main>
<footer>{e(pie)}</footer>
<script>{GUION}</script>
</body>
</html>
"""


REDIRECCION = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=panel.html">
<title>Panel del taller</title>
</head>
<body>
<p>El catálogo ahora es el <a href="panel.html">panel del taller</a>.</p>
</body>
</html>
"""


def _avance(p: dict) -> tuple[int, str]:
    h = hechos(p)
    return max(i for i, (clave, _) in enumerate(PASOS) if clave in h), p.get("fecha") or ""


def _cantidad(n: int, una: str, varias: str) -> str:
    return f"{n} {una if n == 1 else varias}"


def resumen_corto(catalogo: dict) -> str:
    """Una línea para el comienzo de la conversación."""
    piezas = catalogo["piezas"]
    if not piezas:
        return "Todavía no hay ideas ni piezas en el panel."
    ideas = sum(1 for p in piezas if grupo_de(p) == "pendiente")
    sin_laminar = sum(1 for p in piezas if grupo_de(p) == "en_proceso" and "laminada" not in hechos(p))
    listas = sum(1 for p in piezas if grupo_de(p) == "en_proceso" and "laminada" in hechos(p))
    terminadas = sum(1 for p in piezas if grupo_de(p) == "terminada")
    partes = [x for x in (
        _cantidad(ideas, "idea pendiente", "ideas pendientes") if ideas else "",
        _cantidad(sin_laminar, "pieza diseñada sin laminar", "piezas diseñadas sin laminar") if sin_laminar else "",
        _cantidad(listas, "lista para imprimir", "listas para imprimir") if listas else "") if x]
    if not partes:
        return f"Nada pendiente: {_cantidad(terminadas, 'pieza terminada', 'piezas terminadas')}. Todo está en panel.html."
    texto = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"Tenés {texto}. Todo está en panel.html, en tu carpeta de trabajo."


def resumen(catalogo: dict, buscar: str | None = None) -> str:
    piezas = catalogo["piezas"]
    if buscar:
        q = buscar.lower()
        piezas = [p for p in piezas if q in " ".join(str(p.get(k) or "") for k in
                                                   ("nombre", "material", "color", "impresora", "nota",
                                                    "carpeta")).lower()]
    if not piezas:
        return "No hay nada" + (f" que coincida con «{buscar}»." if buscar else " en el panel.")
    lineas = [f"{len(piezas)} entre ideas y piezas:"]
    ordenadas = sorted(piezas, key=lambda x: x.get("fecha") or "", reverse=True)       # lo más nuevo primero
    for p in sorted(ordenadas, key=lambda x: list(GRUPOS).index(grupo_de(x))):
        datos = [GRUPOS[grupo_de(p)][:-1].lower() if grupo_de(p) != "en_proceso" else "en proceso"]
        if p.get("impresora"):
            datos.append(p["impresora"])
        if p.get("material"):
            datos.append(p["material"])
        if p.get("tiempo"):
            datos.append(p["tiempo"])
        if _plata(p.get("precio")):
            datos.append("precio " + _plata(p["precio"]))
        sigue = siguiente(p)
        lineas.append(f"- {p.get('fecha', '')} {p.get('nombre', '')} ({', '.join(d for d in datos if d)})"
                      + (f" → sigue: {sigue}" if sigue else "") + f" [{p['carpeta']}]")
    return "\n".join(lineas)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="accion", required=True)

    a = sub.add_parser("agregar", help="agrega o actualiza una pieza")
    a.add_argument("--catalogo", required=True, type=Path)
    a.add_argument("--carpeta", required=True, help="carpeta de la pieza, relativa a la carpeta de trabajo")
    a.add_argument("--nombre")
    a.add_argument("--tipo", choices=sorted(TIPOS))
    a.add_argument("--fecha", help="AAAA-MM-DD (si no, la del nombre de la carpeta)")
    a.add_argument("--material")
    a.add_argument("--color")
    a.add_argument("--impresora", help="nombre de la impresora para la que se hizo (el de config.json)")
    a.add_argument("--de-idea", help="la idea anotada que se hizo pieza (ideas/AAAA-MM-DD_nombre): pasa a esta pieza")
    a.add_argument("--informe-gcode")
    a.add_argument("--informe-stl")
    a.add_argument("--producto", help="publicacion.json de /publicar (o el producto.json de antes de la 0.1.30)")
    a.add_argument("--archivos", nargs="*", default=[], help="archivos de la carpeta de la pieza (relativos a ella)")
    a.add_argument("--imagen", help="imagen principal (relativa a la carpeta de la pieza)")
    a.add_argument("--estado", choices=sorted(ESTADOS))
    a.add_argument("--nota")
    a.add_argument("--url-tienda")
    a.add_argument("--id-tienda", help="número del producto en la tienda, para actualizarlo en vez de crear otro")
    a.add_argument("--estado-publicacion", choices=sorted(ESTADOS_PUBLICACION),
                   help="dónde está la publicación: vista_previa (armada), borrador (cargada) o publicada")
    a.add_argument("--moneda", help="moneda del precio, si no sale del costo")
    a.add_argument("--origen", choices=sorted(ORIGENES), help="de dónde salió el modelo (un STL del usuario, por ejemplo)")
    a.add_argument("--fuente", help="la página de donde se bajó el modelo (http o https)")
    a.add_argument("--licencia", help="la licencia del modelo bajado, como la dice su página (CC BY, CC BY-NC…)")

    i = sub.add_parser("idea", help="anota una idea para más adelante")
    i.add_argument("--catalogo", required=True, type=Path)
    i.add_argument("--nombre", required=True)
    i.add_argument("--nota")
    i.add_argument("--impresora")
    i.add_argument("--fecha", help="AAAA-MM-DD (si no, hoy)")

    q = sub.add_parser("quitar-idea", help="saca una idea que el usuario descartó")
    q.add_argument("--catalogo", required=True, type=Path)
    q.add_argument("--carpeta", required=True, help="ideas/AAAA-MM-DD_nombre")

    d = sub.add_parser("desde-listado", help="suma las piezas que ya estaban en la carpeta de trabajo")
    d.add_argument("--catalogo", required=True, type=Path)
    d.add_argument("--listado", required=True, type=Path, help="JSON de device_list_dir (recursive) o lista de rutas")

    c = sub.add_parser("carpeta", help="nombre de la carpeta de una pieza nueva y de su G-code y proyecto")
    c.add_argument("--tipo", choices=sorted(TIPOS), default="impresion")
    c.add_argument("--nombre", required=True)
    c.add_argument("--impresora", help="la impresora para la que se lamina (en diseños, solo si se hizo para una)")
    c.add_argument("--fecha", help="AAAA-MM-DD (si no, hoy)")

    h = sub.add_parser("html", help="arma panel.html")
    h.add_argument("--catalogo", required=True, type=Path)
    h.add_argument("--salida", required=True, type=Path)
    h.add_argument("--titulo", default="Panel del taller")
    h.add_argument("--modo", choices=["archivo", "claude"], default="archivo",
                   help="archivo: panel.html de la carpeta de trabajo; claude: la página para publicar en claude.ai")
    h.add_argument("--imagenes", type=Path, help="(modo claude) JSON carpeta de la pieza → ruta de su foto en la página")
    h.add_argument("--config", type=Path, help="config.json del taller: suma la caja «Tu taller» (qué falta para los costos)")
    h.add_argument("--impresoras-orca", type=Path,
                   help="salida de impresora.py detectar --json: el selector de impresora con las de Orca sin preparar")

    rd = sub.add_parser("redireccion", help="catalogo.html que lleva al panel (para el de antes de la 0.1.13)")
    rd.add_argument("--salida", required=True, type=Path)

    t = sub.add_parser("estados-tienda", help="anota en el panel si los productos están publicados o en borrador")
    t.add_argument("--catalogo", required=True, type=Path)
    t.add_argument("--estados", required=True, type=Path, help="lo que devolvió estado_productos (taller3d-tienda)")
    t.add_argument("--sacar", nargs="*", default=[],
                   help="carpetas de piezas cuyo producto está en la papelera o borrado y el usuario dijo de sacar")

    r = sub.add_parser("resumen", help="lista las piezas en texto")
    r.add_argument("--catalogo", required=True, type=Path)
    r.add_argument("--buscar")
    r.add_argument("--corto", action="store_true", help="una línea: qué está pendiente")

    args = ap.parse_args(argv)
    if args.accion == "redireccion":
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(REDIRECCION, encoding="utf-8")
        print(f"Acceso al panel: {args.salida}")
        return
    if args.accion == "carpeta":
        print(json.dumps({"carpeta": carpeta_de_pieza(args.tipo, args.nombre, args.impresora, args.fecha),
                          "archivo": archivo_de_pieza(args.nombre, args.impresora)}, ensure_ascii=False))
        return
    catalogo = cargar(args.catalogo)
    if args.accion == "agregar":
        extra = datos_de_informes(_leer_json(args.informe_gcode), _leer_json(args.informe_stl),
                                  _leer_json(args.producto))
        # La publicación: lo nuevo de publicacion.json pisa lo anterior, pero su estado se conserva si no se dice otro.
        anterior = next((p for p in catalogo["piezas"] if p.get("carpeta") == normalizar_carpeta(args.carpeta)), {})
        vieja = anterior.get("publicacion") if isinstance(anterior.get("publicacion"), dict) else None
        if "publicacion" in extra or args.estado_publicacion and (vieja is not None or args.id_tienda):
            pub = {**(vieja or {}), **extra.get("publicacion", {})}
            estado_pub = (args.estado_publicacion or (vieja or {}).get("estado")
                          or ("borrador" if args.id_tienda or anterior.get("id_tienda") else "vista_previa"))
            if estado_pub == "vista_previa" and (args.id_tienda or anterior.get("id_tienda")):
                estado_pub = "borrador"
            pub["estado"] = estado_pub
            extra["publicacion"] = pub
            if estado_pub in ("borrador", "publicada"):
                extra["estado"] = "en_tienda"
        if args.id_tienda:
            extra.setdefault("estado", "en_tienda")
        if args.estado:
            extra["estado"] = args.estado
            if args.estado in ("disenada", "laminada"):
                extra["impresa"] = False           # volver atrás a mano («no la imprimí»): deja de contar como impresa
        if args.moneda and extra.get("precio"):
            extra["precio"]["moneda"] = args.moneda
        pieza = agregar(catalogo, args.carpeta, nombre=args.nombre, tipo=args.tipo, fecha=args.fecha,
                        material=args.material or extra.pop("material", None), color=args.color,
                        impresora=args.impresora, de_idea=args.de_idea,
                        archivos=args.archivos, imagen=args.imagen, nota=args.nota, url_tienda=args.url_tienda,
                        id_tienda=args.id_tienda, origen=args.origen, fuente=args.fuente,
                        licencia=_en_una_linea(args.licencia, 80) if args.licencia else None,
                        **{k: v for k, v in extra.items() if k != "material"})
        guardar(args.catalogo, catalogo)
        print(f"Catálogo: {pieza['nombre']} ({etiqueta_estado(pieza)}) — "
              f"{len(catalogo['piezas'])} piezas en total.")
    elif args.accion == "estados-tienda":
        estados = json.loads(args.estados.read_text(encoding="utf-8"))
        if isinstance(estados, dict) and isinstance(estados.get("structuredContent"), dict):
            estados = estados["structuredContent"]          # el resultado entero de la herramienta
        r = aplicar_estados_tienda(catalogo, estados, args.sacar)
        r["guardado"] = bool(r["cambios"] or r["sacadas"] or r["enlaces"])
        if r["guardado"]:                                  # sin cambios no se toca (no hay nada que escribir en la PC)
            guardar(args.catalogo, catalogo)
        print(json.dumps({**r, "mensaje": contar_estados(r)}, ensure_ascii=False, indent=1))
    elif args.accion == "idea":
        idea = agregar_idea(catalogo, args.nombre, args.nota, args.impresora, args.fecha)
        guardar(args.catalogo, catalogo)
        print(json.dumps({"carpeta": idea["carpeta"], "nombre": idea["nombre"]}, ensure_ascii=False))
    elif args.accion == "quitar-idea":
        quitada = quitar_idea(catalogo, args.carpeta)
        guardar(args.catalogo, catalogo)
        print("Idea quitada." if quitada else "No encontré esa idea.")
    elif args.accion == "desde-listado":
        listado = json.loads(args.listado.read_text(encoding="utf-8"))
        nuevas = desde_listado(catalogo, listado)
        guardar(args.catalogo, catalogo)
        print(f"Sumé {len(nuevas)} piezas que ya estaban: {', '.join(nuevas) if nuevas else 'ninguna'}.")
    elif args.accion == "html":
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        imagenes = _leer_json(args.imagenes) if args.imagenes else None
        detectadas = []
        if args.impresoras_orca:
            try:
                detectadas = comun.leer_detectadas(args.impresoras_orca)
            except (OSError, ValueError) as error:
                raise SystemExit(f"No pude leer {args.impresoras_orca} ({error}).")
        estado, config = None, {}
        if args.config and args.config.exists():
            import costos
            config = _leer_json(str(args.config))
            estado = costos.estado_taller(config, detectadas)
        impresoras = comun.impresoras_para_elegir(config, detectadas)
        args.salida.write_text(generar_html(catalogo, args.titulo, args.modo, imagenes, estado, impresoras),
                               encoding="utf-8")
        print(f"Página: {args.salida} ({len(catalogo['piezas'])} entre ideas y piezas).")
    else:
        print(resumen_corto(catalogo) if args.corto else resumen(catalogo, args.buscar))


if __name__ == "__main__":
    main()
