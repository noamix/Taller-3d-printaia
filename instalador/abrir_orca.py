#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""taller3d-orca: servidor MCP local (stdio, solo biblioteca estándar) del taller, con dos herramientas.

  abrir_en_orca(ruta)            abre en la ventana de OrcaSlicer un proyecto .3mf que esté dentro de la carpeta de
                                 trabajo del taller. No lamina, no imprime, no manda nada a la impresora, no escribe
                                 ni borra archivos.
  mandar_a_la_papelera(carpeta)  manda a la papelera de la PC (se recupera desde ahí hasta que se vacía) la carpeta
                                 entera de una pieza: impresiones/AAAA-MM-DD_nombre o disenos/AAAA-MM-DD_nombre, y
                                 nada más. Claude la usa solo después de que el usuario confirmó en el chat, viendo qué
                                 se borra. Nunca borra para siempre.

Lo arranca la app de escritorio de Claude (entrada "taller3d-orca" de claude_desktop_config.json, que escribe el
instalador). La configuración sale solo de esa entrada, nunca de la herramienta ni de archivos que Claude pueda
escribir (la carpeta de trabajo, por ejemplo):
  TALLER3D_CARPETA  carpeta de trabajo (ruta absoluta).
  TALLER3D_ORCA     comando que abre Orca, como lista JSON y sin el archivo:
                      ["/home/u/.local/bin/orca-slicer-taller"]
                      ["/usr/bin/flatpak", "run", "com.orcaslicer.OrcaSlicer"]
                      ["C:\\\\Program Files\\\\OrcaSlicer\\\\orca-slicer.exe", "--datadir", "C:\\\\Users\\\\u\\\\OrcaSlicer"]
                      ["/usr/bin/open", "-a", "/Applications/OrcaSlicer.app"]
  TALLER3D_LANZAR   (Linux, opcional) auto (por defecto) | systemd | directo.

Habla MCP por stdio en las dos épocas del protocolo: con el saludo initialize (2025-11-25 y anteriores) y con la
versión en cada pedido (2026-07-28, server/discover).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import zipfile

NOMBRE = "taller3d-orca"
VERSION = "0.2.0"
INFO = {"name": NOMBRE, "title": "Taller 3D: abrir en OrcaSlicer y mandar piezas a la papelera", "version": VERSION}
VERSIONES_MODERNAS = ("2026-07-28",)
VERSIONES_LEGADAS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPACIDADES = "io.modelcontextprotocol/clientCapabilities"
META_SERVIDOR = "io.modelcontextprotocol/serverInfo"

# Las mismas que rechaza perfil_orca.py: Orca las ejecuta al laminar.
CLAVES_QUE_EJECUTAN = ("post_process", "plugins", "slicing_pipeline_plugin")
VARIABLES_GRAFICAS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY")
MAX_RUTA = 1024
MAX_PROYECTO = 512 * 1024 * 1024
MAX_PARTES = 20000
MAX_CONFIG = 8 * 1024 * 1024

INSTRUCCIONES = (
    "Servidor local del taller 3D (plugin taller-3d). abrir_en_orca abre en la ventana de OrcaSlicer un proyecto .3mf "
    "de la carpeta de trabajo del taller: usala cuando el usuario pida ver o abrir una pieza en Orca, también cuando "
    "el pedido llega desde el panel. Solo abre la ventana: imprimir es siempre del usuario; nunca uses la pestaña "
    "Dispositivo de Orca ni sus botones Imprimir o Enviar. mandar_a_la_papelera manda a la papelera de la PC la "
    "carpeta entera de una pieza (impresiones/… o disenos/…): usala SOLO después de mostrarle al usuario qué se borra "
    "(cuántos archivos y cuánto ocupa, y si está en la tienda) y de que confirme en el chat. Nunca borra para siempre "
    "ni toca nada fuera de esa carpeta.")
MAX_ARCHIVOS_CONTADOS = 100000

HERRAMIENTA = {
    "name": "abrir_en_orca",
    "title": "Abrir un proyecto en OrcaSlicer",
    "description": (
        "Abre en la ventana de OrcaSlicer, en la PC del usuario, un proyecto .3mf de la carpeta de trabajo del "
        "taller 3D, para ver o tocar la pieza. Solo abre la ventana: no lamina, no imprime y no manda nada a la "
        "impresora (imprimir es siempre del usuario). `ruta`: el .3mf, relativo a la carpeta de trabajo (por "
        "ejemplo impresiones/2026-11-21_soporte_ender-3-v3-plus/soporte_ender-3-v3-plus.3mf) o absoluto dentro de "
        "ella. Rechaza otros archivos, otras carpetas y proyectos con scripts de posprocesado o plugins."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "ruta": {"type": "string", "minLength": 1, "maxLength": MAX_RUTA,
                     "description": "El proyecto .3mf, relativo a la carpeta de trabajo o absoluto dentro de ella."},
        },
        "required": ["ruta"],
        "additionalProperties": False,
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "abierto": {"type": "boolean", "description": "Si Orca quedó abriendo el proyecto."},
            "mensaje": {"type": "string", "description": "Qué pasó, para mostrarle al usuario."},
            "ruta": {"type": "string", "description": "El proyecto, relativo a la carpeta de trabajo."},
            "repetido": {"type": "boolean", "description": "El mismo pedido llegó hace un momento: no se abrió otra vez."},
        },
        "required": ["abierto", "mensaje"],
    },
    # Abre un programa: no es de solo lectura (la app puede pedir confirmación), pero no borra ni cambia nada.
    "annotations": {"title": "Abrir en OrcaSlicer", "readOnlyHint": False, "destructiveHint": False,
                    "idempotentHint": False, "openWorldHint": False},
}

PAPELERA = {
    "name": "mandar_a_la_papelera",
    "title": "Mandar una pieza a la papelera",
    "description": (
        "Manda a la papelera de la PC del usuario la carpeta entera de una pieza del taller 3D, con todo lo que tiene "
        "adentro (modelo, G-code, proyecto de Orca, fotos, publicación). Se puede recuperar desde la papelera hasta "
        "que el usuario la vacíe: nunca borra para siempre. Usala SOLO después de que el usuario confirmó en el chat "
        "que quiere borrar esa pieza, viendo qué se borra. No toca nada fuera de esa carpeta, ni la tienda. "
        "`carpeta`: relativa a la carpeta de trabajo, impresiones/AAAA-MM-DD_nombre o disenos/AAAA-MM-DD_nombre."),
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
            "borrado": {"type": "boolean", "description": "Si la carpeta quedó en la papelera."},
            "mensaje": {"type": "string", "description": "Qué pasó, para mostrarle al usuario."},
            "carpeta": {"type": "string"},
            "archivos": {"type": "integer", "description": "Cuántos archivos tenía."},
            "bytes": {"type": "integer", "description": "Cuánto ocupaba."},
            "papelera": {"type": "string", "description": "A qué papelera fue."},
        },
        "required": ["borrado", "mensaje"],
    },
    # Mueve archivos a la papelera: destructivo (la app puede pedir confirmación), aunque se recupera desde ahí.
    "annotations": {"title": "Mandar a la papelera", "readOnlyHint": False, "destructiveHint": True,
                    "idempotentHint": False, "openWorldHint": False},
}
HERRAMIENTAS = [HERRAMIENTA, PAPELERA]


class Rechazo(Exception):
    """Un motivo para no abrir, que se le cuenta a quien pidió."""


def registrar(texto: str) -> None:
    """Registro en stderr (la app de Claude lo guarda en el log del servidor). stdout es solo para MCP."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {NOMBRE}: {texto}", file=sys.stderr, flush=True)


def _numero(entorno, clave: str, defecto: float) -> float:
    try:
        return max(0.0, float(entorno.get(clave, defecto)))
    except ValueError:
        return defecto


# --- Rutas ------------------------------------------------------------------------------------------------------

def dentro_de(ruta: str, raiz: str) -> bool:
    """¿`ruta` (ya resuelta) está dentro de `raiz` (ya resuelta), sin ser la raíz misma?"""
    r, b = os.path.normcase(ruta), os.path.normcase(raiz)
    try:
        return r != b and os.path.commonpath([r, b]) == b
    except ValueError:                                     # otra unidad de disco en Windows
        return False


def _con_control(texto: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in texto)


def validar_ruta(pedida, raiz: str) -> str:
    """La ruta real del proyecto si se puede abrir; si no, Rechazo con el motivo."""
    if not isinstance(pedida, str):
        raise Rechazo("`ruta` tiene que ser texto: la ruta del proyecto .3mf.")
    if not pedida.strip():
        raise Rechazo("Falta la ruta del proyecto .3mf.")
    if len(pedida) > MAX_RUTA:
        raise Rechazo("La ruta es demasiado larga.")
    if _con_control(pedida):
        raise Rechazo("La ruta tiene caracteres de control.")
    if "://" in pedida:
        raise Rechazo("Pasá la ruta del archivo, no un enlace (computer:// o file://).")
    if pedida.startswith("~"):
        raise Rechazo("Pasá la ruta completa o relativa a la carpeta de trabajo (sin ~).")
    if os.name == "nt":
        if pedida.startswith(("\\\\", "//")):                # red (SMB) o \\?\: ni siquiera se resuelven
            raise Rechazo("No abro archivos de la red ni rutas especiales de Windows.")
        if ":" in pedida and not re.match(r"^[A-Za-z]:[\\/][^:]*$", pedida):
            raise Rechazo("La ruta tiene ':' fuera de la letra de la unidad.")   # flujos NTFS, C:relativa
        partes = re.split(r"[\\/]+", pedida)
    else:
        partes = pedida.split("/")
    if ".." in partes:
        raise Rechazo("La ruta no puede tener '..': pasá la ruta del .3mf dentro de la carpeta de trabajo.")
    candidato = pedida if os.path.isabs(pedida) else os.path.join(raiz, pedida)
    real = os.path.realpath(candidato)                      # sigue los enlaces simbólicos
    if not dentro_de(real, raiz):
        raise Rechazo("Solo abro proyectos que estén dentro de la carpeta de trabajo del taller "
                      "(tampoco a través de enlaces que salgan de ella).")
    if not (os.path.basename(candidato).lower().endswith(".3mf") and os.path.basename(real).lower().endswith(".3mf")):
        raise Rechazo("Solo abro proyectos de Orca (.3mf).")
    if _con_control(real):
        raise Rechazo("La ruta real tiene caracteres de control.")
    try:
        datos = os.stat(real)
    except FileNotFoundError:
        raise Rechazo("No existe ese proyecto en la carpeta de trabajo.") from None
    except OSError as error:
        raise Rechazo(f"No puedo leer ese proyecto ({error.strerror or error}).") from None
    if not stat.S_ISREG(datos.st_mode):
        raise Rechazo("Esa ruta no es un archivo.")
    if datos.st_size > MAX_PROYECTO:
        raise Rechazo("El proyecto es demasiado grande para abrirlo desde acá: abrilo con doble clic.")
    revisar_3mf(real)
    return real


# --- Contenido del .3mf -----------------------------------------------------------------------------------------

def _tiene_valor(valor) -> bool:
    valores = valor if isinstance(valor, list) else [valor]
    return any(str(v).strip() for v in valores if v is not None)


def claves_que_ejecutan(datos: bytes) -> list[str]:
    """Las claves que hacen que Orca ejecute algo, con valor, en un archivo de configuración del proyecto:
    JSON (Orca y Bambu), INI (PrusaSlicer, que Orca importa) o XML (ajustes por objeto)."""
    texto = datos.decode("utf-8", "replace")
    halladas = set()
    try:
        objeto = json.loads(texto)
    except ValueError:
        objeto = None
    if isinstance(objeto, dict):
        halladas.update(k for k in CLAVES_QUE_EJECUTAN if _tiene_valor(objeto.get(k)))
    for clave in CLAVES_QUE_EJECUTAN:
        for m in re.finditer(rf"(?im)^[ \t;#]*{clave}[ \t]*=[ \t]*(.*?)[ \t]*$", texto):
            if m.group(1) not in ("", '""', "''", "[]"):
                halladas.add(clave)
        for m in re.finditer(rf'key\s*=\s*"{clave}"\s+value\s*=\s*"([^"]*)"', texto):
            if m.group(1).strip():
                halladas.add(clave)
    return sorted(halladas)


def revisar_3mf(ruta: str) -> None:
    """Que sea un 3MF de verdad y sin scripts de posprocesado ni plugins (Orca los correría al laminar)."""
    try:
        with zipfile.ZipFile(ruta) as z:
            partes = z.infolist()
            if len(partes) > MAX_PARTES:
                raise Rechazo("El proyecto tiene demasiadas partes adentro: no parece un .3mf normal.")
            if not any(p.filename.lower().endswith(".model") for p in partes):
                raise Rechazo("No parece un proyecto 3MF: no tiene un modelo 3D adentro.")
            for parte in partes:
                nombre = parte.filename.lower()
                if not (nombre.startswith("metadata/") and nombre.endswith(".config")):
                    continue
                if parte.file_size > MAX_CONFIG:
                    raise Rechazo("La configuración del proyecto es demasiado grande para revisarla.")
                with z.open(parte) as f:
                    datos = f.read(MAX_CONFIG + 1)
                if len(datos) > MAX_CONFIG:
                    raise Rechazo("La configuración del proyecto es demasiado grande para revisarla.")
                halladas = claves_que_ejecutan(datos)
                if halladas:
                    raise Rechazo(f"El proyecto trae {', '.join(halladas)} ({parte.filename}): Orca correría "
                                  "programas o plugins al laminar. No lo abro desde acá; si es tuyo y confiás en "
                                  "él, abrilo vos con doble clic.")
    except zipfile.BadZipFile:
        raise Rechazo("No es un proyecto .3mf válido (no es un archivo ZIP).") from None
    except Rechazo:
        raise
    except Exception as error:                              # zlib, compresión rara, archivo cortado
        raise Rechazo(f"No pude revisar el proyecto ({type(error).__name__}).") from None


# --- Configuración ----------------------------------------------------------------------------------------------

def carpeta_de_trabajo(entorno) -> str:
    """La carpeta de trabajo (resuelta), de la entrada de la app. Rechazo si algo no cierra."""
    carpeta = entorno.get("TALLER3D_CARPETA", "")
    if not carpeta or not os.path.isabs(carpeta):
        raise Rechazo("Falta configurar la carpeta de trabajo (TALLER3D_CARPETA, ruta completa) en la entrada "
                      "taller3d-orca de la app de Claude: volvé a correr el instalador del taller.")
    raiz = os.path.realpath(carpeta)
    if not os.path.isdir(raiz):
        raise Rechazo(f"No encuentro la carpeta de trabajo ({carpeta}).")
    casa = os.path.realpath(os.path.expanduser("~"))
    if os.path.normcase(raiz) == os.path.normcase(casa) or os.path.dirname(raiz) == raiz:
        raise Rechazo("La carpeta de trabajo no puede ser tu carpeta personal entera ni la raíz del disco.")
    return raiz


def configuracion(entorno) -> tuple[str, list[str]]:
    """Carpeta de trabajo (resuelta) y comando de Orca, de la entrada de la app. Rechazo si algo no cierra."""
    raiz = carpeta_de_trabajo(entorno)
    try:
        comando = json.loads(entorno.get("TALLER3D_ORCA", ""))
    except ValueError:
        comando = None
    if not (isinstance(comando, list) and comando and all(isinstance(x, str) and x for x in comando)):
        raise Rechazo("Falta configurar Orca (TALLER3D_ORCA, una lista JSON con el programa) en la entrada "
                      "taller3d-orca de la app de Claude: volvé a correr el instalador del taller.")
    programa = comando[0]
    if not os.path.isabs(programa):
        raise Rechazo("TALLER3D_ORCA tiene que empezar con la ruta completa del programa.")
    real = os.path.realpath(programa)
    if not os.path.isfile(real) or not os.access(real, os.X_OK):
        raise Rechazo(f"No encuentro el programa de Orca ({programa}).")
    if dentro_de(real, raiz) or dentro_de(os.path.abspath(programa), raiz):
        raise Rechazo("El programa de Orca no puede estar dentro de la carpeta de trabajo (ahí escribe Claude).")
    return raiz, comando


# --- Abrir Orca -------------------------------------------------------------------------------------------------

def _buscar(programa: str, entorno) -> str | None:
    return shutil.which(programa, path=entorno.get("PATH") or "/usr/local/bin:/usr/bin:/bin")


def _carpeta_runtime(entorno) -> str | None:
    """XDG_RUNTIME_DIR, o /run/user/<uid> si la app no lo pasó: ahí está el bus de la sesión del usuario."""
    for carpeta in (entorno.get("XDG_RUNTIME_DIR"), f"/run/user/{os.getuid()}"):
        try:
            if carpeta and os.path.isabs(carpeta) and os.stat(carpeta).st_uid == os.getuid():
                return carpeta
        except OSError:
            continue
    return None


def _es_socket(ruta: str) -> bool:
    try:
        return stat.S_ISSOCK(os.stat(ruta).st_mode)
    except OSError:
        return False


def entorno_de_la_sesion(entorno) -> dict[str, str]:
    """El entorno de la sesión gráfica del usuario según systemd --user (solo lectura)."""
    systemctl, runtime = _buscar("systemctl", entorno), _carpeta_runtime(entorno)
    if not systemctl or not runtime:
        return {}
    try:
        r = subprocess.run([systemctl, "--user", "show-environment"], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=5, env={**entorno, "XDG_RUNTIME_DIR": runtime})
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}
    sesion = {}
    for linea in r.stdout.splitlines():
        clave, igual, valor = linea.partition("=")
        if igual and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", clave) and not valor.startswith("$'"):
            sesion[clave] = valor
    return sesion


def entorno_grafico(entorno) -> tuple[dict[str, str], dict[str, str]]:
    """(variables de la pantalla, entorno de la sesión). Si la app no pasó DISPLAY ni WAYLAND_DISPLAY, las toma de
    la sesión del usuario (systemd --user), que las tiene en Ubuntu."""
    propias = {k: entorno[k] for k in VARIABLES_GRAFICAS if entorno.get(k)}
    if propias.get("DISPLAY") or propias.get("WAYLAND_DISPLAY"):
        return propias, {}
    sesion = entorno_de_la_sesion(entorno)
    graficas = {k: v for k, v in sesion.items() if k in VARIABLES_GRAFICAS and v and not _con_control(v)}
    return graficas, sesion


def _esperar(proceso: subprocess.Popen, espera: float) -> dict:
    """Unos segundos para ver si Orca se cierra enseguida (error); después lo deja andar solo."""
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        codigo = proceso.poll()
        if codigo is not None:
            if codigo != 0:
                raise Rechazo(f"Orca se cerró enseguida (código {codigo}). Probá abrir el .3mf con doble clic "
                              "para ver qué dice.")
            return {"via": "directo", "terminado": True}
        time.sleep(0.05)
    threading.Thread(target=proceso.wait, daemon=True).start()   # lo recoge cuando se cierre (sin zombis)
    return {"via": "directo"}


def _lanzar_directo(argv: list[str], carpeta: str, env: dict, espera: float) -> dict:
    """Linux y macOS: proceso aparte, en su propia sesión (no recibe las señales del servidor), sin la entrada ni
    la salida del servidor: lo que imprima Orca no puede mezclarse con los mensajes MCP."""
    try:
        proceso = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True, cwd=carpeta,
                                   env=env)
    except OSError as error:
        raise Rechazo(f"No pude ejecutar Orca ({argv[0]}): {error.strerror or error}.") from None
    return _esperar(proceso, espera)


def _lanzar_windows(argv: list[str], carpeta: str, espera: float) -> dict:
    """Windows: proceso desacoplado; si la app lo permite, fuera de su grupo de procesos (job), así Orca sigue
    abierto aunque se cierre la app de Claude. Sin probar en una PC con Windows."""
    base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP      # type: ignore[attr-defined]
    ultimo = None
    for banderas in (base | subprocess.CREATE_BREAKAWAY_FROM_JOB, base):         # type: ignore[attr-defined]
        try:
            proceso = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, close_fds=True, creationflags=banderas, cwd=carpeta)
            return _esperar(proceso, espera)
        except OSError as error:
            ultimo = error
    raise Rechazo(f"No pude ejecutar Orca ({argv[0]}): {ultimo}.")


def _lanzar_systemd(argv: list[str], graficas: dict, entorno, espera: float, obligatorio: bool) -> dict | None:
    """Linux: Orca como servicio de la sesión del usuario (systemd-run --user). Toma el entorno de la sesión y
    queda fuera del árbol de procesos de la app de Claude: si la app se cierra, Orca sigue abierto."""
    systemd_run, runtime = _buscar("systemd-run", entorno), _carpeta_runtime(entorno)
    if not systemd_run or not runtime or not _es_socket(os.path.join(runtime, "bus")):
        if obligatorio:
            raise Rechazo("No encuentro systemd-run o la sesión de systemd del usuario.")
        return None
    unidad = f"taller3d-orca-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{int(time.monotonic() * 1000) % 100000}"
    args = [systemd_run, "--user", "--quiet", "--collect", f"--unit={unidad}",
            "--description=OrcaSlicer abierto por taller-3d"]
    args += [f"--setenv={k}={v}" for k, v in sorted(graficas.items()) if k in VARIABLES_GRAFICAS]
    args += ["--", *argv]
    env = {**entorno, "XDG_RUNTIME_DIR": runtime}
    try:
        r = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20, env=env)
        fallo = None if r.returncode == 0 else (r.stderr or r.stdout or f"código {r.returncode}").strip()[:300]
    except (OSError, subprocess.SubprocessError) as error:
        fallo = str(error)
    if fallo:
        if obligatorio:
            raise Rechazo(f"systemd-run no pudo abrir Orca: {fallo}")
        registrar(f"systemd-run falló ({fallo}); lo abro directo")
        return None
    time.sleep(espera)
    systemctl = _buscar("systemctl", entorno)
    estado = ""
    if systemctl:
        try:
            estado = subprocess.run([systemctl, "--user", "is-active", unidad], stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=5, env=env).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            estado = ""
    if estado in ("active", "activating", "reloading"):
        return {"via": "systemd-run", "unidad": unidad}
    return {"via": "systemd-run", "unidad": unidad, "sin_confirmar": True}


def lanzar(comando: list[str], ruta: str, entorno) -> dict:
    """Abre Orca con el proyecto: sin terminal de por medio, con el programa configurado y la ruta como un solo
    argumento absoluto (no puede tomarse por una opción de Orca)."""
    argv, carpeta = [*comando, ruta], os.path.dirname(ruta)
    espera = _numero(entorno, "TALLER3D_ESPERA_S", 1.5)
    if os.name == "nt":
        return _lanzar_windows(argv, carpeta, espera)
    if sys.platform == "darwin":
        return _lanzar_directo(argv, carpeta, dict(entorno), espera)
    graficas, sesion = entorno_grafico(entorno)
    if not (graficas.get("DISPLAY") or graficas.get("WAYLAND_DISPLAY")):
        raise Rechazo("No encuentro una sesión gráfica abierta en la PC (DISPLAY o WAYLAND_DISPLAY): Orca no puede "
                      "mostrar su ventana. Abrí el .3mf con doble clic cuando estés en la PC.")
    modo = entorno.get("TALLER3D_LANZAR", "auto")
    if modo not in ("auto", "systemd", "directo"):
        raise Rechazo("TALLER3D_LANZAR tiene que ser auto, systemd o directo.")
    if modo != "directo":
        hecho = _lanzar_systemd(argv, graficas, entorno, espera, obligatorio=(modo == "systemd"))
        if hecho:
            return hecho
    return _lanzar_directo(argv, carpeta, {**sesion, **entorno, **graficas}, espera)


# --- La herramienta ---------------------------------------------------------------------------------------------

# --- Mandar una pieza a la papelera ----------------------------------------------------------------------------

CARPETAS_DE_PIEZAS = ("impresiones", "disenos")
RE_PIEZA = re.compile(r"^\d{4}-\d{2}-\d{2}_[^\\/:]+$")


def validar_pieza(pedida, raiz: str) -> str:
    """La ruta real de la carpeta de una pieza (impresiones/… o disenos/…, un nivel adentro); si no, Rechazo."""
    uso = ("Solo mando a la papelera la carpeta de una pieza, relativa a la carpeta de trabajo: "
           "impresiones/AAAA-MM-DD_nombre o disenos/AAAA-MM-DD_nombre.")
    if not isinstance(pedida, str) or not pedida.strip():
        raise Rechazo("Falta `carpeta`. " + uso)
    if len(pedida) > MAX_RUTA or _con_control(pedida):
        raise Rechazo("La carpeta es demasiado larga o tiene caracteres de control.")
    texto = pedida.strip()
    if "://" in texto or texto.startswith(("~", "/", "\\")) or re.match(r"^[A-Za-z]:", texto):
        raise Rechazo(uso)
    partes = texto.replace("\\", "/").strip("/").split("/")
    if len(partes) != 2 or partes[0] not in CARPETAS_DE_PIEZAS or not RE_PIEZA.match(partes[1]) \
            or partes[1].endswith((".", " ")):
        raise Rechazo(uso)
    padre = os.path.join(raiz, partes[0])
    candidato = os.path.join(padre, partes[1])
    if os.path.islink(padre) or os.path.islink(candidato):
        raise Rechazo("Esa carpeta es un enlace: no la toco. Borrala a mano si querés.")
    real = os.path.realpath(candidato)
    if os.path.normcase(os.path.dirname(real)) != os.path.normcase(os.path.realpath(padre)) \
            or not dentro_de(real, raiz):
        raise Rechazo(uso)
    if not os.path.isdir(real):
        raise Rechazo(f"No existe la carpeta {partes[0]}/{partes[1]} en el taller (¿ya estaba borrada?).")
    return real


def contar(real: str) -> tuple[int, int]:
    """Cuántos archivos tiene la carpeta y cuánto ocupan (sin seguir enlaces)."""
    archivos = peso = 0
    for raiz, carpetas, nombres in os.walk(real, followlinks=False):
        for nombre in nombres + [c for c in carpetas if os.path.islink(os.path.join(raiz, c))]:
            archivos += 1
            try:
                peso += os.lstat(os.path.join(raiz, nombre)).st_size
            except OSError:
                pass
            if archivos >= MAX_ARCHIVOS_CONTADOS:
                return archivos, peso
    return archivos, peso


def _nombre_libre(carpeta: str, base: str, sufijo: str = "") -> str:
    nombre, n = base, 1
    while os.path.lexists(os.path.join(carpeta, nombre + sufijo)):
        n += 1
        nombre = f"{base}.{n}"
    return nombre


def _papelera_freedesktop(real: str, entorno) -> str:
    """La papelera del usuario según freedesktop.org (la misma del explorador de archivos): ~/.local/share/Trash."""
    casa = os.path.expanduser("~")
    datos = entorno.get("XDG_DATA_HOME") or ""
    if not os.path.isabs(datos):
        datos = os.path.join(casa, ".local", "share")
    papelera = os.path.join(datos, "Trash")
    archivos, info = os.path.join(papelera, "files"), os.path.join(papelera, "info")
    os.makedirs(archivos, mode=0o700, exist_ok=True)
    os.makedirs(info, mode=0o700, exist_ok=True)
    base = os.path.basename(real)
    while True:
        nombre = _nombre_libre(archivos, base)
        ruta_info = os.path.join(info, nombre + ".trashinfo")
        try:
            fd = os.open(ruta_info, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            base = nombre + ".x"
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"[Trash Info]\nPath={urllib.parse.quote(real)}\nDeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    try:
        os.rename(real, os.path.join(archivos, nombre))
    except OSError as error:
        try:
            os.unlink(ruta_info)
        except OSError:
            pass
        raise Rechazo(f"No pude mandarla a la papelera ({error.strerror or error}): puede que esté en otro disco. "
                      "Borrala a mano desde el explorador de archivos.") from None
    return papelera


def _papelera_mac(real: str) -> str:
    papelera = os.path.join(os.path.expanduser("~"), ".Trash")
    destino = os.path.join(papelera, _nombre_libre(papelera, os.path.basename(real)))
    try:
        os.rename(real, destino)
    except OSError as error:
        raise Rechazo(f"No pude mandarla a la papelera ({error.strerror or error}): borrala a mano desde el Finder.") from None
    return papelera


def _papelera_windows(real: str) -> str:
    """La papelera de reciclaje, con SHFileOperationW y FOF_ALLOWUNDO. Sin probar en una PC con Windows."""
    import ctypes
    from ctypes import wintypes

    class Operacion(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    borrar, silencio, sin_preguntar, deshacer, sin_errores = 3, 0x4, 0x10, 0x40, 0x400
    op = Operacion(None, borrar, real + "\0", None, deshacer | sin_preguntar | silencio | sin_errores, False, None,
                   None)
    if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) != 0 or op.fAnyOperationsAborted:  # type: ignore[attr-defined]
        raise Rechazo("No pude mandarla a la papelera de reciclaje: borrala a mano desde el Explorador de archivos.")
    return "Papelera de reciclaje"


def a_la_papelera(real: str, entorno) -> str:
    """Manda la carpeta a la papelera del sistema; devuelve a cuál. Nunca borra para siempre."""
    if os.name == "nt":
        return _papelera_windows(real)
    if sys.platform == "darwin":
        return _papelera_mac(real)
    gio = _buscar("gio", entorno)                           # GNOME y otros: conoce también las papeleras de otros discos
    if gio:
        try:
            r = subprocess.run([gio, "trash", "--", real], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=120)
            if r.returncode == 0 and not os.path.lexists(real):
                return "papelera de la PC (gio)"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return _papelera_freedesktop(real, entorno)


def _peso(bytes_: int) -> str:
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB".replace(".", ",")
    return f"{max(1, round(bytes_ / 1024))} KB" if bytes_ else "0 KB"


class Servidor:
    def __init__(self, entorno=None):
        self.entorno = dict(os.environ if entorno is None else entorno)
        self.legada: str | None = None                       # versión legada acordada con initialize
        self.ultimo = float("-inf")
        self.abiertos: dict[str, float] = {}
        self.intervalo = _numero(self.entorno, "TALLER3D_INTERVALO_S", 3.0)
        self.repetido = _numero(self.entorno, "TALLER3D_REPETIDO_S", 20.0)

    def abrir(self, argumentos: dict) -> tuple[dict, bool]:
        """(structuredContent, isError)."""
        pedida = argumentos.get("ruta")
        try:
            extra = sorted(set(argumentos) - {"ruta"})
            if extra:
                raise Rechazo(f"Solo acepto `ruta` (sobra: {', '.join(map(str, extra))}).")
            raiz, comando = configuracion(self.entorno)
            real = validar_ruta(pedida, raiz)
            relativa = os.path.relpath(real, raiz).replace(os.sep, "/")
            ahora = time.monotonic()
            previo = self.abiertos.get(real)
            if previo is not None and ahora - previo < self.repetido:
                salida = {"abierto": True, "repetido": True, "ruta": relativa,
                          "mensaje": f"Ya mandé a abrir {os.path.basename(real)} hace {ahora - previo:.0f} s: "
                                     "esperá que aparezca la ventana de Orca."}
                registrar(f"repetido: {relativa}")
                return salida, False
            if ahora - self.ultimo < self.intervalo:
                raise Rechazo(f"Acabo de abrir otro proyecto: esperá {self.intervalo:.0f} segundos entre uno y otro.")
            detalle = lanzar(comando, real, self.entorno)
            self.ultimo = ahora
            self.abiertos = {k: v for k, v in self.abiertos.items() if ahora - v < self.repetido}
            self.abiertos[real] = ahora
            nombre = os.path.basename(real)
            if detalle.get("sin_confirmar"):
                salida = {"abierto": False, "ruta": relativa,
                          "mensaje": f"Mandé a abrir {nombre}, pero Orca no quedó abierto: puede que ya estuviera "
                                     "abierto y lo haya tomado, o que haya fallado. Si no ves la ventana, abrí el .3mf "
                                     "con doble clic."}
            else:
                salida = {"abierto": True, "ruta": relativa,
                          "mensaje": f"Listo: se abre {nombre} en OrcaSlicer (puede tardar unos segundos). "
                                     "Imprimir sigue siendo tuyo."}
            registrar(f"abierto ({detalle.get('via')}): {relativa}")
            return salida, False
        except Rechazo as motivo:
            registrar(f"rechazado: {pedida!r}: {motivo}")
            return {"abierto": False, "mensaje": str(motivo)}, True


    def papelera(self, argumentos: dict) -> tuple[dict, bool]:
        """(structuredContent, isError). Solo después de que el usuario confirmó en el chat."""
        pedida = argumentos.get("carpeta")
        try:
            extra = sorted(set(argumentos) - {"carpeta"})
            if extra:
                raise Rechazo(f"Solo acepto `carpeta` (sobra: {', '.join(map(str, extra))}).")
            raiz = carpeta_de_trabajo(self.entorno)
            real = validar_pieza(pedida, raiz)
            relativa = os.path.relpath(real, raiz).replace(os.sep, "/")
            archivos, peso = contar(real)
            donde = a_la_papelera(real, self.entorno)
            if os.path.lexists(real):
                raise Rechazo("La carpeta sigue en su lugar: no se pudo mandar a la papelera. Borrala a mano.")
            registrar(f"a la papelera: {relativa} ({archivos} archivos, {peso} bytes) → {donde}")
            return {"borrado": True, "carpeta": relativa, "archivos": archivos, "bytes": peso, "papelera": donde,
                    "mensaje": f"Listo: mandé {relativa} a la papelera de tu PC ({archivos} archivos, {_peso(peso)}). "
                               "Si te arrepentís, la recuperás desde la papelera hasta que la vacíes."}, False
        except Rechazo as motivo:
            registrar(f"papelera rechazada: {pedida!r}: {motivo}")
            return {"borrado": False, "mensaje": str(motivo)}, True


def _error(ident, codigo: int, mensaje: str, datos=None) -> dict:
    e = {"code": codigo, "message": mensaje}
    if datos is not None:
        e["data"] = datos
    return {"jsonrpc": "2.0", "id": ident, "error": e}


def _resultado_herramienta(salida: dict, es_error: bool) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(salida, ensure_ascii=False)}],
            "structuredContent": salida, "isError": es_error}


def procesar(servidor: Servidor, m) -> dict | None:
    """Un mensaje JSON-RPC → la respuesta (o None para notificaciones y respuestas)."""
    if not isinstance(m, dict):
        return _error(None, -32600, "Invalid Request")
    if "method" not in m and ("result" in m or "error" in m):
        return None                                          # una respuesta del cliente: no se contesta
    ident = m.get("id")
    es_pedido = "id" in m
    if m.get("jsonrpc") != "2.0" or not isinstance(m.get("method"), str):
        return _error(ident if isinstance(ident, (str, int)) else None, -32600, "Invalid Request")
    if es_pedido and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
        return _error(None, -32600, "Invalid Request: id tiene que ser texto o número entero")
    if not es_pedido:
        return None                                          # notificaciones: initialized, cancelled, ...
    metodo, params = m["method"], m.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error(ident, -32602, "Invalid params")
    meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
    version = meta.get(META_VERSION)

    if metodo == "initialize":                               # época legada: el saludo fija la versión
        pedida = params.get("protocolVersion")
        servidor.legada = pedida if pedida in VERSIONES_LEGADAS else VERSIONES_LEGADAS[0]
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": servidor.legada, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": INFO, "instructions": INSTRUCCIONES}}
    if version is not None and not (servidor.legada and version in VERSIONES_LEGADAS):
        # época moderna: la versión viene en cada pedido
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
    except Exception as error:                               # nunca dejar un pedido sin respuesta
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
        if nombre not in (HERRAMIENTA["name"], PAPELERA["name"]):
            return _error(ident, -32602, f"Unknown tool: {nombre}")
        if argumentos is None:
            argumentos = {}
        if not isinstance(argumentos, dict):
            return _error(ident, -32602, "Invalid params: arguments tiene que ser un objeto")
        if nombre == PAPELERA["name"]:
            resultado = _resultado_herramienta(*servidor.papelera(argumentos))
        else:
            resultado = _resultado_herramienta(*servidor.abrir(argumentos))
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
    if isinstance(mensaje, list):                            # lotes (solo 2025-03-26)
        if not mensaje:
            return _error(None, -32600, "Invalid Request")
        respuestas = [r for r in (procesar(servidor, x) for x in mensaje) if r is not None]
        return respuestas or None
    return procesar(servidor, mensaje)


def main() -> None:
    servidor = Servidor()
    entrada, salida = sys.stdin.buffer, sys.stdout.buffer
    registrar(f"{VERSION} listo")
    while True:
        linea = entrada.readline()
        if not linea:                                        # la app cerró la entrada: terminar
            break
        if not linea.strip():
            continue
        try:
            respuesta = procesar_linea(servidor, linea)
        except Exception as error:                           # nunca dejar la conexión sin respuesta
            registrar(f"error interno: {type(error).__name__}: {error}")
            respuesta = _error(None, -32603, "Internal error")
        if respuesta is not None:
            salida.write(json.dumps(respuesta, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
            salida.flush()


if __name__ == "__main__":
    main()
