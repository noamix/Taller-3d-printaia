#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""taller3d-tienda: servidor MCP local (stdio, solo biblioteca estándar) que carga productos en la tienda WooCommerce
del usuario, SIEMPRE como borrador.

Herramientas:
  cargar_borrador(carpeta)  lee <carpeta de la pieza>/producto/publicacion.json (lo arma /publicar), sube sus fotos y
                            crea o actualiza el producto como borrador. Un producto que ya está publicado no se toca.
  estado_tienda()           dice si la tienda está conectada y responde. No cambia nada.
  categorias_tienda()       las categorías de productos de la tienda (número, nombre, «Padre › Hija»), para elegir
                            entre ellas las de cada producto. No cambia nada.
  crear_categoria(nombre, padre)  crea una categoría de productos que no existe, solo cuando el usuario dijo que sí.
  cambiar_categorias(carpeta)  le pone a un producto que ya está en la tienda (también uno publicado, con el OK del
                            usuario) las categorías de su publicación. No cambia nada más: ni el estado, ni el texto,
                            ni el precio, ni las fotos.
  estado_productos(ids)     en qué estado está cada producto del taller en la tienda (borrador, publicado, en la
                            papelera, borrado...). Sin ids, los que tiene anotados el panel (taller-3d/catalogo.json).
                            No cambia nada.

Nunca publica, no borra, no toca pedidos, clientes ni otros productos. Categorías nuevas, solo con crear_categoria. Habla solo con la tienda guardada (https) y no
sigue redirecciones (no le manda la contraseña a otro sitio).

Lo arranca la app de escritorio de Claude (entrada "taller3d-tienda" de claude_desktop_config.json, que escribe el
instalador). La configuración sale solo de esa entrada y del archivo de credenciales, nunca de la herramienta:
  TALLER3D_CARPETA       carpeta de trabajo (ruta absoluta).
  TALLER3D_CREDENCIALES  (opcional) el archivo con la tienda, el usuario y la contraseña de aplicación. Por defecto
                         ~/.config/taller-3d/credenciales-tienda.json (Windows: %APPDATA%\\taller-3d\\...).

La contraseña de aplicación (se crea en WordPress: Usuarios → Perfil → Contraseñas de aplicación) la guarda el
usuario una vez, en una terminal, con:  python3 tienda_mcp.py configurar
(en Windows, el instalador deja conectar-tienda.bat, que hace lo mismo). Antes de pedirla, revisa la tienda sin
contraseña: que responda en https sin redirecciones, que tenga WooCommerce y las contraseñas de aplicación
habilitadas. Eso solo, sin conectar nada:  python3 tienda_mcp.py revisar
Nunca pasa por el chat. El archivo queda solo para su usuario (permisos 600).

Escribe un solo archivo: <carpeta de la pieza>/producto/tienda.json (número del producto, enlaces y las fotos ya
subidas, para no subirlas dos veces). Sin la contraseña.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

NOMBRE = "taller3d-tienda"
VERSION = "0.3.0"
INFO = {"name": NOMBRE, "title": "Taller 3D: cargar en la tienda", "version": VERSION}
VERSIONES_MODERNAS = ("2026-07-28",)
VERSIONES_LEGADAS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPACIDADES = "io.modelcontextprotocol/clientCapabilities"
META_SERVIDOR = "io.modelcontextprotocol/serverInfo"

ARCHIVO_CREDENCIALES = "credenciales-tienda.json"
ESTADO = "tienda.json"                 # en <pieza>/producto/
MAX_RUTA = 1024
MAX_PUBLICACION = 2 * 1024 * 1024
MAX_CATALOGO = 8 * 1024 * 1024
MAX_IDS = 100
CATALOGO = os.path.join("taller-3d", "catalogo.json")   # el panel, en la carpeta de trabajo
MAX_CREDENCIALES = 64 * 1024
MAX_FOTO = 15 * 1024 * 1024
MAX_FOTOS = 10
MAX_ETIQUETAS = 10
MAX_RESPUESTA = 8 * 1024 * 1024
REPETIDO_S = 20.0
TIPOS_FOTO = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
ESTADOS = {"draft": "borrador", "publish": "publicado", "pending": "pendiente de revisión", "private": "privado",
           "future": "programado"}
EN_LA_PAPELERA, BORRADO = "trash", "borrado"           # «borrado»: la tienda ya no lo tiene (no es un estado de WooCommerce)
ESTADOS_TODOS = {**ESTADOS, EN_LA_PAPELERA: "en la papelera", BORRADO: "borrado"}


def como_reconectar() -> str:
    """Cómo se conecta (o se vuelve a conectar) la tienda en esta PC, para los mensajes."""
    if os.name == "nt":
        return "conectar-tienda.bat, que está en %LOCALAPPDATA%\\taller-3d"
    aqui = os.path.abspath(__file__)
    casa = os.path.expanduser("~")
    ruta = "~" + aqui[len(casa):] if casa not in ("", "/") and aqui.startswith(casa + os.sep) else aqui
    if " " in ruta:
        ruta = f'"{aqui}"'
    return f"python3 {ruta} configurar"


SIN_CONECTAR = ("La tienda todavía no está conectada. Hacelo una sola vez en la PC, " +
                ("abriendo " if os.name == "nt" else "en una terminal: ") + como_reconectar() +
                " (te pide la dirección de la tienda, tu usuario de WordPress y una contraseña de aplicación).")

INSTRUCCIONES = (
    "Servidor local del taller 3D (plugin taller-3d) para la tienda WooCommerce del usuario. cargar_borrador carga "
    "como BORRADOR, con sus fotos, la publicación que /publicar armó en <carpeta de la pieza>/producto/"
    "publicacion.json; si el producto ya está publicado, no lo toca. Usala cuando el usuario pida cargar una "
    "publicación en su tienda, también desde el panel. estado_tienda dice si la tienda está conectada. "
    "categorias_tienda da las categorías que ya tiene la tienda: elegí entre ellas las de cada producto antes de "
    "armar la publicación. crear_categoria crea una nueva solo si el usuario la aprobó. cambiar_categorias cambia solo "
    "las categorías de un producto que ya está en la tienda (si está publicado, solo con el OK del usuario). "
    "estado_productos dice si los productos del panel siguen en borrador, ya están publicados o se borraron, sin "
    "cambiar nada: usala al empezar a trabajar con el taller y antes de rehacer el panel. Nunca publica: publicar es "
    "siempre del usuario, desde su tienda.")

HERRAMIENTAS = [
    {
        "name": "cargar_borrador",
        "title": "Cargar un producto en la tienda, como borrador",
        "description": (
            "Carga en la tienda WooCommerce del usuario, como BORRADOR, el producto que /publicar armó para una "
            "pieza: lee <carpeta>/producto/publicacion.json, sube sus fotos y crea el producto o actualiza el "
            "borrador que ya tenga el mismo SKU. Si ese producto ya está publicado, no lo toca. Nunca publica. "
            "`carpeta`: la de la pieza, relativa a la carpeta de trabajo del taller (por ejemplo "
            "impresiones/2026-11-22_kit-escuadras-melamina-18-mm_ender-3-v3-plus)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "carpeta": {"type": "string", "minLength": 1, "maxLength": MAX_RUTA,
                            "description": "La carpeta de la pieza, relativa a la carpeta de trabajo."},
            },
            "required": ["carpeta"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "cargado": {"type": "boolean", "description": "Si el producto quedó cargado (o actualizado) como borrador."},
                "mensaje": {"type": "string", "description": "Qué pasó, para mostrarle al usuario."},
                "accion": {"type": "string", "enum": ["creado", "actualizado", "ya_publicado"]},
                "id": {"type": "integer", "description": "El número del producto en la tienda."},
                "estado": {"type": "string", "description": "Cómo quedó en la tienda: borrador, publicado, ..."},
                "fotos": {"type": "integer", "description": "Fotos que tiene el producto."},
                "enlace_admin": {"type": "string", "description": "El producto en el administrador de la tienda."},
                "enlace_vista_previa": {"type": "string", "description": "La vista previa del borrador en la tienda."},
                "avisos": {"type": "array", "items": {"type": "string"}},
                "repetido": {"type": "boolean", "description": "El mismo pedido llegó hace un momento: no se repitió."},
            },
            "required": ["cargado", "mensaje"],
        },
        # Crea o cambia un borrador en otro sistema (la tienda): no es de solo lectura, pero no borra ni publica.
        "annotations": {"title": "Cargar en la tienda (borrador)", "readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "estado_tienda",
        "title": "Ver si la tienda está conectada",
        "description": ("Dice si la tienda WooCommerce del usuario está conectada y responde (dirección y usuario). "
                        "No cambia nada."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": {
            "type": "object",
            "properties": {
                "conectada": {"type": "boolean"},
                "mensaje": {"type": "string"},
                "tienda": {"type": "string"},
                "usuario": {"type": "string"},
            },
            "required": ["conectada", "mensaje"],
        },
        "annotations": {"title": "Estado de la tienda", "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "categorias_tienda",
        "title": "Ver las categorías de la tienda",
        "description": ("Las categorías de productos que tiene la tienda WooCommerce del usuario: número, nombre, "
                        "dentro de cuál está («Padre › Hija») y cuántos productos tiene. Sirve para elegir entre "
                        "ellas las de cada producto (en la publicación van por su nombre exacto, o «Padre › Hija» si "
                        "hay dos con el mismo nombre). No cambia nada."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": {
            "type": "object",
            "properties": {
                "categorias": {"type": "array", "items": {"type": "object", "properties": {
                    "id": {"type": "integer"}, "nombre": {"type": "string"}, "padre": {"type": "integer"},
                    "ruta": {"type": "string"}, "productos": {"type": "integer"}}}},
                "tienda": {"type": "string"},
                "mensaje": {"type": "string"},
            },
            "required": ["categorias", "mensaje"],
        },
        "annotations": {"title": "Categorías de la tienda", "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "crear_categoria",
        "title": "Crear una categoría en la tienda",
        "description": ("Crea en la tienda WooCommerce del usuario una categoría de productos nueva. Usala solo "
                        "después de que el usuario aprobó el nombre (y dentro de cuál va): las categorías se ven en "
                        "su tienda. Si ya hay una con ese nombre en ese lugar, no crea otra y devuelve esa. "
                        "`padre`: el número o el nombre de la categoría dentro de la que va (vacío: arriba de todo)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "minLength": 2, "maxLength": 60,
                           "description": "El nombre de la categoría nueva, como se va a ver en la tienda."},
                "padre": {"type": ["integer", "string"],
                          "description": "Opcional: la categoría dentro de la que va (número o nombre)."},
            },
            "required": ["nombre"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "creada": {"type": "boolean", "description": "Si se creó (false si ya existía o si no se pudo)."},
                "id": {"type": "integer"},
                "nombre": {"type": "string"},
                "ruta": {"type": "string"},
                "mensaje": {"type": "string"},
            },
            "required": ["creada", "mensaje"],
        },
        # Crea algo en otro sistema (la tienda): no es de solo lectura, pero no borra ni cambia lo que hay.
        "annotations": {"title": "Crear categoría", "readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "cambiar_categorias",
        "title": "Cambiar las categorías de un producto de la tienda",
        "description": ("Le pone al producto de una pieza que ya está en la tienda (el de producto/tienda.json o el "
                        "del mismo SKU) las categorías de su publicación (producto/publicacion.json), elegidas entre "
                        "las que existen. Cambia solo eso: ni el estado, ni el texto, ni el precio, ni las fotos. Si "
                        "el producto ya está publicado, el cambio se ve en la tienda: usala solo con el OK del "
                        "usuario. `carpeta`: la de la pieza, relativa a la carpeta de trabajo."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "carpeta": {"type": "string", "minLength": 1, "maxLength": MAX_RUTA,
                            "description": "La carpeta de la pieza, relativa a la carpeta de trabajo."},
            },
            "required": ["carpeta"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "cambiado": {"type": "boolean"},
                "id": {"type": "integer"},
                "estado": {"type": "string", "description": "Cómo está el producto en la tienda: borrador, publicado, ..."},
                "categorias": {"type": "array", "items": {"type": "string"}},
                "avisos": {"type": "array", "items": {"type": "string"}},
                "mensaje": {"type": "string"},
            },
            "required": ["cambiado", "mensaje"],
        },
        "annotations": {"title": "Cambiar categorías", "readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "estado_productos",
        "title": "Ver si los productos del taller están publicados",
        "description": ("Dice en qué estado está cada producto del taller en la tienda WooCommerce del usuario: "
                        "borrador, publicado, pendiente de revisión, privado, programado, en la papelera o borrado. "
                        "Sin `ids`, revisa los productos que tiene anotados el panel del taller "
                        "(taller-3d/catalogo.json de la carpeta de trabajo) y dice de qué pieza es cada uno. "
                        "No cambia nada."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "integer", "minimum": 1}, "maxItems": MAX_IDS,
                        "description": "Opcional: los números de los productos. Sin esto, los del panel."},
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "productos": {"type": "array", "items": {"type": "object", "properties": {
                    "id": {"type": "integer"},
                    "carpeta": {"type": ["string", "null"], "description": "La pieza del panel (sin ids)."},
                    "nombre": {"type": "string"},
                    "estado": {"type": "string", "description": "borrador, publicado, ..., en la papelera, borrado"},
                    "status": {"type": "string", "description": "El de WooCommerce (draft, publish...) o «borrado»."},
                    "tipo": {"type": "string", "description": "simple, variable..."},
                    "precio": {"type": "string"},
                    "enlace": {"type": ["string", "null"], "description": "La página del producto, si está publicado."},
                    "enlace_admin": {"type": "string"},
                    "modificado": {"type": ["string", "null"]}}}},
                "resumen": {"type": "object", "description": "Cuántos hay en cada estado."},
                "tienda": {"type": "string"},
                "mensaje": {"type": "string"},
            },
            "required": ["productos", "mensaje"],
        },
        "annotations": {"title": "Estado de los productos", "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
]


class Rechazo(Exception):
    """Un motivo para no seguir, que se le cuenta a quien pidió."""


def registrar(texto: str) -> None:
    """Registro en stderr (la app de Claude lo guarda en el log del servidor). stdout es solo para MCP.
    Nunca lleva la contraseña ni el encabezado de autorización."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {NOMBRE}: {texto}", file=sys.stderr, flush=True)


# --- Rutas ------------------------------------------------------------------------------------------------------

def dentro_de(ruta: str, raiz: str, o_igual: bool = False) -> bool:
    r, b = os.path.normcase(ruta), os.path.normcase(raiz)
    try:
        return (o_igual or r != b) and os.path.commonpath([r, b]) == b
    except ValueError:                                     # otra unidad de disco en Windows
        return False


def _con_control(texto: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in texto)


def carpeta_de_trabajo(entorno) -> str:
    raiz = (entorno.get("TALLER3D_CARPETA") or "").strip()
    if not raiz or not os.path.isabs(raiz):
        raise Rechazo("Falta la carpeta de trabajo del taller en la configuración de la app (TALLER3D_CARPETA): "
                      "corré de nuevo el instalador.")
    real = os.path.realpath(raiz)
    if not os.path.isdir(real):
        raise Rechazo(f"No existe la carpeta de trabajo {raiz}.")
    return real


def validar_carpeta(pedida, raiz: str) -> str:
    """La ruta real de la carpeta de la pieza (dentro de la de trabajo); si no, Rechazo con el motivo."""
    if not isinstance(pedida, str) or not pedida.strip():
        raise Rechazo("Falta `carpeta`: la carpeta de la pieza, relativa a la carpeta de trabajo.")
    if len(pedida) > MAX_RUTA or _con_control(pedida) or "://" in pedida:
        raise Rechazo("`carpeta` tiene que ser la ruta de la carpeta de la pieza (sin enlaces ni caracteres raros).")
    pedida = pedida.strip().replace("\\", "/") if os.sep == "/" else pedida.strip()
    ruta = pedida if os.path.isabs(pedida) else os.path.join(raiz, pedida)
    real = os.path.realpath(ruta)
    if not dentro_de(real, raiz):
        raise Rechazo("Solo cargo piezas de la carpeta de trabajo del taller.")
    if not os.path.isdir(real):
        raise Rechazo(f"No existe la carpeta {pedida} en la carpeta de trabajo.")
    return real


def _leer_json(ruta: str, maximo: int, que: str):
    try:
        if os.path.getsize(ruta) > maximo:
            raise Rechazo(f"{que} es demasiado grande.")
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise Rechazo(f"No pude leer {que}: {error}") from None


def leer_publicacion(carpeta: str) -> dict:
    ruta = os.path.realpath(os.path.join(carpeta, "producto", "publicacion.json"))
    if not dentro_de(ruta, carpeta) or not os.path.isfile(ruta):
        raise Rechazo("Esta pieza no tiene la publicación armada (producto/publicacion.json): pedile a Claude que la "
                      "arme con /publicar y que te muestre la vista previa.")
    datos = _leer_json(ruta, MAX_PUBLICACION, "publicacion.json")
    if not isinstance(datos, dict) or not isinstance(datos.get("producto"), dict):
        raise Rechazo("publicacion.json no tiene el producto: pedile a Claude que arme de nuevo la publicación.")
    return datos


# --- El producto ------------------------------------------------------------------------------------------------

def _texto(valor, largo: int, que: str, obligatorio: bool = True) -> str:
    if valor is None and not obligatorio:
        return ""
    if not isinstance(valor, str) or (obligatorio and not valor.strip()):
        raise Rechazo(f"Falta {que} en la publicación.")
    if len(valor) > largo:
        raise Rechazo(f"{que[0].upper()}{que[1:]} es demasiado largo.")
    return valor.strip()


def _numero(valor, que: str) -> str:
    if isinstance(valor, bool) or valor is None or valor == "":
        raise Rechazo(f"Falta {que} en la publicación.")
    t = str(valor).strip().replace(",", ".")
    if not re.fullmatch(r"\d{1,9}(\.\d{1,4})?", t):
        raise Rechazo(f"{que[0].upper()}{que[1:]} no es un número: {valor!r}.")
    return t


def _categorias_pedidas(lista, maximo: int = 5) -> list[dict]:
    """Las categorías que pide la publicación: por número ({"id": 16}) o por nombre ({"name": "Hogar y deco"}, o
    «Padre › Hija» si hay dos con el mismo nombre). Hasta 5, sin repetir."""
    salida, vistas = [], set()
    for x in lista if isinstance(lista, list) else []:
        numero = x.get("id") if isinstance(x, dict) else None
        if isinstance(numero, int) and not isinstance(numero, bool) and numero > 0:
            clave, pedida = ("id", numero), {"id": numero}
        else:
            n = x.get("name") if isinstance(x, dict) else x
            if not isinstance(n, str) or not n.strip() or len(n) > 200 or _con_control(n):
                continue
            clave, pedida = ("nombre", _clave(n)), {"name": n.strip()}
        if clave not in vistas:
            vistas.add(clave)
            salida.append(pedida)
    return salida[:maximo]


def _clave(texto: str) -> str:
    """Para comparar nombres: sin acentos, sin mayúsculas y con los espacios de a uno."""
    t = unicodedata.normalize("NFKD", html.unescape(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t).strip().casefold()


def _nombres(lista, maximo: int) -> list[str]:
    salida = []
    for x in lista if isinstance(lista, list) else []:
        n = x.get("name") if isinstance(x, dict) else x
        if isinstance(n, str) and n.strip() and len(n) <= 100 and not _con_control(n):
            n = n.strip()
            if n.casefold() not in {s.casefold() for s in salida}:
                salida.append(n)
    return salida[:maximo]


def armar_producto(pub: dict) -> tuple[dict, list[dict], list[str]]:
    """(datos del producto para WooCommerce, categorías pedidas, nombres de etiquetas). Siempre borrador."""
    p = pub["producto"]
    if p.get("type") not in (None, "", "simple"):
        raise Rechazo("Solo cargo productos simples.")
    datos = {
        "name": _texto(p.get("name"), 200, "el nombre"),
        "type": "simple",
        "status": "draft",
        "sku": _texto(p.get("sku"), 100, "el SKU"),
        "regular_price": _numero(p.get("regular_price"), "el precio"),
        "description": _texto(p.get("description"), 100_000, "la descripción", obligatorio=False),
        "short_description": _texto(p.get("short_description"), 5_000, "la descripción corta", obligatorio=False),
        "manage_stock": bool(p.get("manage_stock") or False),
    }
    if p.get("weight") not in (None, ""):
        datos["weight"] = _numero(p.get("weight"), "el peso")
    medidas = p.get("dimensions") if isinstance(p.get("dimensions"), dict) else {}
    if medidas:
        datos["dimensions"] = {k: _numero(medidas.get(k), f"la medida «{k}»") for k in ("length", "width", "height")
                               if medidas.get(k) not in (None, "")}
    return datos, _categorias_pedidas(p.get("categories")), _nombres(p.get("tags"), MAX_ETIQUETAS)


def rutas_fotos(pub: dict, carpeta: str) -> tuple[list[str], list[str]]:
    """Las fotos de la publicación (relativas a producto/), en su orden: solo imágenes de la carpeta de la pieza."""
    base = os.path.join(carpeta, "producto")
    fotos, avisos = [], []
    for nombre in pub.get("fotos") if isinstance(pub.get("fotos"), list) else []:
        if not isinstance(nombre, str) or not nombre.strip() or _con_control(nombre) or "://" in nombre:
            continue
        real = os.path.realpath(os.path.join(base, nombre))
        extension = os.path.splitext(real)[1].lower()
        if not dentro_de(real, carpeta) or extension not in TIPOS_FOTO:
            avisos.append(f"Salteé la foto {nombre}: no es una imagen de la carpeta de la pieza.")
        elif not os.path.isfile(real):
            avisos.append(f"No encontré la foto {nombre}: la salteé.")
        elif os.path.getsize(real) > MAX_FOTO:
            avisos.append(f"La foto {nombre} pesa más de {MAX_FOTO // (1024 * 1024)} MB: la salteé.")
        elif real not in fotos:
            fotos.append(real)
    if len(fotos) > MAX_FOTOS:
        avisos.append(f"Subí las primeras {MAX_FOTOS} fotos.")
    return fotos[:MAX_FOTOS], avisos


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "producto"


# --- La tienda --------------------------------------------------------------------------------------------------

def validar_url(url) -> str:
    if not isinstance(url, str) or not url.strip() or _con_control(url):
        raise Rechazo("Falta la dirección de la tienda.")
    u = urllib.parse.urlsplit(url.strip())
    local = u.hostname in ("localhost", "127.0.0.1")
    if not u.hostname or not (u.scheme == "https" or (u.scheme == "http" and local)):
        raise Rechazo("La dirección de la tienda tiene que empezar con https:// (por ejemplo https://mitienda.com.ar).")
    if u.username or u.password or u.query or u.fragment:
        raise Rechazo("Guardá solo la dirección de la tienda, sin usuario ni nada después de ? o #.")
    return f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}"


def ruta_credenciales(entorno) -> str:
    propia = (entorno.get("TALLER3D_CREDENCIALES") or "").strip()
    if propia:
        return os.path.expanduser(propia)
    if os.name == "nt" and entorno.get("APPDATA"):
        return os.path.join(entorno["APPDATA"], "taller-3d", ARCHIVO_CREDENCIALES)
    base = entorno.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "taller-3d", ARCHIVO_CREDENCIALES)


def leer_credenciales(entorno) -> tuple[str, str, str]:
    ruta = ruta_credenciales(entorno)
    if not os.path.isfile(ruta):
        raise Rechazo(SIN_CONECTAR)
    if os.name == "posix" and os.stat(ruta).st_mode & 0o077:
        raise Rechazo(f"El archivo con la conexión de tu tienda ({ruta}) lo pueden leer otros usuarios de la PC: "
                      f"corré chmod 600 \"{ruta}\" y probá de nuevo.")
    datos = _leer_json(ruta, MAX_CREDENCIALES, "el archivo de la tienda")
    if not isinstance(datos, dict):
        raise Rechazo(SIN_CONECTAR)
    usuario, clave = datos.get("usuario"), datos.get("contrasena")
    if not isinstance(usuario, str) or not usuario.strip() or not isinstance(clave, str) or not clave.strip():
        raise Rechazo(SIN_CONECTAR)
    return validar_url(datos.get("tienda")), usuario.strip(), clave.strip()


def guardar_credenciales(ruta: str, tienda: str, usuario: str, clave: str) -> None:
    carpeta = os.path.dirname(ruta)
    os.makedirs(carpeta, mode=0o700, exist_ok=True)
    temporal = ruta + ".tmp"
    if os.path.lexists(temporal):
        os.remove(temporal)
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"tienda": tienda, "usuario": usuario, "contrasena": clave}, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)
    if os.name == "posix":
        os.chmod(ruta, 0o600)


class Redireccion(Rechazo):
    """La tienda contestó con una redirección (por ejemplo, a la dirección con www)."""

    def __init__(self, destino: str):
        self.destino = str(destino)
        super().__init__(f"La tienda contestó con una redirección a {self.destino}. Guardá esa dirección (por ejemplo, "
                         f"con o sin www) con: {como_reconectar()}")


class SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Una redirección podría llevar la contraseña a otro sitio: no se sigue."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Redireccion(newurl)


def _json(datos: bytes):
    if len(datos) > MAX_RESPUESTA:
        raise Rechazo("La tienda contestó algo demasiado grande.")
    try:
        return json.loads(datos.decode("utf-8")) if datos.strip() else None
    except (UnicodeDecodeError, ValueError):
        return None


def _explicar(codigo: int, cuerpo, ruta: str) -> str:
    c = cuerpo.get("code", "") if isinstance(cuerpo, dict) else ""
    m = cuerpo.get("message", "") if isinstance(cuerpo, dict) else ""
    m = re.sub(r"<[^>]+>", "", html.unescape(m if isinstance(m, str) else ""))[:300].strip()
    if codigo == 401:
        if c in ("incorrect_password", "invalid_username", "invalid_email", "application_passwords_disabled"):
            return ("La tienda no aceptó el usuario o la contraseña de aplicación. Creá otra en tu WordPress "
                    f"(Usuarios → Perfil → Contraseñas de aplicación) y guardala con: {como_reconectar()}")
        return ("La tienda no reconoció la conexión: o la contraseña de aplicación ya no existe, o el servidor no le "
                "pasa a WordPress el encabezado de autorización (Herramientas → Salud del sitio lo revisa; la guía "
                "TIENDA-WOOCOMMERCE.md del taller dice cómo se arregla). Probá creando otra contraseña de aplicación y "
                f"guardándola con: {como_reconectar()}")
    if codigo == 403:
        que = "subir imágenes" if ruta.startswith("/wp/v2/media") else "cargar productos"
        return (f"Tu usuario de WordPress no tiene permiso para {que}: tiene que ser Administrador o Gestor de la "
                "tienda." + (f" ({m})" if m else ""))
    if codigo == 404 and c == "rest_no_route":
        return ("La tienda no tiene la conexión de WooCommerce (/wp-json/wc/v3): revisá que WooCommerce esté activo y "
                "que los enlaces permanentes no estén en «Simple».")
    if codigo == 400:
        return "La tienda no aceptó los datos del producto" + (f": {m}" if m else ".")
    if codigo >= 500:
        return f"La tienda tuvo un error ({codigo})" + (f": {m}" if m else "") + ". Probá de nuevo en un rato."
    return f"La tienda contestó {codigo}" + (f": {m}" if m else ".")


class Tienda:
    """La API de WordPress y WooCommerce de la tienda, con la contraseña de aplicación del usuario."""

    def __init__(self, base: str, usuario: str, clave: str, tiempo: float = 45.0, abridor=None):
        self.base = validar_url(base)
        self._autorizacion = "Basic " + base64.b64encode(f"{usuario}:{clave}".encode("utf-8")).decode("ascii")
        self.tiempo = tiempo
        self.abridor = abridor or urllib.request.build_opener(SinRedirecciones())

    def pedir(self, metodo: str, ruta: str, datos=None, params=None, cuerpo: bytes | None = None,
              tipo: str | None = None, archivo: str | None = None, admitir=()):
        url = f"{self.base}/wp-json{ruta}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        encabezados = {"Authorization": self._autorizacion, "Accept": "application/json",
                       "User-Agent": f"{NOMBRE}/{VERSION}"}
        if datos is not None:
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            encabezados["Content-Type"] = "application/json; charset=utf-8"
        elif cuerpo is not None:
            encabezados["Content-Type"] = tipo or "application/octet-stream"
            encabezados["Content-Disposition"] = f'attachment; filename="{archivo or "foto"}"'
        pedido = urllib.request.Request(url, data=cuerpo, headers=encabezados, method=metodo)
        try:
            with self.abridor.open(pedido, timeout=self.tiempo) as r:
                return r.status, _json(r.read(MAX_RESPUESTA + 1))
        except urllib.error.HTTPError as error:
            respuesta = _json(error.read(MAX_RESPUESTA + 1) or b"")
            if error.code in admitir:
                return error.code, respuesta
            raise Rechazo(_explicar(error.code, respuesta, ruta)) from None
        except urllib.error.URLError as error:
            raise Rechazo(f"No pude conectarme con la tienda ({self.base}): {error.reason}. Revisá que la PC tenga "
                          "internet y que la dirección esté bien.") from None
        except TimeoutError:
            raise Rechazo("La tienda tardó demasiado en contestar: probá de nuevo en un rato.") from None

    # Enlaces
    def enlace_admin(self, pid: int) -> str:
        return f"{self.base}/wp-admin/post.php?post={pid}&action=edit"

    def enlace_vista_previa(self, pid: int) -> str:
        return f"{self.base}/?post_type=product&p={pid}&preview=true"


def _lista(valor) -> list[dict]:
    return [x for x in valor if isinstance(x, dict)] if isinstance(valor, list) else []


def buscar_existente(tienda: Tienda, sku: str, id_previo) -> dict | None:
    """El producto de esta pieza en la tienda: el que se cargó antes (tienda.json) o el que tiene su SKU."""
    if isinstance(id_previo, int) and id_previo > 0:
        codigo, p = tienda.pedir("GET", f"/wc/v3/products/{id_previo}", admitir=(404, 410))
        if codigo == 200 and isinstance(p, dict) and p.get("status") != "trash":
            return p
    _, lista = tienda.pedir("GET", "/wc/v3/products", params={"sku": sku, "status": "any", "per_page": 10})
    return next((p for p in _lista(lista) if p.get("sku") == sku and p.get("status") != "trash"), None)


def _numero_de_producto(valor) -> int | None:
    """El número de un producto: entero positivo (o texto con solo dígitos, como lo guarda a veces el panel)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str) and valor.strip().isdigit():
        valor = int(valor.strip())
    return valor if isinstance(valor, int) and 0 < valor < 2 ** 63 else None


def ids_del_panel(raiz: str) -> list[tuple[int, str]]:
    """Los productos que tiene anotados el panel (id_tienda de cada pieza), con la carpeta de la pieza."""
    ruta = os.path.join(raiz, CATALOGO)
    if os.path.islink(ruta) or not dentro_de(os.path.realpath(ruta), raiz) or not os.path.isfile(ruta):
        raise Rechazo("No encontré el panel del taller (taller-3d/catalogo.json) en la carpeta de trabajo.")
    datos = _leer_json(ruta, MAX_CATALOGO, "catalogo.json")
    piezas = datos.get("piezas") if isinstance(datos, dict) else None
    if not isinstance(piezas, list):
        raise Rechazo("taller-3d/catalogo.json no tiene el formato del panel.")
    vistos: dict[int, str] = {}
    for p in piezas:
        if not isinstance(p, dict):
            continue
        pid = _numero_de_producto(p.get("id_tienda"))
        carpeta = p.get("carpeta")
        if pid and pid not in vistos:
            vistos[pid] = carpeta if isinstance(carpeta, str) and not _con_control(carpeta) else ""
    return list(vistos.items())


def estados_de(tienda: Tienda, ids: list[int]) -> dict[int, dict]:
    """El estado de cada producto en la tienda. Los que no aparecen se buscan uno por uno: en la papelera la tienda
    todavía los da; si no los da, están borrados."""
    vistos: dict[int, dict] = {}
    campos = "id,name,status,type,price,permalink,date_modified"
    for i in range(0, len(ids), MAX_IDS):
        bloque = ids[i:i + MAX_IDS]
        _, lista = tienda.pedir("GET", "/wc/v3/products", params={
            "include": ",".join(map(str, bloque)), "status": "any", "per_page": MAX_IDS, "_fields": campos})
        for p in _lista(lista):
            if p.get("id") in bloque:
                vistos[p["id"]] = p
    for pid in ids:
        if pid not in vistos:
            codigo, p = tienda.pedir("GET", f"/wc/v3/products/{pid}", params={"_fields": campos}, admitir=(404, 410))
            vistos[pid] = p if codigo == 200 and isinstance(p, dict) and p.get("id") == pid else {"status": BORRADO}
    return vistos


def describir_producto(tienda: Tienda, pid: int, p: dict, carpeta: str | None) -> dict:
    status = str(p.get("status") or "")
    enlace = p.get("permalink") if status == "publish" and isinstance(p.get("permalink"), str) else None
    if enlace and not (enlace.startswith(tienda.base + "/") or enlace == tienda.base):
        enlace = None                                    # solo enlaces de la misma tienda
    modificado = p.get("date_modified")
    return {"id": pid, "carpeta": carpeta, "nombre": _limpio(p.get("name"), 200),
            "estado": ESTADOS_TODOS.get(status, status or "desconocido"), "status": status,
            "tipo": str(p.get("type") or ""), "precio": str(p.get("price") or ""),
            "enlace": enlace, "enlace_admin": tienda.enlace_admin(pid),
            "modificado": modificado if isinstance(modificado, str) else None}


def resumir_estados(productos: list[dict]) -> tuple[dict, str]:
    cuenta: dict[str, int] = {}
    for x in productos:
        cuenta[x["estado"]] = cuenta.get(x["estado"], 0) + 1
    plurales = {"borrador": "borradores", "publicado": "publicados", "privado": "privados",
                "programado": "programados", "borrado": "borrados", "pendiente de revisión": "pendientes de revisión"}
    partes = [f"{n} {plurales.get(e, e) if n > 1 else e}" for e, n in sorted(cuenta.items(), key=lambda x: -x[1])]
    texto = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1] if partes else ""
    return cuenta, texto


def _mismo_nombre(a, b: str) -> bool:
    return isinstance(a, str) and html.unescape(a).strip().casefold() == b.strip().casefold()


MAX_CATEGORIAS = 300


def listar_categorias(tienda: Tienda) -> list[dict]:
    """Las categorías de productos de la tienda (hasta 300), con su ruta («Padre › Hija») y cuántos productos tiene
    cada una."""
    crudas: list[dict] = []
    for pagina in range(1, MAX_CATEGORIAS // 100 + 1):
        _, lista = tienda.pedir("GET", "/wc/v3/products/categories",
                                params={"per_page": 100, "page": pagina, "orderby": "name", "order": "asc"})
        lote = [c for c in _lista(lista) if isinstance(c.get("id"), int) and isinstance(c.get("name"), str)]
        crudas += lote
        if len(lote) < 100:
            break
    por_id = {c["id"]: c for c in crudas}

    def ruta(c: dict) -> str:
        partes, actual, vistas = [], c, set()
        while actual and actual["id"] not in vistas and len(partes) < 10:
            vistas.add(actual["id"])
            partes.append(_limpio(actual["name"], 100))
            actual = por_id.get(actual.get("parent")) if actual.get("parent") else None
        return " › ".join(reversed(partes))

    return [{"id": c["id"], "nombre": _limpio(c["name"], 100),
             "padre": c["parent"] if isinstance(c.get("parent"), int) else 0, "ruta": ruta(c),
             "productos": c["count"] if isinstance(c.get("count"), int) else 0} for c in crudas]


def _las_que_hay(todas: list[dict]) -> str:
    rutas = [c["ruta"] for c in todas]
    return ", ".join(rutas[:15]) + (f" y {len(rutas) - 15} más" if len(rutas) > 15 else "") if rutas else "ninguna"


def buscar_categoria(todas: list[dict], pedida) -> tuple[list[dict], str]:
    """Las categorías que coinciden con lo pedido (número, nombre o «Padre › Hija»), y cómo se pidió (para avisos)."""
    if isinstance(pedida, dict) and "id" in pedida:
        return [c for c in todas if c["id"] == pedida["id"]], f"con el número {pedida['id']}"
    nombre = pedida.get("name", "") if isinstance(pedida, dict) else str(pedida)
    partes = [_clave(p) for p in re.split(r"\s*[›>]\s*", nombre) if p.strip()]
    if not partes:
        return [], "sin nombre"
    halladas = [c for c in todas if [_clave(x) for x in c["ruta"].split(" › ")][-len(partes):] == partes]
    return halladas, f"«{nombre}»"


def ids_categorias(tienda: Tienda, pedidas: list[dict], avisos: list[str]) -> list[dict]:
    """Solo categorías que ya existen en la tienda (por número, nombre o «Padre › Hija»). Las que no, se avisan con
    las que hay, para elegir una: no se crean acá (eso es crear_categoria, con el OK del usuario)."""
    if not pedidas:
        return []
    todas = listar_categorias(tienda)
    ids: list[dict] = []
    for pedida in pedidas:
        halladas, como = buscar_categoria(todas, pedida)
        if len(halladas) == 1:
            if {"id": halladas[0]["id"]} not in ids:
                ids.append({"id": halladas[0]["id"]})
        elif halladas:
            avisos.append(f"En tu tienda hay {len(halladas)} categorías {como} ("
                          + ", ".join(c["ruta"] for c in halladas[:5]) + "): decí cuál con «Padre › Hija». El "
                          "producto quedó sin esa.")
        else:
            avisos.append(f"En tu tienda no hay una categoría {como}: el producto quedó sin ella. Las que hay: "
                          f"{_las_que_hay(todas)}. Elegí una de esas o pedile a Claude que la cree.")
    return ids


def crear_categoria(tienda: Tienda, nombre, padre=None) -> dict:
    """Crea una categoría de productos (o devuelve la que ya existe con ese nombre en ese lugar)."""
    if not isinstance(nombre, str) or not nombre.strip():
        raise Rechazo("Falta el nombre de la categoría.")
    if _con_control(nombre) or re.search(r"[<>›]", nombre):
        raise Rechazo("El nombre de la categoría no puede llevar < > ni ›.")
    nombre = re.sub(r"\s+", " ", nombre).strip()
    if not 2 <= len(nombre) <= 60:
        raise Rechazo("El nombre de la categoría tiene que tener entre 2 y 60 letras.")
    todas = listar_categorias(tienda)
    padre_id, padre_ruta, en = 0, "", ""
    if padre not in (None, "", 0):
        if isinstance(padre, bool) or not isinstance(padre, (int, str)):
            raise Rechazo("`padre` tiene que ser el número o el nombre de una categoría.")
        halladas, como = buscar_categoria(todas, {"id": padre} if isinstance(padre, int) else {"name": padre})
        if len(halladas) != 1:
            raise Rechazo(f"No encuentro una sola categoría {como} para ponerla adentro. Las que hay: "
                          f"{_las_que_hay(todas)}.")
        padre_id, padre_ruta = halladas[0]["id"], halladas[0]["ruta"]
        en = f" dentro de «{padre_ruta}»"
    ya = next((c for c in todas if c["padre"] == padre_id and _clave(c["nombre"]) == _clave(nombre)), None)
    if ya:
        return {"creada": False, "id": ya["id"], "nombre": ya["nombre"], "ruta": ya["ruta"],
                "mensaje": f"La categoría «{ya['ruta']}» ya estaba en tu tienda (número {ya['id']}): uso esa."}
    codigo, nueva = tienda.pedir("POST", "/wc/v3/products/categories", {"name": nombre, "parent": padre_id},
                                 admitir=(400,))
    datos = nueva.get("data") if isinstance(nueva, dict) and isinstance(nueva.get("data"), dict) else {}
    if codigo in (200, 201) and isinstance(nueva, dict) and isinstance(nueva.get("id"), int):
        ruta = f"{padre_ruta} › {nombre}" if padre_ruta else nombre
        return {"creada": True, "id": nueva["id"], "nombre": nombre, "ruta": ruta,
                "mensaje": f"Listo: creé la categoría «{nombre}»{en} en tu tienda (número {nueva['id']})."}
    if isinstance(datos.get("resource_id"), int):                   # term_exists: ya estaba
        return {"creada": False, "id": datos["resource_id"], "nombre": nombre, "ruta": nombre,
                "mensaje": f"La categoría «{nombre}» ya estaba en tu tienda (número {datos['resource_id']}): uso esa."}
    raise Rechazo(f"No pude crear la categoría «{nombre}»" + (f": {_limpio(nueva.get('message'), 200)}"
                                                             if isinstance(nueva, dict) and nueva.get("message")
                                                             else "."))


def ids_etiquetas(tienda: Tienda, nombres: list[str], avisos: list[str]) -> list[dict]:
    ids = []
    for n in nombres:
        _, lista = tienda.pedir("GET", "/wc/v3/products/tags", params={"search": n, "per_page": 100})
        hallada = next((t for t in _lista(lista) if _mismo_nombre(t.get("name"), n)), None)
        if hallada and isinstance(hallada.get("id"), int):
            ids.append({"id": hallada["id"]})
            continue
        codigo, nueva = tienda.pedir("POST", "/wc/v3/products/tags", {"name": n}, admitir=(400,))
        datos = nueva.get("data") if isinstance(nueva, dict) and isinstance(nueva.get("data"), dict) else {}
        if codigo in (200, 201) and isinstance(nueva, dict) and isinstance(nueva.get("id"), int):
            ids.append({"id": nueva["id"]})
        elif isinstance(datos.get("resource_id"), int):            # term_exists: ya estaba
            ids.append({"id": datos["resource_id"]})
        else:
            avisos.append(f"No pude agregar la etiqueta «{n}».")
    return ids


def subir_fotos(tienda: Tienda, fotos: list[str], previas: dict, nombre: str, sku: str) -> tuple[list[int], dict]:
    """Sube las fotos a la biblioteca de medios (las que ya se subieron antes, iguales, no se suben de nuevo)."""
    ids, mapa = [], {}
    for i, ruta in enumerate(fotos, 1):
        with open(ruta, "rb") as f:
            datos = f.read(MAX_FOTO + 1)
        huella = hashlib.sha256(datos).hexdigest()
        mid = previas.get(huella) if isinstance(previas, dict) else None
        if isinstance(mid, int) and mid > 0:
            codigo, _ = tienda.pedir("GET", f"/wp/v2/media/{mid}", params={"context": "edit"}, admitir=(404, 410))
            mid = mid if codigo == 200 else None
        else:
            mid = None
        if mid is None:
            extension = os.path.splitext(ruta)[1].lower()
            _, media = tienda.pedir("POST", "/wp/v2/media", cuerpo=datos, tipo=TIPOS_FOTO[extension],
                                    archivo=f"{_slug(sku)}-{i}{extension}")
            if not isinstance(media, dict) or not isinstance(media.get("id"), int):
                raise Rechazo("La tienda no devolvió el número de la foto que subí.")
            mid = media["id"]
            try:                                           # el texto alternativo es un extra: si falla, se sigue
                tienda.pedir("POST", f"/wp/v2/media/{mid}", {"alt_text": nombre, "title": nombre})
            except Rechazo:
                pass
        ids.append(mid)
        mapa[huella] = mid
    return ids, mapa


def leer_estado(ruta: str, base: str) -> dict:
    if not os.path.isfile(ruta) or os.path.islink(ruta):
        return {}
    try:
        datos = _leer_json(ruta, MAX_CREDENCIALES, "tienda.json")
    except Rechazo:
        return {}
    return datos if isinstance(datos, dict) and datos.get("tienda") == base else {}


def guardar_estado(ruta: str, datos: dict) -> bool:
    if os.path.islink(ruta) or not os.path.isdir(os.path.dirname(ruta)):
        return False
    temporal = ruta + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporal, ruta)
        return True
    except OSError:
        return False


# --- Las herramientas -------------------------------------------------------------------------------------------

class Servidor:
    def __init__(self, entorno=None, abridor=None):
        self.entorno = dict(os.environ if entorno is None else entorno)
        self.abridor = abridor
        self.legada: str | None = None
        self.recientes: dict[str, tuple[float, dict]] = {}

    def tienda(self) -> Tienda:
        base, usuario, clave = leer_credenciales(self.entorno)
        return Tienda(base, usuario, clave, abridor=self.abridor)

    def cargar(self, argumentos: dict) -> tuple[dict, bool]:
        """(structuredContent, isError)."""
        pedida = argumentos.get("carpeta")
        try:
            extra = sorted(set(argumentos) - {"carpeta"})
            if extra:
                raise Rechazo(f"Solo acepto `carpeta` (sobra: {', '.join(map(str, extra))}).")
            raiz = carpeta_de_trabajo(self.entorno)
            carpeta = validar_carpeta(pedida, raiz)
            relativa = os.path.relpath(carpeta, raiz).replace(os.sep, "/")
            ahora = time.monotonic()
            previo = self.recientes.get(carpeta)
            if previo and ahora - previo[0] < REPETIDO_S:
                registrar(f"repetido: {relativa}")
                return {**previo[1], "repetido": True,
                        "mensaje": f"Ya lo hice hace {ahora - previo[0]:.0f} s. " + previo[1]["mensaje"]}, False
            pub = leer_publicacion(carpeta)
            datos, categorias, etiquetas = armar_producto(pub)
            fotos, avisos = rutas_fotos(pub, carpeta)
            tienda = self.tienda()
            archivo_estado = os.path.join(carpeta, "producto", ESTADO)
            estado = leer_estado(archivo_estado, tienda.base)
            existente = buscar_existente(tienda, datos["sku"], estado.get("id"))
            nombre = datos["name"]
            if existente and existente.get("status") != "draft":
                pid = int(existente["id"])
                como = ESTADOS.get(existente.get("status"), str(existente.get("status")))
                salida = {"cargado": False, "accion": "ya_publicado", "id": pid, "estado": como,
                          "enlace_admin": tienda.enlace_admin(pid), "avisos": avisos,
                          "mensaje": f"«{nombre}» ya está en tu tienda como {como} (producto {pid}): no lo toqué. Si "
                                     "querés cambiarle el precio o el texto, pedíselo a Claude."}
                registrar(f"ya publicado, sin tocar: {relativa} → {pid}")
                return salida, False
            elegidas = ids_categorias(tienda, categorias, avisos)
            if elegidas or not existente:          # al actualizar sin ninguna encontrada, quedan las que ya tenía
                datos["categories"] = elegidas
            datos["tags"] = ids_etiquetas(tienda, etiquetas, avisos)
            imagenes, mapa = subir_fotos(tienda, fotos, estado.get("fotos") or {}, nombre, datos["sku"])
            datos["images"] = [{"id": i} for i in imagenes]
            if existente:
                _, producto = tienda.pedir("PUT", f"/wc/v3/products/{int(existente['id'])}", datos)
                accion = "actualizado"
            else:
                _, producto = tienda.pedir("POST", "/wc/v3/products", datos)
                accion = "creado"
            if not isinstance(producto, dict) or not isinstance(producto.get("id"), int):
                raise Rechazo("La tienda no devolvió el número del producto.")
            pid = producto["id"]
            _, visto = tienda.pedir("GET", f"/wc/v3/products/{pid}")
            visto = visto if isinstance(visto, dict) else {}
            if visto.get("status") != "draft":            # nunca debería pasar: se vuelve a borrador y se avisa
                tienda.pedir("PUT", f"/wc/v3/products/{pid}", {"status": "draft"})
                avisos.append("La tienda lo había dejado publicado: lo pasé a borrador.")
                _, visto = tienda.pedir("GET", f"/wc/v3/products/{pid}")
                visto = visto if isinstance(visto, dict) else {}
                if visto.get("status") != "draft":
                    raise Rechazo(f"El producto {pid} no quedó como borrador: revisalo en tu tienda ya mismo.")
            if visto.get("sku") != datos["sku"]:
                avisos.append(f"La tienda le dejó otro SKU («{visto.get('sku')}»): revisalo en el borrador.")
            if str(visto.get("regular_price")) != datos["regular_price"]:
                avisos.append(f"El precio quedó en {visto.get('regular_price')} en vez de {datos['regular_price']}: "
                              "revisalo en el borrador.")
            salida = {"cargado": True, "accion": accion, "id": pid, "estado": "borrador",
                      "fotos": len(_lista(visto.get("images"))) or len(imagenes),
                      "enlace_admin": tienda.enlace_admin(pid), "enlace_vista_previa": tienda.enlace_vista_previa(pid),
                      "avisos": avisos}
            fotos_txt = {0: "sin fotos", 1: "con 1 foto"}.get(salida["fotos"], f"con {salida['fotos']} fotos")
            hecho = "quedó como borrador" if accion == "creado" else "se actualizó (sigue como borrador)"
            salida["mensaje"] = (f"Listo: «{nombre}» {hecho} en tu tienda (producto {pid}), {fotos_txt}. Revisalo y "
                                 "publicalo vos desde la tienda.")
            if avisos:
                juntos = " ".join(avisos)
                salida["mensaje"] += " Ojo: " + juntos[:1].lower() + juntos[1:]
            guardar_estado(archivo_estado, {
                "tienda": tienda.base, "id": pid, "sku": datos["sku"], "estado": "borrador",
                "enlace_admin": salida["enlace_admin"], "enlace_vista_previa": salida["enlace_vista_previa"],
                "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "fotos": mapa})
            self.recientes = {k: v for k, v in self.recientes.items() if ahora - v[0] < REPETIDO_S}
            self.recientes[carpeta] = (ahora, salida)
            registrar(f"{accion}: {relativa} → {pid} ({len(imagenes)} fotos)")
            return salida, False
        except Rechazo as motivo:
            registrar(f"rechazado: {pedida!r}: {motivo}")
            return {"cargado": False, "mensaje": str(motivo)}, True

    def categorias(self, argumentos: dict) -> tuple[dict, bool]:
        try:
            if argumentos:
                raise Rechazo("categorias_tienda no lleva datos.")
            tienda = self.tienda()
            todas = listar_categorias(tienda)
            mensaje = (f"Tu tienda tiene {len(todas)} categorías: {_las_que_hay(todas)}." if todas
                       else "Tu tienda todavía no tiene categorías de productos.")
            return {"tienda": tienda.base, "categorias": todas, "mensaje": mensaje}, False
        except Rechazo as motivo:
            return {"categorias": [], "mensaje": str(motivo)}, True

    def crear_categoria(self, argumentos: dict) -> tuple[dict, bool]:
        try:
            extra = sorted(set(argumentos) - {"nombre", "padre"})
            if extra:
                raise Rechazo(f"Solo acepto `nombre` y `padre` (sobra: {', '.join(map(str, extra))}).")
            salida = crear_categoria(self.tienda(), argumentos.get("nombre"), argumentos.get("padre"))
            registrar(f"categoría {'creada' if salida['creada'] else 'que ya estaba'}: {salida['ruta']} → {salida['id']}")
            return salida, False
        except Rechazo as motivo:
            registrar(f"categoría rechazada: {argumentos.get('nombre')!r}: {motivo}")
            return {"creada": False, "mensaje": str(motivo)}, True

    def cambiar_categorias(self, argumentos: dict) -> tuple[dict, bool]:
        pedida = argumentos.get("carpeta")
        try:
            extra = sorted(set(argumentos) - {"carpeta"})
            if extra:
                raise Rechazo(f"Solo acepto `carpeta` (sobra: {', '.join(map(str, extra))}).")
            raiz = carpeta_de_trabajo(self.entorno)
            carpeta = validar_carpeta(pedida, raiz)
            pub = leer_publicacion(carpeta)
            datos, categorias, _ = armar_producto(pub)
            tienda = self.tienda()
            estado = leer_estado(os.path.join(carpeta, "producto", ESTADO), tienda.base)
            existente = buscar_existente(tienda, datos["sku"], estado.get("id"))
            if not existente:
                raise Rechazo(f"«{datos['name']}» todavía no está en tu tienda: cargalo primero (cargar_borrador).")
            if not categorias:
                raise Rechazo("La publicación no tiene categorías: elegí una entre las de tu tienda (categorias_tienda).")
            avisos: list[str] = []
            elegidas = ids_categorias(tienda, categorias, avisos)
            if not elegidas:
                raise Rechazo("No cambié nada: " + " ".join(avisos))
            pid = int(existente["id"])
            tienda.pedir("PUT", f"/wc/v3/products/{pid}", {"categories": elegidas})
            _, visto = tienda.pedir("GET", f"/wc/v3/products/{pid}")
            visto = visto if isinstance(visto, dict) else {}
            quedaron = sorted(c.get("id") for c in _lista(visto.get("categories")) if isinstance(c.get("id"), int))
            if quedaron != sorted(c["id"] for c in elegidas):
                avisos.append("La tienda no dejó las categorías como se pidió: revisalas en el producto.")
            todas = {c["id"]: c["ruta"] for c in listar_categorias(tienda)}
            rutas = [todas.get(c["id"], str(c["id"])) for c in elegidas]
            como = ESTADOS.get(visto.get("status") or existente.get("status"), str(visto.get("status") or ""))
            salida = {"cambiado": True, "id": pid, "estado": como, "categorias": rutas, "avisos": avisos,
                      "mensaje": f"Listo: «{datos['name']}» ({como}, producto {pid}) quedó en "
                                 + " y ".join(f"«{r}»" for r in rutas) + ". No cambié nada más."
                                 + (" Ojo: " + " ".join(avisos) if avisos else "")}
            registrar(f"categorías: {pid} → {', '.join(rutas)}")
            return salida, False
        except Rechazo as motivo:
            registrar(f"categorías rechazadas: {pedida!r}: {motivo}")
            return {"cambiado": False, "mensaje": str(motivo)}, True

    def productos(self, argumentos: dict) -> tuple[dict, bool]:
        """En qué estado están los productos en la tienda. Solo lee."""
        try:
            extra = sorted(set(argumentos) - {"ids"})
            if extra:
                raise Rechazo(f"Solo acepto `ids` (sobra: {', '.join(map(str, extra))}).")
            if "ids" in argumentos:
                pedidos = argumentos["ids"]
                if not isinstance(pedidos, list) or not pedidos or len(pedidos) > MAX_IDS:
                    raise Rechazo(f"`ids` tiene que ser una lista de 1 a {MAX_IDS} números de producto.")
                ids = [_numero_de_producto(x) if isinstance(x, int) else None for x in pedidos]
                if None in ids:
                    raise Rechazo("Los números de producto tienen que ser enteros positivos.")
                lista = [(pid, None) for pid in dict.fromkeys(ids)]
            else:
                lista = ids_del_panel(carpeta_de_trabajo(self.entorno))
            tienda = self.tienda()
            if not lista:
                return {"productos": [], "resumen": {}, "tienda": tienda.base,
                        "mensaje": "El panel todavía no tiene productos cargados en la tienda."}, False
            vistos = estados_de(tienda, [pid for pid, _ in lista])
            productos = [describir_producto(tienda, pid, vistos[pid], carpeta) for pid, carpeta in lista]
            cuenta, texto = resumir_estados(productos)
            registrar(f"estados: {len(productos)} productos ({texto})")
            return {"productos": productos, "resumen": cuenta, "tienda": tienda.base,
                    "mensaje": f"En tu tienda: {texto}. No cambié nada."}, False
        except Rechazo as motivo:
            return {"productos": [], "mensaje": str(motivo)}, True

    def estado(self, argumentos: dict) -> tuple[dict, bool]:
        try:
            if argumentos:
                raise Rechazo("estado_tienda no lleva datos.")
            tienda = self.tienda()
            _, yo = tienda.pedir("GET", "/wp/v2/users/me", params={"context": "edit"})
            tienda.pedir("GET", "/wc/v3/products", params={"per_page": 1})
            usuario = (yo or {}).get("name") or (yo or {}).get("slug") or ""
            return {"conectada": True, "tienda": tienda.base, "usuario": str(usuario),
                    "mensaje": f"La tienda {tienda.base} está conectada" + (f" (usuario {usuario})" if usuario else "")
                               + ". Los productos se cargan siempre como borrador."}, False
        except Rechazo as motivo:
            return {"conectada": False, "mensaje": str(motivo)}, False


# --- MCP por stdio (igual que taller3d-orca) ---------------------------------------------------------------------

def _error(ident, codigo: int, mensaje: str, datos=None) -> dict:
    e = {"code": codigo, "message": mensaje}
    if datos is not None:
        e["data"] = datos
    return {"jsonrpc": "2.0", "id": ident, "error": e}


def _resultado_herramienta(salida: dict, es_error: bool) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(salida, ensure_ascii=False)}],
            "structuredContent": salida, "isError": es_error}


def procesar(servidor: Servidor, m) -> dict | None:
    if not isinstance(m, dict):
        return _error(None, -32600, "Invalid Request")
    if "method" not in m and ("result" in m or "error" in m):
        return None
    ident = m.get("id")
    es_pedido = "id" in m
    if m.get("jsonrpc") != "2.0" or not isinstance(m.get("method"), str):
        return _error(ident if isinstance(ident, (str, int)) else None, -32600, "Invalid Request")
    if es_pedido and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
        return _error(None, -32600, "Invalid Request: id tiene que ser texto o número entero")
    if not es_pedido:
        return None
    metodo, params = m["method"], m.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error(ident, -32602, "Invalid params")
    meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
    version = meta.get(META_VERSION)
    if metodo == "initialize":
        pedida = params.get("protocolVersion")
        servidor.legada = pedida if pedida in VERSIONES_LEGADAS else VERSIONES_LEGADAS[0]
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": servidor.legada, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": INFO, "instructions": INSTRUCCIONES}}
    if version is not None and not (servidor.legada and version in VERSIONES_LEGADAS):
        if version not in VERSIONES_MODERNAS:
            return _error(ident, -32022, "Unsupported protocol version",
                          {"supported": list(VERSIONES_MODERNAS), "requested": version})
        if not isinstance(meta.get(META_CAPACIDADES), dict):
            return _error(ident, -32602, f"Invalid params: falta _meta[{META_CAPACIDADES!r}]")
        moderno = True
    elif servidor.legada or metodo == "ping":
        moderno = False
    else:
        return _error(ident, -32602, f"Invalid params: falta _meta[{META_VERSION!r}] o el saludo initialize")
    try:
        return _atender(servidor, ident, metodo, params, moderno)
    except Exception as error:
        registrar(f"error interno en {metodo}: {type(error).__name__}: {error}")
        return _error(ident, -32603, "Internal error")


def _atender(servidor: Servidor, ident, metodo: str, params: dict, moderno: bool) -> dict:
    if metodo == "server/discover":
        resultado = {"supportedVersions": list(VERSIONES_MODERNAS), "capabilities": {"tools": {"listChanged": False}},
                     "instructions": INSTRUCCIONES}
    elif metodo == "ping":
        resultado = {}
    elif metodo == "tools/list":
        resultado = {"tools": HERRAMIENTAS}
    elif metodo in ("resources/list", "resources/templates/list", "prompts/list"):
        resultado = {{"resources/list": "resources", "resources/templates/list": "resourceTemplates",
                      "prompts/list": "prompts"}[metodo]: []}
    elif metodo == "tools/call":
        nombre, argumentos = params.get("name"), params.get("arguments")
        if argumentos is None:
            argumentos = {}
        if not isinstance(argumentos, dict):
            return _error(ident, -32602, "Invalid params: arguments tiene que ser un objeto")
        if nombre == "cargar_borrador":
            resultado = _resultado_herramienta(*servidor.cargar(argumentos))
        elif nombre == "estado_tienda":
            resultado = _resultado_herramienta(*servidor.estado(argumentos))
        elif nombre == "categorias_tienda":
            resultado = _resultado_herramienta(*servidor.categorias(argumentos))
        elif nombre == "crear_categoria":
            resultado = _resultado_herramienta(*servidor.crear_categoria(argumentos))
        elif nombre == "cambiar_categorias":
            resultado = _resultado_herramienta(*servidor.cambiar_categorias(argumentos))
        elif nombre == "estado_productos":
            resultado = _resultado_herramienta(*servidor.productos(argumentos))
        else:
            return _error(ident, -32602, f"Unknown tool: {nombre}")
    else:
        return _error(ident, -32601, f"Method not found: {metodo}")
    if moderno:
        resultado = {"resultType": "complete", **resultado, "_meta": {META_SERVIDOR: INFO}}
    return {"jsonrpc": "2.0", "id": ident, "result": resultado}


def procesar_linea(servidor: Servidor, linea: bytes):
    try:
        mensaje = json.loads(linea.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _error(None, -32700, "Parse error")
    if isinstance(mensaje, list):
        if not mensaje:
            return _error(None, -32600, "Invalid Request")
        respuestas = [r for r in (procesar(servidor, x) for x in mensaje) if r is not None]
        return respuestas or None
    return procesar(servidor, mensaje)


def servir() -> None:
    servidor = Servidor()
    entrada, salida = sys.stdin.buffer, sys.stdout.buffer
    registrar(f"{VERSION} listo")
    while True:
        linea = entrada.readline()
        if not linea:
            break
        if not linea.strip():
            continue
        try:
            respuesta = procesar_linea(servidor, linea)
        except Exception as error:
            registrar(f"error interno: {type(error).__name__}: {error}")
            respuesta = _error(None, -32603, "Internal error")
        if respuesta is not None:
            salida.write(json.dumps(respuesta, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
            salida.flush()


# --- Revisar la tienda sin contraseña (antes de conectarla) -----------------------------------------------------

def _base_de(destino: str) -> str:
    """La dirección de la tienda a la que lleva una redirección (sin /wp-json/... ni lo que sigue)."""
    u = urllib.parse.urlsplit(destino)
    camino = u.path.split("/wp-json")[0].rstrip("/")
    return f"{u.scheme}://{u.netloc}{camino}"


def _sitio(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    return f"{(u.hostname or '').lower()}{u.path.rstrip('/')}"


def _pedir_publico(base: str, ruta: str, abridor, tiempo: float):
    """GET sin contraseña: (código, JSON o None). Las redirecciones no se siguen: salen como Redireccion."""
    pedido = urllib.request.Request(f"{base}/wp-json{ruta}", method="GET",
                                    headers={"Accept": "application/json", "User-Agent": f"{NOMBRE}/{VERSION}"})
    try:
        with abridor.open(pedido, timeout=tiempo) as r:
            return r.status, _json(r.read(MAX_RESPUESTA + 1))
    except urllib.error.HTTPError as error:
        return error.code, _json(error.read(MAX_RESPUESTA + 1) or b"")


def _limpio(texto, largo: int = 80) -> str:
    t = html.unescape(texto) if isinstance(texto, str) else ""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", t).strip()[:largo]


def revisar_tienda(direccion, abridor=None, tiempo: float = 20.0) -> dict:
    """Revisa, sin contraseña y sin cambiar nada, si la tienda sirve para el conector: que responda en https sin
    redirecciones, que sea un WordPress con WooCommerce y que tenga las contraseñas de aplicación habilitadas.
    Devuelve {"tienda", "sirve", "nombre", "sugerida" (si redirige), "puntos": [{"que", "ok", "detalle"}]}, con ok
    True (bien), False (hay que arreglarlo antes de conectar) o None (aviso: se puede seguir)."""
    puntos: list[dict] = []
    salida = {"tienda": str(direccion or "").strip(), "sirve": False, "nombre": "", "puntos": puntos}

    def punto(que: str, ok, detalle: str) -> None:
        puntos.append({"que": que, "ok": ok, "detalle": detalle})

    try:
        base = validar_url(direccion)
    except Rechazo as motivo:
        punto("direccion", False, str(motivo))
        return salida
    salida["tienda"] = base
    abridor = abridor or urllib.request.build_opener(SinRedirecciones())

    def pedir(ruta: str):
        try:
            return _pedir_publico(base, ruta, abridor, tiempo)
        except Redireccion as r:
            otra = _base_de(r.destino)
            if _sitio(otra) == _sitio(base):
                punto("api", False, f"La API de WordPress ({base}/wp-json/) redirige a otra página "
                                    f"({_limpio(r.destino, 200)}): revisá que los enlaces permanentes no estén en "
                                    "«Simple» (Ajustes → Enlaces permanentes) y que ningún plugin redirija /wp-json/.")
                return None
            if otra.startswith("https://") or otra.startswith("http://127.0.0.1") or otra.startswith("http://localhost"):
                salida["sugerida"] = otra
            punto("api", False, f"La dirección redirige a {otra}: usá esa (con o sin www, como la muestra el navegador).")
        except Rechazo as motivo:
            punto("api", False, str(motivo))
        except urllib.error.URLError as error:
            punto("api", False, f"No pude conectarme con {base} ({error.reason}). Revisá la dirección y que la PC tenga "
                                "internet.")
        except OSError:
            punto("api", False, f"{base} no contestó a tiempo. Probá de nuevo en un rato.")
        except Exception as error:                 # una respuesta rota (http.client.HTTPException, por ejemplo)
            punto("api", False, f"{base} contestó algo que no entiendo ({type(error).__name__}). Probá de nuevo en un "
                                "rato.")
        return None

    respuesta = pedir("/")
    if respuesta is None:
        return salida
    codigo, indice = respuesta
    espacios: list[str] = []
    if codigo == 200 and isinstance(indice, dict) and isinstance(indice.get("namespaces"), list):
        nombre = _limpio(indice.get("name"))
        salida["nombre"] = nombre
        punto("api", True, "Responde en https y sin redirecciones" + (f": «{nombre}»." if nombre else "."))
        espacios = [n for n in indice["namespaces"] if isinstance(n, str)]
        if "wc/v3" in espacios:
            punto("woocommerce", True, "WooCommerce está activo.")
        else:
            punto("woocommerce", False, "No veo WooCommerce: el conector carga productos de WooCommerce. Si lo tenés, "
                                        "revisá que esté activado en Plugins.")
        autenticacion = indice.get("authentication") if isinstance(indice.get("authentication"), dict) else {}
        if "application-passwords" in autenticacion:
            punto("contrasenas", True, "Las contraseñas de aplicación están habilitadas.")
        else:
            punto("contrasenas", False,
                  "Las contraseñas de aplicación están apagadas, y sin ellas no hay cómo conectarse. Suele ser un plugin "
                  "de seguridad (en Wordfence: All Options → Brute Force Protection → «Disable WordPress application "
                  "passwords», destildado) o que WordPress no ve el sitio en https (Ajustes → Generales).")
        home = indice.get("home") if isinstance(indice.get("home"), str) else ""
        if home and _sitio(home) != _sitio(base):
            punto("direccion", None, f"WordPress dice que su dirección es {_limpio(home, 200)}: si algo falla, probá "
                                     "con esa.")
    elif codigo in (401, 403) and isinstance(indice, dict) and str(indice.get("code", "")).startswith("rest_"):
        punto("api", None, "La API de WordPress no le contesta a cualquiera (la cierra un plugin para los visitantes): "
                           "sin contraseña no puedo ver más. Se prueba con tu contraseña de aplicación.")
    elif codigo == 404:
        punto("api", False, f"No encuentro la API de WordPress en {base}/wp-json/. Si es un WordPress, en Ajustes → "
                            "Enlaces permanentes elegí cualquier opción menos «Simple» y guardá. Si no es un WordPress, "
                            "este conector no sirve para esa tienda.")
    else:
        que = "una página" if indice is None else "algo que no es la API"
        punto("api", False, f"{base}/wp-json/ contestó {codigo} con {que}: puede ser un firewall del hosting o un plugin "
                            "de seguridad que bloquea la API. Tiene que dejar pasar /wp-json/.")
    if "wc/v3" in espacios and all(p["ok"] is not False for p in puntos):
        respuesta = pedir("/wc/v3/products?per_page=1")
        if respuesta is not None:
            codigo, cuerpo = respuesta
            if codigo in (401, 403) and isinstance(cuerpo, dict):
                punto("productos", True, "La API de productos responde y pide contraseña, como tiene que ser.")
            elif codigo == 200:
                punto("productos", None, "La API de productos contesta sin contraseña: no es lo normal, revisá los "
                                         "permisos de WooCommerce.")
            else:
                que = "una página" if cuerpo is None else "un error"
                punto("productos", False, f"La API de productos de WooCommerce contestó {codigo} con {que}: puede ser un "
                                          "firewall o un plugin de seguridad. Tiene que dejar pasar /wp-json/wc/.")
    salida["sirve"] = bool(puntos) and all(p["ok"] is not False for p in puntos)
    return salida


def mostrar_revision(informe: dict) -> None:
    marcas = {True: "[ok]   ", False: "[falta]", None: "[aviso]"}
    for p in informe.get("puntos") or []:
        print(f"   {marcas.get(p.get('ok'), '[aviso]')} {p.get('detalle', '')}")


def _con_esquema(direccion: str) -> str:
    d = (direccion or "").strip()
    return "https://" + d if d and "://" not in d else d


def _preguntar_si(texto: str) -> bool:
    r = input(f"   {texto} (S/n): ").strip().lower()
    return r in ("", "s", "si", "sí", "y", "yes")


def _revisar_para_conectar(tienda: str) -> tuple[str, dict]:
    """Revisa la tienda antes de pedir la contraseña; si redirige a otra dirección, ofrece usar esa."""
    print(f"   Revisando {tienda} (sin contraseña: solo lo que la tienda le muestra a cualquiera)…")
    informe = revisar_tienda(tienda)
    mostrar_revision(informe)
    otra = informe.get("sugerida")
    if not informe["sirve"] and otra and otra != tienda and _preguntar_si(f"¿Uso {otra}?"):
        tienda = otra
        print(f"   Revisando {tienda}…")
        informe = revisar_tienda(tienda)
        mostrar_revision(informe)
    return tienda, informe


def _conexion_anterior() -> dict:
    ruta = ruta_credenciales(os.environ)
    if not os.path.isfile(ruta):
        return {}
    try:
        datos = _leer_json(ruta, MAX_CREDENCIALES, "el archivo de la tienda")
    except Rechazo:
        return {}
    return datos if isinstance(datos, dict) else {}


def revisar(argumentos) -> int:
    ap = argparse.ArgumentParser(prog="tienda_mcp.py revisar",
                                 description="Revisa sin contraseña, y sin cambiar nada, si tu tienda sirve para el "
                                             "conector del taller.")
    ap.add_argument("--tienda", help="dirección de la tienda (https://...)")
    a = ap.parse_args(argumentos)
    try:
        tienda = a.tienda or _preguntar("Dirección de tu tienda", str(_conexion_anterior().get("tienda") or ""))
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    tienda, informe = _revisar_para_conectar(_con_esquema(tienda))
    if informe["sirve"]:
        print("   Tu tienda sirve para el conector. Lo que sigue es crear la contraseña de aplicación y conectarla con: "
              + como_reconectar())
        return 0
    print("   Hay que resolver lo marcado con [falta] antes de conectar la tienda.")
    return 1


# --- Configurar desde una terminal (lo hace el usuario, una vez) -------------------------------------------------

def _preguntar(texto: str, defecto: str = "") -> str:
    r = input(f"   {texto}" + (f" [{defecto}]" if defecto else "") + ": ").strip()
    return r or defecto


def configurar(argumentos) -> int:
    ap = argparse.ArgumentParser(prog="tienda_mcp.py configurar",
                                 description="Guarda la conexión con tu tienda WooCommerce (una sola vez).")
    ap.add_argument("--tienda", help="dirección de la tienda (https://...)")
    ap.add_argument("--usuario", help="tu usuario de WordPress")
    a = ap.parse_args(argumentos)
    ruta = ruta_credenciales(os.environ)
    anterior = _conexion_anterior()
    print("Conectar el taller 3D con tu tienda WooCommerce (los productos se cargan siempre como borrador).")
    print("Antes, creá una contraseña de aplicación en tu WordPress: Usuarios → Perfil → Contraseñas de aplicación,")
    print("con el nombre «Taller 3D» → Añadir. WordPress la muestra una sola vez: copiala.")
    try:
        tienda = validar_url(_con_esquema(a.tienda or _preguntar("Dirección de tu tienda",
                                                                  str(anterior.get("tienda") or ""))))
        tienda, informe = _revisar_para_conectar(tienda)
        if not informe["sirve"]:
            print("   No te pido la contraseña hasta que eso esté resuelto. Cuando lo arregles, corré de nuevo: "
                  + como_reconectar())
            return 1
        usuario = a.usuario or _preguntar("Tu usuario de WordPress", str(anterior.get("usuario") or ""))
        clave = getpass.getpass("   Contraseña de aplicación (no se ve mientras la escribís): ").strip()
    except Rechazo as motivo:
        print(f"   {motivo}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n   No guardé nada.")
        return 1
    if not usuario or not clave:
        print("   Faltan el usuario o la contraseña: no guardé nada.")
        return 1
    t = Tienda(tienda, usuario, clave)
    try:
        _, yo = t.pedir("GET", "/wp/v2/users/me", params={"context": "edit"})
        t.pedir("GET", "/wc/v3/products", params={"per_page": 1})
    except Rechazo as motivo:
        print(f"   No pude conectarme: {motivo}")
        print("   No guardé nada. Revisá los datos y corré de nuevo: " + como_reconectar())
        return 1
    guardar_credenciales(ruta, tienda, usuario, clave)
    nombre = (yo or {}).get("name") if isinstance(yo, dict) else None
    print(f"   Listo: la tienda {tienda} quedó conectada" + (f" (usuario {nombre})" if nombre else "") + ".")
    print(f"   La conexión quedó en {ruta}, que solo puede leer tu usuario.")
    return 0


def probar() -> int:
    salida, _ = Servidor().estado({})
    print(f"   {salida['mensaje']}")
    return 0 if salida.get("conectada") else 1


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "configurar":
        sys.exit(configurar(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "revisar":
        sys.exit(revisar(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "probar":
        sys.exit(probar())
    if len(sys.argv) > 1:
        sys.exit("Uso: tienda_mcp.py [revisar | configurar | probar] (sin nada, atiende a la app de Claude por MCP).")
    servir()


if __name__ == "__main__":
    main()
