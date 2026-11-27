#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
# Instalador de taller-3d para Linux (x86_64; probado en Ubuntu 24.04).
#
# Primero revisa que la PC alcance (sistema, procesador, memoria, placa de video, disco e internet):
# si no alcanza, no cambia nada. Después revisa qué tenés instalado, saltea lo que ya está y hace
# solo lo que falta:
#   1. Muestra el aviso de uso y pide que escribas ACEPTO.
#   2. OrcaSlicer: usa el que ya tengas (AppImage, Flatpak, del sistema, portable o en un contenedor)
#      o descarga el 2.5.1 oficial (AppImage de GitHub) y verifica su huella SHA-256.
#   3. Crea un lanzador para que Claude use tus perfiles (y el acceso directo del menú si instala Orca).
#   4. Instala orca-mcp 0.1.0 (la conexión entre Claude y Orca) con uv o pipx.
#   5. Crea la carpeta de trabajo con su configuración inicial.
#   6. Te muestra cómo conectar orca-mcp en la app de Claude y, si querés, lo agrega (con respaldo).
#
# No usa sudo salvo que lo aceptes (solo para bibliotecas del sistema, xvfb o pipx). No borra nada:
# lo que reemplaza va a la papelera. Anota todo lo que instala en ~/.local/state/taller-3d/instalado.txt
# para que desinstalar.sh pueda quitarlo.
#
# Uso:
#   bash instalar.sh [--prueba] [--orca RUTA] [--datos-orca DIR] [--carpeta-apps DIR]
#                    [--carpeta-trabajo DIR] [--sin-app]
#     --prueba          muestra lo que haría, sin cambiar nada
#     --orca            un Orca que ya tengas: ejecutable, AppImage o el script que lo abre
#                       (portable o en un contenedor); saltea la búsqueda
#     --datos-orca      carpeta de datos de ese Orca (por defecto ~/.config/OrcaSlicer)
#     --carpeta-apps    dónde guardar el AppImage (por defecto ~/Aplicaciones o ~/Applications)
#     --carpeta-trabajo solo para probar el instalador: el taller guarda siempre en <Documentos>/Taller 3D
#     --sin-app         no tocar la configuración de la app de Claude
set -euo pipefail

VERSION_PLUGIN="0.1.41"
ORCA_VERSION="2.5.1"
ORCA_ARCHIVO="OrcaSlicer_Linux_AppImage_Ubuntu2404_V${ORCA_VERSION}.AppImage"
ORCA_URL="https://github.com/OrcaSlicer/OrcaSlicer/releases/download/v${ORCA_VERSION}/${ORCA_ARCHIVO}"
ORCA_SHA256="073b8105c928356141db0ddbce88b81d52c7a9e2442f9baae0a9089c89ff04eb"
ORCA_MCP_VERSION="0.1.0"
FLATPAK_IDS=(com.orcaslicer.OrcaSlicer io.github.softfever.OrcaSlicer)

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRUEBA=0
SIN_APP=0
CARPETA_APPS=""
CARPETA_TRABAJO=""
YA_CONFIGURADO=0
ORCA_OPCION=""
DATOS_OPCION=""

valor_de() {  # valor_de OPCION RESTO... -> el valor que sigue a la opción, o error claro
  [ $# -ge 2 ] && [ -n "$2" ] && [ "${2#--}" = "$2" ] || { echo "Falta la ruta después de $1." >&2; exit 2; }
  printf '%s' "$2"
}
while [ $# -gt 0 ]; do
  case "$1" in
    --orca|--datos-orca|--carpeta-apps|--carpeta-trabajo) V="$(valor_de "$@")" ;;
  esac
  case "$1" in
    --prueba) PRUEBA=1 ;;
    --sin-app) SIN_APP=1 ;;
    --orca) ORCA_OPCION="$V"; shift ;;
    --datos-orca) DATOS_OPCION="$V"; shift ;;
    --carpeta-apps) CARPETA_APPS="$V"; shift ;;
    --carpeta-trabajo) CARPETA_TRABAJO="$V"; shift ;;
    -h|--help) sed -n '4,30p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
  shift
done

ESTADO="$HOME/.local/state/taller-3d"
MANIFIESTO="$ESTADO/instalado.txt"
REGISTRO="$ESTADO/instalacion-$(date +%Y%m%d-%H%M%S).log"
if [ "$PRUEBA" -eq 0 ]; then
  mkdir -p "$ESTADO"
  exec > >(tee -a "$REGISTRO") 2>&1
fi

paso() { printf '\n== %s\n' "$*"; }
info() { printf '   %s\n' "$*"; }
fila() { if [ "$1" = ok ]; then printf '   [ok]    %s\n' "$2"; else printf '   [falta] %s\n' "$2"; fi; }
hacer() {  # ejecuta o, en modo prueba, solo muestra
  if [ "$PRUEBA" -eq 1 ]; then printf '   [prueba] %s\n' "$*"; else "$@"; fi
}
anotar() { [ "$PRUEBA" -eq 1 ] || printf '%s\t%s\n' "$1" "$2" >> "$MANIFIESTO"; }
# Si algo falla a mitad de camino, decir qué quedó y cómo deshacerlo (set -e corta en silencio)
trap 'echo; echo "Paré por un error (línea $LINENO). Lo que ya quedó hecho está anotado en $MANIFIESTO y se deshace con: bash desinstalar.sh" >&2' ERR
preguntar() {  # preguntar "texto" -> 0 si responde s/si (por defecto NO)
  local r
  if [ "$PRUEBA" -eq 1 ]; then printf '   [prueba] %s (s/N): se asume NO\n' "$1"; return 1; fi
  read -r -p "   $1 (s/N): " r
  case "${r,,}" in s|si|sí|y|yes) return 0 ;; *) return 1 ;; esac
}
preguntar_si() {  # como preguntar, pero por defecto SÍ
  local r
  if [ "$PRUEBA" -eq 1 ]; then printf '   [prueba] %s (S/n): se asume SÍ\n' "$1"; return 0; fi
  read -r -p "   $1 (S/n): " r
  case "${r,,}" in n|no) return 1 ;; *) return 0 ;; esac
}
sha_ok() { echo "$ORCA_SHA256  $1" | sha256sum -c --status 2>/dev/null; }
version_de_nombre() { basename "$1" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true; }
version_flatpak() { LC_ALL=C flatpak info "$1" 2>/dev/null | awk -F': *' '$1 ~ /^ *Version$/ {print $2; exit}' || true; }
# La app de Claude guarda su configuración con lo que tiene en memoria: si sigue abierta, pisa lo que se escriba.
app_de_claude_abierta() {
  pgrep -u "$(id -u)" -f '(^|/)(claude-desktop|Claude)( |$)' >/dev/null 2>&1 \
    || pgrep -u "$(id -u)" -x 'claude-desktop|Claude' >/dev/null 2>&1
}
# La última carpeta de trabajo que usó el instalador (la creada o una que ya existía).
carpeta_anotada() { awk -F'\t' '$1 == "carpeta" || $1 == "carpeta-usada" {c = $2} END {print c}' "$MANIFIESTO" 2>/dev/null || true; }

# --- 0. Comprobaciones e inventario -----------------------------------------------------------
paso "Revisando tu PC"
[ "$PRUEBA" -eq 0 ] || info "Modo prueba: no cambio nada, solo te muestro lo que haría."
[ "$(uname -s)" = "Linux" ] || { echo "Este instalador es para Linux. En Windows usá instalar-windows.bat; en macOS, INSTALACION.md."; exit 1; }
[ "$(uname -m)" = "x86_64" ] || { echo "Este instalador es para PCs x86_64."; exit 1; }
for c in python3 sha256sum; do command -v "$c" >/dev/null || { echo "Falta '$c'. Instalalo y volvé a correr."; exit 1; }; done
if command -v curl >/dev/null; then BAJAR=(curl -fL --retry 3 -o); elif command -v wget >/dev/null; then BAJAR=(wget -q --show-progress -O); else echo "Falta curl o wget."; exit 1; fi
if grep -qi microsoft /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME:-}" ]; then
  info "Estás en WSL (Linux adentro de Windows). Para Windows conviene el instalador nativo: instalar-windows.bat."
  info "Si seguís acá, Orca abre como ventana de Linux y la app de Claude de Windows no ve orca-mcp sin configurarlo a mano."
  if [ "$PRUEBA" -eq 0 ] && ! preguntar "¿Seguís igual en WSL?"; then exit 1; fi
fi
if pgrep -ix 'orca-slicer|orcaslicer' >/dev/null 2>&1; then
  if [ "$PRUEBA" -eq 1 ]; then info "OrcaSlicer está abierto: para instalar de verdad hay que cerrarlo."
  else echo "Cerrá OrcaSlicer antes de seguir."; exit 1; fi
fi
LDD_VERSION="$(ldd --version 2>/dev/null || true)"
GLIBC="$(head -1 <<<"$LDD_VERSION" | grep -oE '[0-9]+\.[0-9]+$' || true)"
[ -n "$GLIBC" ] || GLIBC=0
if python3 -c "import sys; sys.exit(0 if tuple(map(int,'$GLIBC'.split('.'))) >= (2,39) else 1)"; then ORCA_POR_APPIMAGE=1; else ORCA_POR_APPIMAGE=0; fi

if [ -z "$CARPETA_APPS" ]; then
  if [ -d "$HOME/Aplicaciones" ]; then CARPETA_APPS="$HOME/Aplicaciones"; else CARPETA_APPS="$HOME/Applications"; fi
fi
APP_OFICIAL="$CARPETA_APPS/$ORCA_ARCHIVO"
# Carpeta de trabajo: siempre "Taller 3D" dentro de la carpeta de documentos (desde la 0.1.34 no se pregunta
# ni se sigue usando la de una instalación anterior). Si antes se usó otra, se avisa en el paso 4 para mudarla.
CARPETA_ANTERIOR=""
if [ -z "$CARPETA_TRABAJO" ]; then
  DOCS="$(xdg-user-dir DOCUMENTS 2>/dev/null || true)"
  if [ -z "$DOCS" ] || [ "$DOCS" = "$HOME" ]; then
    if [ ! -d "$HOME/Documentos" ] && [ -d "$HOME/Documents" ]; then DOCS="$HOME/Documents"; else DOCS="$HOME/Documentos"; fi
  fi
  CARPETA_TRABAJO="$DOCS/Taller 3D"
  if [ -f "$MANIFIESTO" ]; then
    ANTERIOR="$(carpeta_anotada)"
    if [ -n "$ANTERIOR" ] && [ "$ANTERIOR" != "$CARPETA_TRABAJO" ] && [ -f "$ANTERIOR/taller-3d/config.json" ]; then
      CARPETA_ANTERIOR="$ANTERIOR"
    fi
  fi
fi
CONFIG="$CARPETA_TRABAJO/taller-3d/config.json"
LANZADOR="$HOME/.local/bin/orca-slicer-taller"
CONFIG_APP="$HOME/.config/Claude/claude_desktop_config.json"

# Orcas que ya hay: "tipo|ruta o id|versión|carpeta de datos"
CANDIDATOS=()
if [ -n "$ORCA_OPCION" ]; then
  [ -e "$ORCA_OPCION" ] || { echo "No existe $ORCA_OPCION."; exit 1; }
  [ -x "$ORCA_OPCION" ] || { echo "$ORCA_OPCION no es ejecutable (chmod +x)."; exit 1; }
  v="$(version_de_nombre "$ORCA_OPCION")"
  CANDIDATOS+=("indicado|$ORCA_OPCION|${v:-desconocida}|${DATOS_OPCION:-$HOME/.config/OrcaSlicer}")
else
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ "$f" = "$APP_OFICIAL" ] && sha_ok "$f"; then CANDIDATOS=("oficial|$f|$ORCA_VERSION|$HOME/.config/OrcaSlicer" "${CANDIDATOS[@]}")
    else v="$(version_de_nombre "$f")"; CANDIDATOS+=("appimage|$f|${v:-desconocida}|$HOME/.config/OrcaSlicer"); fi
  done < <(find "$HOME" -maxdepth 3 -type f -iname 'orcaslicer*.appimage' ! -path '*/Trash/*' ! -name '.*' 2>/dev/null | sort)
  if command -v flatpak >/dev/null 2>&1; then
    for id in "${FLATPAK_IDS[@]}"; do
      v="$(version_flatpak "$id")"
      [ -n "$v" ] && CANDIDATOS+=("flatpak|$id|$v|$HOME/.var/app/$id/config/OrcaSlicer")
    done
  fi
  for f in "$(command -v orca-slicer 2>/dev/null || true)" /usr/bin/orca-slicer /usr/local/bin/orca-slicer /opt/orcaslicer/bin/orca-slicer; do
    [ -n "$f" ] && [ -x "$f" ] && [ "$f" != "$LANZADOR" ] || continue
    repetido=0
    for c in "${CANDIDATOS[@]}"; do [ "$(cut -d'|' -f2 <<<"$c")" = "$f" ] && repetido=1; done
    [ "$repetido" -eq 1 ] || CANDIDATOS+=("sistema|$f|desconocida|$HOME/.config/OrcaSlicer")
  done
fi
ELEGIDO=""
for c in "${CANDIDATOS[@]}"; do case "$c" in oficial\|*|indicado\|*) ELEGIDO="$c"; break ;; esac; done
if [ -z "$ELEGIDO" ]; then for c in "${CANDIDATOS[@]}"; do [ "$(cut -d'|' -f3 <<<"$c")" = "$ORCA_VERSION" ] && { ELEGIDO="$c"; break; }; done; fi
if [ -z "$ELEGIDO" ] && [ ${#CANDIDATOS[@]} -gt 0 ]; then ELEGIDO="${CANDIDATOS[0]}"; fi

ORCA_MCP_YA="$(command -v orca-mcp 2>/dev/null || true)"
[ -n "$ORCA_MCP_YA" ] || { [ -x "$HOME/.local/bin/orca-mcp" ] && ORCA_MCP_YA="$HOME/.local/bin/orca-mcp"; } || true
APP_TIENE_MCP=0
[ -f "$CONFIG_APP" ] && python3 -c 'import json,sys; sys.exit(0 if "orca-mcp" in (json.load(open(sys.argv[1])).get("mcpServers") or {}) else 1)' "$CONFIG_APP" 2>/dev/null && APP_TIENE_MCP=1

if [ -n "$ELEGIDO" ]; then IFS='|' read -r t r v _ <<<"$ELEGIDO"; fila ok "OrcaSlicer $v ($t): $r"; else fila falta "OrcaSlicer"; fi
if [ -n "$ORCA_MCP_YA" ]; then fila ok "orca-mcp: $ORCA_MCP_YA"; else fila falta "orca-mcp $ORCA_MCP_VERSION"; fi
if command -v uv >/dev/null 2>&1; then fila ok "uv"; elif command -v pipx >/dev/null 2>&1; then fila ok "pipx"
else [ -n "$ORCA_MCP_YA" ] || fila falta "uv o pipx (para instalar orca-mcp)"; fi
if [ -f "$CONFIG" ]; then fila ok "Carpeta de trabajo y configuración: $CARPETA_TRABAJO"; else fila falta "Carpeta de trabajo: $CARPETA_TRABAJO"; fi
if [ -d "$HOME/.config/Claude" ]; then
  fila ok "App de escritorio de Claude"
  if [ "$APP_TIENE_MCP" -eq 1 ]; then fila ok "orca-mcp conectado en la app"; else fila falta "orca-mcp conectado en la app"; fi
else
  fila falta "App de escritorio de Claude (instalala desde https://claude.ai/download)"
fi
if command -v xvfb-run >/dev/null 2>&1; then fila ok "xvfb (opcional)"; else info "[opcional] xvfb no está: solo hace falta si Orca pide pantalla para laminar"; fi
if command -v blender >/dev/null 2>&1 || { command -v flatpak >/dev/null 2>&1 && flatpak info org.blender.Blender >/dev/null 2>&1; }; then
  info "[opcional] Blender instalado"
else
  info "[opcional] Blender no está: solo hace falta para formas orgánicas"
fi

# --- Requisitos: ¿la PC se banca lo que hay que instalar? (antes de cambiar nada) ---------------
paso "¿La PC alcanza?"
NO_ALCANZA=()
req() {  # req ok|aviso|no "texto"
  case "$1" in
    ok) printf '   [ok]         %s\n' "$2" ;;
    aviso) printf '   [aviso]      %s\n' "$2" ;;
    no) printf '   [no alcanza] %s\n' "$2"; NO_ALCANZA+=("$2") ;;
  esac
}
ELEGIDO_VERSION="$(cut -d'|' -f3 <<<"$ELEGIDO")"
HAY_QUE_BAJAR_ORCA=0
if [ -z "$ELEGIDO" ] || { [ "$ELEGIDO_VERSION" != "$ORCA_VERSION" ] && [ -z "$ORCA_OPCION" ]; }; then HAY_QUE_BAJAR_ORCA=1; fi
HAY_QUE_BAJAR=$HAY_QUE_BAJAR_ORCA
[ -n "$ORCA_MCP_YA" ] || HAY_QUE_BAJAR=1
# Sistema
SO="$( (. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME:-Linux}") || echo Linux)"
req ok "Sistema: $SO, $(uname -m), glibc $GLIBC"
if [ "$ORCA_POR_APPIMAGE" -eq 0 ]; then
  req aviso "glibc $GLIBC: el AppImage oficial pide Ubuntu 24.04 o equivalente. Se puede usar Orca de Flathub."
fi
# Procesador (Orca no pide un mínimo; con menos de 4 núcleos lamina más lento)
CPU_MODELO="$(awk -F': *' '/^model name/ {print $2; exit}' /proc/cpuinfo 2>/dev/null)"
CPU_NUCLEOS="$(nproc 2>/dev/null || echo 1)"
if [ "$CPU_NUCLEOS" -lt 2 ]; then req aviso "Procesador: ${CPU_MODELO:-desconocido}, $CPU_NUCLEOS núcleo. Va a laminar lento."
elif [ "$CPU_NUCLEOS" -lt 4 ]; then req aviso "Procesador: ${CPU_MODELO:-desconocido}, $CPU_NUCLEOS núcleos. Alcanza; las piezas grandes laminan más lento."
else req ok "Procesador: ${CPU_MODELO:-desconocido}, $CPU_NUCLEOS núcleos"; fi
# Memoria (OrcaSlicer pide 4 GB como mínimo y recomienda 8 GB o más)
MEM_KB="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
MEM_GB="$(awk -v k="${MEM_KB:-0}" 'BEGIN {printf "%.1f", k/1048576}')"
if [ "${MEM_KB:-0}" -lt 3670016 ]; then req no "Memoria: $MEM_GB GB. Orca pide 4 GB como mínimo."
elif [ "$MEM_KB" -lt 7864320 ]; then req aviso "Memoria: $MEM_GB GB. Alcanza; con piezas grandes conviene 8 GB o más."
else req ok "Memoria: $MEM_GB GB"; fi
# Disco libre (Orca ocupa unos 500 MB; orca-mcp y su Python, unos 200 MB)
DISCO_KB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')"
DISCO_GB="$(awk -v k="${DISCO_KB:-0}" 'BEGIN {printf "%.1f", k/1048576}')"
MIN_KB=307200; [ "$HAY_QUE_BAJAR_ORCA" -eq 1 ] && MIN_KB=1048576
if [ "${DISCO_KB:-0}" -lt "$MIN_KB" ]; then req no "Disco libre: $DISCO_GB GB. Hace falta por lo menos $((MIN_KB / 1048576 > 0 ? MIN_KB / 1048576 : 1)) GB."
elif [ "$DISCO_KB" -lt 2097152 ]; then req aviso "Disco libre: $DISCO_GB GB. Alcanza justo; las piezas y respaldos también ocupan."
else req ok "Disco libre: $DISCO_GB GB"; fi
# Placa de video (Orca pide OpenGL 3.3 para la ventana; Claude lamina igual sin ventana)
if command -v lspci >/dev/null 2>&1; then
  while IFS= read -r placa; do
    [ -n "$placa" ] && info "             Placa de video: $placa"
  done < <(lspci 2>/dev/null | grep -iE 'vga|3d controller|display controller' | cut -d: -f3- | sed 's/^ *//' | head -3)
fi
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  req aviso "Sin escritorio gráfico: Orca no va a poder abrir su ventana. Claude puede laminar igual (con xvfb)."
elif command -v glxinfo >/dev/null 2>&1; then
  GL_INFO="$(glxinfo -B 2>/dev/null || true)"
  # (|| true: con pipefail, un grep sin resultados cortaría el instalador entero)
  GL_VERSION="$(grep -E 'OpenGL (core profile )?version string' <<<"$GL_INFO" | grep -oE '[0-9]+\.[0-9]+' | sort -V | tail -1 || true)"
  GL_PLACA="$(grep -m1 'OpenGL renderer string' <<<"$GL_INFO" | cut -d: -f2- | sed 's/^ *//' || true)"
  if [ -z "$GL_VERSION" ]; then req aviso "No pude leer la versión de OpenGL. Orca pide 3.3."
  elif [ "$(printf '%s\n3.3\n' "$GL_VERSION" | sort -V | head -1)" != "3.3" ]; then
    req aviso "OpenGL $GL_VERSION ($GL_PLACA): Orca pide 3.3; la ventana puede no abrir. Claude lamina igual."
  elif grep -qi 'llvmpipe\|softpipe\|software' <<<"$GL_PLACA"; then
    req aviso "Gráficos por software ($GL_PLACA): Orca va a andar lento. Instalá el driver de la placa de video."
  else req ok "Gráficos: OpenGL $GL_VERSION ($GL_PLACA)"; fi
else
  info "[sin ver]    Gráficos: no pude verificar OpenGL (para verlo: sudo apt install mesa-utils). Orca pide 3.3."
fi
# FUSE para el AppImage (usa fusermount; sin él se abre extrayéndose cada vez, más lento)
NECESITA_FUSE=0
if [ "$ORCA_POR_APPIMAGE" -eq 1 ] && ! command -v fusermount3 >/dev/null 2>&1 && ! command -v fusermount >/dev/null 2>&1; then
  NECESITA_FUSE=1
  req aviso "Falta fusermount (paquete fuse3), que usa el AppImage de Orca. Te ofrezco instalarlo; si no, Orca se abre más lento."
fi
# Internet (solo si hay algo para bajar)
if [ "$HAY_QUE_BAJAR" -eq 1 ]; then
  if command -v curl >/dev/null; then PROBAR=(curl -sS -o /dev/null --max-time 15); else PROBAR=(wget -q --spider --timeout=15); fi
  if "${PROBAR[@]}" https://github.com 2>/dev/null && "${PROBAR[@]}" https://pypi.org/simple/orca-mcp/ 2>/dev/null; then
    req ok "Conexión a GitHub y PyPI (para bajar Orca y orca-mcp)"
  else
    req no "Sin conexión a github.com o pypi.org: hace falta para bajar Orca y orca-mcp."
  fi
fi
if [ ${#NO_ALCANZA[@]} -gt 0 ]; then
  echo
  echo "La PC no alcanza para instalar el taller. No cambié nada."
  printf '   - %s\n' "${NO_ALCANZA[@]}"
  echo "Si la corregís (por ejemplo, liberando disco o conectándote a internet), volvé a correr el instalador."
  exit 1
fi

# --- 1. Aviso de uso ---------------------------------------------------------------------------
paso "Aviso de uso"
AVISO=""
for f in "$AQUI/DISCLAIMER.md" "$AQUI/../DISCLAIMER.md"; do [ -f "$f" ] && { AVISO="$f"; break; }; done
if [ -n "$AVISO" ]; then sed -n '1,200p' "$AVISO"; else
  echo "Este software se ofrece tal cual, sin garantías. Lo usás bajo tu exclusiva cuenta y riesgo."
  echo "La impresión 3D implica calor, electricidad y vapores: no dejes la impresora sin supervisión."
fi
if [ "$PRUEBA" -eq 0 ]; then
  read -r -p "Para seguir, escribí ACEPTO: " RESPUESTA
  [ "$RESPUESTA" = "ACEPTO" ] || { echo "No se instaló nada."; exit 1; }
fi
ACEPTACION_FECHA="$(date -Iseconds)"

# --- 2. OrcaSlicer -----------------------------------------------------------------------------
paso "OrcaSlicer"
ORCA_TIPO=""; ORCA_RUTA=""; ORCA_VERSION_USADA=""; DATOS_ORCA=""
usar() { IFS='|' read -r ORCA_TIPO ORCA_RUTA ORCA_VERSION_USADA DATOS_ORCA <<<"$1"; }
if [ -n "$ELEGIDO" ]; then
  IFS='|' read -r t r v d <<<"$ELEGIDO"
  case "$t" in
    oficial|indicado) usar "$ELEGIDO"; info "Uso el que ya tenés: $r ($v)." ;;
    *)
      if [ "$v" = "$ORCA_VERSION" ]; then
        preguntar_si "Tenés OrcaSlicer $v ($t: $r). ¿Uso ese en lugar de bajar otro?" && usar "$ELEGIDO"
      else
        info "Tenés OrcaSlicer $v ($t: $r). El taller está probado con la $ORCA_VERSION."
        preguntar "¿Uso ese igual en lugar de bajar la $ORCA_VERSION oficial?" && usar "$ELEGIDO"
      fi ;;
  esac
else
  info "No encontré OrcaSlicer en los lugares de siempre."
  if preguntar "¿Tenés OrcaSlicer portable o en un contenedor (distrobox, toolbox, Docker)?"; then
    info "Claude le pasa a Orca rutas de tu PC (el modelo, los perfiles y la carpeta de salida). Si Orca está en"
    info "un contenedor, tiene que ver tu carpeta personal en la misma ruta: distrobox y toolbox lo hacen solos;"
    info "en Docker, montá \$HOME en \$HOME. Si no, conviene instalar el oficial al lado."
    read -r -p "   Ruta del ejecutable, el AppImage o el script que lo abre (Enter para instalar el oficial): " r
    r="${r/#\~/$HOME}"
    if [ -n "$r" ]; then
      if [ -x "$r" ] && [ -f "$r" ]; then
        read -r -p "   Carpeta de datos de ese Orca (Enter = ~/.config/OrcaSlicer): " d
        d="${d/#\~/$HOME}"
        v="$(version_de_nombre "$r")"
        usar "portable|$r|${v:-desconocida}|${d:-$HOME/.config/OrcaSlicer}"
      else
        info "No encuentro un ejecutable en $r: sigo con el oficial."
      fi
    fi
  fi
fi

APP=""
if [ -z "$ORCA_TIPO" ]; then
  if [ "$ORCA_POR_APPIMAGE" -eq 0 ]; then
    info "Tu sistema es más viejo que Ubuntu 24.04 (glibc $GLIBC): el AppImage oficial no va a andar."
    info "Instalá Orca desde Flathub (flatpak install flathub com.orcaslicer.OrcaSlicer) y volvé a correr: lo encuentro solo."
  else
    APP="$APP_OFICIAL"
    FALTAN=()
    # Se lee una sola vez: con "ldconfig -p | grep -q" y pipefail, el grep corta el pipe y da falso faltante
    LIBS_SISTEMA="$(ldconfig -p 2>/dev/null || /sbin/ldconfig -p 2>/dev/null || true)"
    for lib in libOpenGL.so.0 libwebkit2gtk-4.1.so.0 libjavascriptcoregtk-4.1.so.0; do
      grep -qF "$lib" <<<"$LIBS_SISTEMA" || FALTAN+=("$lib")
    done
    if [ ${#FALTAN[@]} -gt 0 ]; then
      info "Faltan bibliotecas del sistema que Orca necesita: ${FALTAN[*]}"
      if command -v apt-get >/dev/null && preguntar "¿Las instalo con 'sudo apt install libopengl0 libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0'? (pide tu contraseña)"; then
        sudo apt-get install -y libopengl0 libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0 \
          && for pq in libopengl0 libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0; do anotar apt "$pq"; done
      else
        info "Instalalas antes de abrir Orca (en otras distribuciones: libglvnd/OpenGL y WebKitGTK 4.1)."
      fi
    fi
    if [ "$NECESITA_FUSE" -eq 1 ]; then
      if command -v apt-get >/dev/null && preguntar "¿Instalo fuse3 con 'sudo apt install fuse3'? (pide tu contraseña)"; then
        sudo apt-get install -y fuse3 && NECESITA_FUSE=0 && anotar apt fuse3
      else
        info "Sin fuse3, Orca se va a abrir extrayéndose cada vez (tarda unos segundos más)."
      fi
    fi
    hacer mkdir -p "$CARPETA_APPS"
    TEMPORAL="$CARPETA_APPS/.$ORCA_ARCHIVO.descarga"
    info "Descargando OrcaSlicer $ORCA_VERSION (~190 MB) desde $ORCA_URL"
    hacer "${BAJAR[@]}" "$TEMPORAL" "$ORCA_URL"
    if [ "$PRUEBA" -eq 0 ]; then
      if ! sha_ok "$TEMPORAL"; then
        gio trash "$TEMPORAL" 2>/dev/null || true
        echo "La huella SHA-256 no coincide: descarté el archivo. No se instaló Orca."; exit 1
      fi
      info "Huella SHA-256 verificada."
    fi
    hacer chmod +x "$TEMPORAL"
    hacer mv "$TEMPORAL" "$APP"
    anotar archivo "$APP"
    usar "oficial|$APP|$ORCA_VERSION|$HOME/.config/OrcaSlicer"
    # Otros AppImages de Orca: ofrecer mandarlos a la papelera
    for c in "${CANDIDATOS[@]}"; do
      IFS='|' read -r t r _ _ <<<"$c"
      [ "$t" = appimage ] && [ "$r" != "$APP" ] || continue
      if preguntar "Encontré otra versión: $r. ¿La mando a la papelera?"; then gio trash "$r" && info "A la papelera: $r"; fi
    done

    paso "Acceso directo del menú"
    ICONOS="$HOME/.local/share/icons"
    ICONO="$ICONOS/taller3d-orcaslicer.png"
    if [ "$PRUEBA" -eq 0 ]; then
      TMPX="$(mktemp -d)"
      ( cd "$TMPX" && "$APP" --appimage-extract .DirIcon >/dev/null 2>&1 || true
        if [ -L squashfs-root/.DirIcon ]; then "$APP" --appimage-extract "$(readlink squashfs-root/.DirIcon)" >/dev/null 2>&1 || true; fi )
      if [ -e "$TMPX/squashfs-root/.DirIcon" ]; then
        mkdir -p "$ICONOS"; cp -L "$TMPX/squashfs-root/.DirIcon" "$ICONO"; anotar archivo "$ICONO"
      else
        ICONO="applications-engineering"
      fi
      gio trash "$TMPX" 2>/dev/null || true
    fi
    ESCRITORIO="$HOME/.local/share/applications/taller3d-orcaslicer.desktop"
    if [ "$PRUEBA" -eq 0 ]; then
      mkdir -p "$(dirname "$ESCRITORIO")"
      cat > "$ESCRITORIO" <<EOF_DESKTOP
[Desktop Entry]
Type=Application
Name=OrcaSlicer
Comment=Laminador para impresión 3D (instalado por taller-3d)
Exec=$([ "$NECESITA_FUSE" -eq 1 ] && printf 'env APPIMAGE_EXTRACT_AND_RUN=1 ')"$APP" %F
Icon=$ICONO
Terminal=false
Categories=Graphics;3DGraphics;Engineering;
MimeType=model/stl;model/3mf;application/vnd.ms-3mfdocument;
StartupWMClass=orca-slicer
EOF_DESKTOP
      anotar archivo "$ESCRITORIO"
      update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
    fi
    info "Acceso directo: $ESCRITORIO"
  fi
fi

# Lanzador para orca-mcp: abre el Orca elegido con su carpeta de datos, así la línea de comandos
# encuentra tus perfiles y los de sistema.
ORCA_PARA_MCP=""
if [ -n "$ORCA_TIPO" ]; then
  paso "Lanzador para Claude"
  case "$ORCA_TIPO" in
    flatpak) COMANDO="$(printf 'exec flatpak run %q --datadir %q "$@"' "$ORCA_RUTA" "$DATOS_ORCA")" ;;
    *)       COMANDO="$(printf 'exec %q --datadir %q "$@"' "$ORCA_RUTA" "$DATOS_ORCA")" ;;
  esac
  # AppImage sin fusermount: que se extraiga y corra (más lento, pero anda)
  if [ "$NECESITA_FUSE" -eq 1 ] && [[ "${ORCA_RUTA,,}" == *.appimage ]]; then
    COMANDO="APPIMAGE_EXTRACT_AND_RUN=1 $COMANDO"
  fi
  if [ "$PRUEBA" -eq 1 ]; then
    info "[prueba] crearía $LANZADOR con: $COMANDO"
  else
    if [ -f "$LANZADOR" ] && ! grep -qF "$COMANDO" "$LANZADOR"; then
      cp "$LANZADOR" "$LANZADOR.respaldo-$(date +%Y%m%d-%H%M%S)"
    fi
    mkdir -p "$(dirname "$LANZADOR")"
    printf '#!/usr/bin/env bash\n# Lanzador de OrcaSlicer para orca-mcp (taller-3d): usa tu carpeta de datos de Orca.\n%s\n' "$COMANDO" > "$LANZADOR"
    chmod +x "$LANZADOR"
    grep -qxF "$(printf 'archivo\t%s' "$LANZADOR")" "$MANIFIESTO" 2>/dev/null || anotar archivo "$LANZADOR"
  fi
  info "Lanzador: $LANZADOR (Orca $ORCA_TIPO, datos en $DATOS_ORCA)"
  ORCA_PARA_MCP="$LANZADOR"
fi

# --- 3. orca-mcp -------------------------------------------------------------------------------
paso "orca-mcp $ORCA_MCP_VERSION (conexión Claude ↔ Orca)"
if [ -n "$ORCA_MCP_YA" ]; then
  info "Ya está instalado: $ORCA_MCP_YA"
elif command -v uv >/dev/null 2>&1; then
  hacer uv tool install "orca-mcp==$ORCA_MCP_VERSION"
  anotar uv orca-mcp
elif command -v pipx >/dev/null 2>&1; then
  hacer pipx install "orca-mcp==$ORCA_MCP_VERSION"
  anotar pipx orca-mcp
else
  info "Necesito pipx para instalarlo aislado del sistema."
  if preguntar "¿Instalo pipx con 'sudo apt install pipx'? (pide tu contraseña)"; then
    sudo apt-get install -y pipx && anotar apt pipx
    pipx install "orca-mcp==$ORCA_MCP_VERSION"
    anotar pipx orca-mcp
  else
    info "Instalalo después con: pipx install orca-mcp==$ORCA_MCP_VERSION"
  fi
fi
ORCA_MCP_BIN="${ORCA_MCP_YA:-$(command -v orca-mcp 2>/dev/null || echo "$HOME/.local/bin/orca-mcp")}"

if ! command -v xvfb-run >/dev/null 2>&1; then
  info "xvfb (opcional) permite laminar sin ventana si Orca lo pide."
  if preguntar "¿Instalo xvfb con 'sudo apt install xvfb'?"; then sudo apt-get install -y xvfb && anotar apt xvfb; fi
fi

# --- 4. Carpeta de trabajo ---------------------------------------------------------------------
paso "Carpeta de trabajo"
info "Tus piezas (con sus vistas y G-code), los respaldos y la configuración se guardan siempre en:"
info "  $CARPETA_TRABAJO"
if [ -n "$CARPETA_ANTERIOR" ]; then
  info "Antes usabas $CARPETA_ANTERIOR. No la toco:"
  info "  pedile a Claude que mude tus piezas a la carpeta nueva (/taller-3d:instalar)."
fi
for d in impresiones disenos respaldos calibraciones "taller-3d/impresoras"; do
  [ -d "$CARPETA_TRABAJO/$d" ] || hacer mkdir -p "$CARPETA_TRABAJO/$d"
done
if [ -f "$CONFIG" ]; then
  YA_CONFIGURADO=1
  info "Ya existe la configuración: $CONFIG (solo le anoto tu ACEPTO si no estaba)."
  # Queda anotada para que el desinstalador la conserve.
  [ "$(carpeta_anotada)" = "$CARPETA_TRABAJO" ] || anotar carpeta-usada "$CARPETA_TRABAJO"
  if [ "$PRUEBA" -eq 0 ]; then
    ACEPTACION_FECHA="$ACEPTACION_FECHA" VERSION_PLUGIN="$VERSION_PLUGIN" \
    RESPALDO="$CARPETA_TRABAJO/respaldos/$(date +%Y-%m-%d_%H%M%S)/taller-3d" python3 - "$CONFIG" <<'EOF_PY' \
      || info "No pude anotar tu ACEPTO en $CONFIG: Claude te lo pide la primera vez."
import json, os, shutil, sys
ruta, e = sys.argv[1], os.environ
with open(ruta, encoding="utf-8") as f:
    config = json.load(f)
if isinstance(config, dict) and not config.get("aceptacion"):
    os.makedirs(e["RESPALDO"], exist_ok=True)
    shutil.copy2(ruta, os.path.join(e["RESPALDO"], "config.json"))
    config["aceptacion"] = {"fecha": e["ACEPTACION_FECHA"], "version_plugin": e["VERSION_PLUGIN"],
                            "texto": "ACEPTO", "medio": "instalar.sh"}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("   Anoté tu ACEPTO en la configuración (la copia de antes quedó en respaldos/).")
EOF_PY
  fi
elif [ "$PRUEBA" -eq 0 ]; then
  CARPETA_TRABAJO="$CARPETA_TRABAJO" ACEPTACION_FECHA="$ACEPTACION_FECHA" VERSION_PLUGIN="$VERSION_PLUGIN" \
  ORCA_VERSION_USADA="${ORCA_VERSION_USADA:-}" ORCA_RUTA="${ORCA_RUTA:-}" ORCA_TIPO="${ORCA_TIPO:-}" \
  DATOS_ORCA="${DATOS_ORCA:-$HOME/.config/OrcaSlicer}" python3 - "$CONFIG" <<'EOF_PY'
import json, os, sys
e = os.environ
config = {
    "version": 1,
    "carpeta_trabajo": e["CARPETA_TRABAJO"],
    "aceptacion": {"fecha": e["ACEPTACION_FECHA"], "version_plugin": e["VERSION_PLUGIN"],
                   "texto": "ACEPTO", "medio": "instalar.sh"},
    "orca": {"version": e["ORCA_VERSION_USADA"] or None, "ejecutable": e["ORCA_RUTA"] or None,
             "origen": e["ORCA_TIPO"] or None,
             "carpeta_usuario": os.path.join(e["DATOS_ORCA"], "user", "default")},
    "impresora_por_defecto": None,
    "impresoras": [],
    "costos": {"moneda": "ARS", "precio_kwh": None, "consumo_w": 180, "filamentos": {}},
    "tienda": {"plataforma": None, "url": None, "margen_pct": None, "costo_hora_maquina": None,
               "embalaje": None, "redondeo": 100, "demora_dias": None, "peso_embalaje_g": 50,
               "categoria_por_defecto": None},
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
EOF_PY
  printf 'fecha;accion;pieza_o_perfil;archivo;resultado\n%s;instalacion;-;-;ok\n' "$(date -Iseconds)" \
    > "$CARPETA_TRABAJO/taller-3d/historial.csv"
  anotar carpeta "$CARPETA_TRABAJO"
else
  info "[prueba] crearía $CONFIG e historial.csv"
fi
info "Carpeta: $CARPETA_TRABAJO"

# Orca de Flatpak: necesita permiso para leer y escribir en la carpeta de trabajo
if [ "$ORCA_TIPO" = flatpak ]; then
  PERMISOS="$( { flatpak info --show-permissions "$ORCA_RUTA"; flatpak override --user --show "$ORCA_RUTA"; } 2>/dev/null \
    | grep -i '^filesystems=' || true)"
  if grep -qE '(^|[=;])(home|host)(:rw)?(;|$)' <<<"$PERMISOS" || grep -qF "$CARPETA_TRABAJO" <<<"$PERMISOS"; then
    info "El Orca de Flatpak ya puede usar la carpeta de trabajo."
  else
    info "El Orca de Flatpak no tiene permiso para la carpeta de trabajo, y lo necesita para laminar."
    if preguntar "¿Le doy acceso solo a '$CARPETA_TRABAJO' (flatpak override --user)?"; then
      flatpak override --user --filesystem="$CARPETA_TRABAJO" "$ORCA_RUTA"
      anotar flatpak-permiso "$ORCA_RUTA|$CARPETA_TRABAJO"
    else
      info "Hacelo después con: flatpak override --user --filesystem=\"$CARPETA_TRABAJO\" $ORCA_RUTA"
    fi
  fi
fi

# --- 4b. Abrir Orca desde Claude y desde el panel ------------------------------------------------
# abrir_orca.py: servidor MCP chico (solo Python, sin dependencias) con una herramienta, abrir_en_orca, que abre en
# la ventana de Orca un .3mf de la carpeta de trabajo. No lamina, no imprime, no escribe archivos.
paso "Abrir Orca desde Claude y desde el panel"
SERVIDOR_ORCA=""
ORCA_VENTANA="$ORCA_PARA_MCP"
if [ -z "$ORCA_VENTANA" ] && [ "$APP_TIENE_MCP" -eq 1 ]; then          # el mismo Orca que ya usa tu orca-mcp
  ORCA_VENTANA="$(python3 -c 'import json,sys; s=(json.load(open(sys.argv[1])).get("mcpServers") or {}).get("orca-mcp") or {}; print((s.get("env") or {}).get("ORCASLICER_PATH", ""))' "$CONFIG_APP" 2>/dev/null || true)"
fi
if [ ! -f "$AQUI/abrir_orca.py" ]; then
  info "No está abrir_orca.py al lado del instalador: salteo este paso."
elif [ -z "$ORCA_VENTANA" ] || { [ ! -x "$ORCA_VENTANA" ] && ! { [ "$PRUEBA" -eq 1 ] && [ "$ORCA_VENTANA" = "$LANZADOR" ]; }; }; then
  info "No encontré el programa de Orca para abrir su ventana: salteo este paso."
else
  info "Deja que Claude y los botones del panel te abran Orca con el proyecto .3mf de una pieza."
  info "Solo abre la ventana (no lamina, no imprime, no manda nada a la impresora) y solo proyectos de"
  info "$CARPETA_TRABAJO. Lo hace abrir_orca.py, un programa chico de Python que arranca la app de Claude."
  if preguntar_si "¿Lo instalo?"; then
    SERVIDOR_ORCA="$HOME/.local/share/taller-3d/abrir_orca.py"
    hacer mkdir -p "$(dirname "$SERVIDOR_ORCA")"
    hacer install -m 0644 "$AQUI/abrir_orca.py" "$SERVIDOR_ORCA"
    grep -qxF "$(printf 'archivo\t%s' "$SERVIDOR_ORCA")" "$MANIFIESTO" 2>/dev/null || anotar archivo "$SERVIDOR_ORCA"
  fi
fi

# --- 4c. Cargar productos en la tienda ------------------------------------------------------------
paso "Cargar productos en tu tienda (opcional)"
SERVIDOR_TIENDA=""
CRED_TIENDA="${XDG_CONFIG_HOME:-$HOME/.config}/taller-3d/credenciales-tienda.json"
if [ ! -f "$AQUI/tienda_mcp.py" ]; then
  info "No está tienda_mcp.py al lado del instalador: salteo este paso."
else
  info "Si vendés en una tienda WooCommerce (WordPress), Claude y el botón «Cargala como borrador» del panel"
  info "cargan ahí el producto con sus fotos, siempre como borrador (publicarlo es tuyo). Lo hace tienda_mcp.py,"
  info "un programa chico de Python que arranca la app de Claude. La contraseña la escribís acá, no en el chat."
  info "Qué necesita tu tienda y cómo crear la contraseña: TIENDA-WOOCOMMERCE.md (junto a INSTALACION.md)."
  if preguntar "¿Lo instalo?"; then
    SERVIDOR_TIENDA="$HOME/.local/share/taller-3d/tienda_mcp.py"
    hacer mkdir -p "$(dirname "$SERVIDOR_TIENDA")"
    hacer install -m 0644 "$AQUI/tienda_mcp.py" "$SERVIDOR_TIENDA"
    grep -qxF "$(printf 'archivo\t%s' "$SERVIDOR_TIENDA")" "$MANIFIESTO" 2>/dev/null || anotar archivo "$SERVIDOR_TIENDA"
    CONECTAR=1
    if [ -f "$CRED_TIENDA" ]; then
      info "Tu tienda ya estaba conectada."
      preguntar "¿La conecto de nuevo (otra contraseña u otra tienda)?" || CONECTAR=0
    fi
    if [ "$CONECTAR" -eq 1 ]; then
      info "Antes, en tu WordPress: Usuarios → Perfil → Contraseñas de aplicación, nombre «Taller 3D» → Añadir."
      info "WordPress la muestra una sola vez: copiala y pegala cuando te la pida."
      if [ "$PRUEBA" -eq 1 ]; then
        info "[prueba] te pediría la dirección de la tienda, tu usuario y la contraseña de aplicación"
      elif ! python3 -I "$SERVIDOR_TIENDA" configurar; then
        info "La tienda no quedó conectada. Cuando quieras: python3 \"$SERVIDOR_TIENDA\" configurar"
      fi
    fi
    if [ -f "$CRED_TIENDA" ] && ! grep -qxF "$(printf 'credenciales-tienda\t%s' "$CRED_TIENDA")" "$MANIFIESTO" 2>/dev/null; then
      anotar credenciales-tienda "$CRED_TIENDA"
    fi
  fi
fi

# --- 5. App de Claude ----------------------------------------------------------------------------
paso "Conexión con la app de Claude"
TEMPORAL_MCP=""
if [ "${ORCA_TIPO:-}" = "flatpak" ]; then
  # El Flatpak tiene su propio /tmp: orca-mcp deja ahí lo que lamina y Orca no lo ve.
  TEMPORAL_MCP="$CARPETA_TRABAJO/taller-3d/tmp"
  hacer mkdir -p "$TEMPORAL_MCP"
fi
ENTRADA="$(ORCA_MCP_BIN="$ORCA_MCP_BIN" ORCA_PARA_MCP="$ORCA_PARA_MCP" DATOS_ORCA="${DATOS_ORCA:-}" \
  TEMPORAL_MCP="$TEMPORAL_MCP" SERVIDOR_ORCA="$SERVIDOR_ORCA" ORCA_VENTANA="$ORCA_VENTANA" \
  SERVIDOR_TIENDA="$SERVIDOR_TIENDA" \
  CARPETA_TRABAJO="$CARPETA_TRABAJO" PYTHON="$(command -v python3)" python3 -c '
import json, os
e = {"command": os.environ["ORCA_MCP_BIN"]}
env = {}
if os.environ.get("ORCA_PARA_MCP"):
    env["ORCASLICER_PATH"] = os.environ["ORCA_PARA_MCP"]
if os.environ.get("DATOS_ORCA"):
    env["ORCASLICER_CONFIG_DIR"] = os.environ["DATOS_ORCA"]
if os.environ.get("TEMPORAL_MCP"):
    env["TMPDIR"] = os.environ["TEMPORAL_MCP"]
if env:
    e["env"] = env
servidores = {"orca-mcp": e}
if os.environ.get("SERVIDOR_ORCA"):
    servidores["taller3d-orca"] = {
        "command": os.environ["PYTHON"], "args": ["-I", os.environ["SERVIDOR_ORCA"]],
        "env": {"TALLER3D_CARPETA": os.environ["CARPETA_TRABAJO"],
                "TALLER3D_ORCA": json.dumps([os.environ["ORCA_VENTANA"]], ensure_ascii=False)}}
if os.environ.get("SERVIDOR_TIENDA"):
    servidores["taller3d-tienda"] = {
        "command": os.environ["PYTHON"], "args": ["-I", os.environ["SERVIDOR_TIENDA"]],
        "env": {"TALLER3D_CARPETA": os.environ["CARPETA_TRABAJO"]}}
print(json.dumps({"mcpServers": servidores}, indent=2, ensure_ascii=False))')"
info "Estas son las entradas para la app de Claude (Configuración → Desarrollador → Editar configuración):"
echo "$ENTRADA"
if [ "$SIN_APP" -eq 0 ] && [ -d "$HOME/.config/Claude" ]; then
  if [ "$APP_TIENE_MCP" -eq 1 ] && [ -z "$SERVIDOR_ORCA" ] && [ -z "$SERVIDOR_TIENDA" ]; then
    info "La app ya tiene un orca-mcp configurado: no lo cambio."
  elif preguntar "¿Las agrego yo a $CONFIG_APP? (hago una copia de respaldo antes; un orca-mcp que ya tengas no lo toco)"; then
    while app_de_claude_abierta; do
      info "La app de Claude está abierta: al cerrarse volvería a dejar su configuración como estaba."
      read -r -p "   Cerrala del todo (Salir desde el ícono de la bandeja; cerrar la ventana no alcanza) y apretá Enter, o escribí SALTEAR: " r
      [ "$r" = "SALTEAR" ] && break
    done
    if app_de_claude_abierta; then
      info "La app sigue abierta: no toqué su configuración. Copiá las entradas de arriba con la app cerrada,"
      info "o cerrala del todo y corré de nuevo este instalador."
    else
    [ -f "$CONFIG_APP" ] && cp "$CONFIG_APP" "$CONFIG_APP.respaldo-$(date +%Y%m%d-%H%M%S)"
    if AGREGADAS="$(ENTRADA="$ENTRADA" python3 - "$CONFIG_APP" <<'EOF_PY'
import json, os, sys
ruta = sys.argv[1]
try:
    with open(ruta, encoding="utf-8") as f:
        actual = json.load(f)
except FileNotFoundError:
    actual = {}
nuevo = json.loads(os.environ["ENTRADA"])
if not isinstance(actual, dict):
    sys.exit("La configuración de la app no tiene el formato esperado: agregá la entrada a mano.")
if not isinstance(actual.get("mcpServers"), dict):
    actual["mcpServers"] = {}
agregadas = []
for nombre, entrada in nuevo["mcpServers"].items():
    if nombre == "orca-mcp" and nombre in actual["mcpServers"]:
        continue                                   # el orca-mcp que ya tenías no se toca
    actual["mcpServers"][nombre] = entrada
    agregadas.append(nombre)
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(actual, f, ensure_ascii=False, indent=2)
print("\n".join(agregadas))
EOF_PY
)"; then
      if grep -qx orca-mcp <<<"$AGREGADAS"; then anotar mcp-app "$CONFIG_APP"; fi
      if grep -qx taller3d-orca <<<"$AGREGADAS" && ! grep -qxF "$(printf 'mcp-app-orca\t%s' "$CONFIG_APP")" "$MANIFIESTO" 2>/dev/null; then
        anotar mcp-app-orca "$CONFIG_APP"
      fi
      if grep -qx taller3d-tienda <<<"$AGREGADAS" && ! grep -qxF "$(printf 'mcp-app-tienda\t%s' "$CONFIG_APP")" "$MANIFIESTO" 2>/dev/null; then
        anotar mcp-app-tienda "$CONFIG_APP"
      fi
      info "Listo. Abrí la app de Claude para que tome el cambio."
    else
      info "No pude agregarlas: copiá las entradas de arriba a mano (tu configuración quedó como estaba)."
    fi
    fi
  fi
fi

# --- 6. Resumen -------------------------------------------------------------------------------------
paso "Listo"
info "Orca: ${ORCA_RUTA:-sin instalar (ver arriba)}"
info "Datos de Orca: ${DATOS_ORCA:-$HOME/.config/OrcaSlicer}"
info "orca-mcp: $ORCA_MCP_BIN"
info "Carpeta de trabajo: $CARPETA_TRABAJO"
[ "$PRUEBA" -eq 1 ] || info "Registro de la instalación: $REGISTRO"
DATOS_MOSTRAR="${DATOS_ORCA:-$HOME/.config/OrcaSlicer}"
if [ "$YA_CONFIGURADO" -eq 1 ]; then
  cat <<EOF_ACTUALIZAR

Próximos pasos (ya tenías el taller: esto fue una actualización):
  1. Si cambió la configuración de la app, cerrala del todo (también desde la bandeja) y volvé a abrirla.
  2. En Claude escribí: /taller-3d:instalar
     Claude revisa que todo ande y te dice qué quedó nuevo.
  El taller guarda siempre en la carpeta de trabajo de arriba. Si tenías piezas en otra,
  pedile a Claude que las mude: /taller-3d:instalar
EOF_ACTUALIZAR
  exit 0
fi
cat <<EOF_FIN

Próximos pasos:
  1. Abrí OrcaSlicer una vez y agregá tu impresora (asistente de Orca). Guardá una copia de usuario
     del perfil de la impresora, por ejemplo "Mi <modelo> 0.4 nozzle", y un perfil propio de proceso
     y de filamento: así Orca crea las carpetas de perfiles.
  2. En la app de Claude, conectá estas carpetas (menú + → Agregar carpeta):
     - $CARPETA_TRABAJO
     - $DATOS_MOSTRAR/user/default (tus perfiles de Orca: process, filament y machine)
  3. Instalá el plugin taller-3d en Claude (si no lo hiciste) y escribí: /taller-3d:instalar
     Claude revisa que todo ande, te pregunta en qué impresora trabajar y hace una pieza de prueba.
EOF_FIN
