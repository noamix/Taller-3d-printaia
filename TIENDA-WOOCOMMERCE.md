# Conectar tu tienda WordPress (WooCommerce)

Con este conector, Claude carga en tu tienda WooCommerce el producto que arma `/taller-3d:publicar`: título, precio, descripción, medidas, peso, etiquetas y fotos. Lo deja **siempre como borrador**: lo revisás y lo publicás vos desde WordPress. Lo usa también el botón **«Cargala como borrador»** del panel del taller, que lo carga directo, sin pasar por el chat.

Lo hace `tienda_mcp.py`, un programa chico de Python (sin dependencias) que arranca la app de escritorio de Claude en tu PC. Se instala y se conecta **una sola vez**.

## Qué hace y qué no

- Crea el producto como borrador, o actualiza el borrador que ya existe (lo reconoce por su SKU): no lo duplica.
- Sube las fotos (hasta 10) a la biblioteca de medios. Las que ya subió no las vuelve a subir.
- Pone el producto en las categorías de tu tienda que le corresponden: Claude las elige entre las que ya tenés. Si ninguna encaja, te propone una nueva y la crea solo si le decís que sí. Las etiquetas que falten las crea.
- Mira, sin cambiar nada, si los productos del panel siguen en borrador o ya los publicaste (o los mandaste a la papelera): así el panel se pone al día solo cada vez que trabajás con Claude.
- **Nunca publica**, no borra nada y no toca pedidos, clientes ni otros productos. Si el producto ya está publicado, no lo cambia (salvo la categoría, si le decís que sí: y entonces solo eso).
- Habla solo con tu tienda, por https, y no sigue redirecciones: así tu contraseña no viaja a otro sitio.
- No sube el modelo 3D ni el G-code.

## Qué necesitás

- Una tienda WordPress con **WooCommerce** activo y dirección **https://**. Da igual dónde esté alojada.
- **Enlaces permanentes** que no sean «Simple» (**Ajustes → Enlaces permanentes**).
- Las **contraseñas de aplicación** habilitadas. Vienen así en WordPress desde la versión 5.6, pero algunos plugins de seguridad las apagan (ver [Problemas comunes](#problemas-comunes)).
- Un usuario de WordPress con rol **Administrador** o **Gestor de la tienda**.
- La app de escritorio de Claude con el taller instalado ([INSTALACION.md](INSTALACION.md)).
- Linux o Windows, con el instalador del taller. En macOS se instala a mano (abajo). **El paso de Windows todavía no se probó en una PC real.**

No hace falta crear claves de la API de WooCommerce (*consumer key*): alcanza con la contraseña de aplicación.

## 1. Revisá tu tienda (sin contraseña)

Antes de pedirte nada, el instalador revisa lo que tu tienda le muestra a cualquiera: que responda en https sin redirecciones, que tenga WooCommerce y las contraseñas de aplicación habilitadas. Si falta algo, te dice qué y no te pide la contraseña.

También podés pedírselo a Claude antes de instalar: «revisá si mi tienda sirve para el conector del taller». O correrlo vos, en la carpeta del instalador:

```bash
python3 tienda_mcp.py revisar
```

Cada punto sale con `[ok]`, `[falta]` (hay que arreglarlo antes de conectar) o `[aviso]` (se puede seguir).

## 2. Creá la contraseña de aplicación

1. Entrá al administrador de tu WordPress (`https://tutienda.com/wp-admin`) con tu usuario.
2. Andá a **Usuarios → Perfil**.
3. Bajá hasta **Contraseñas de aplicación**.
4. En **Nombre de la nueva contraseña de aplicación** escribí `Taller 3D` y tocá **Añadir nueva contraseña de aplicación**.
5. Copiala: WordPress la muestra **una sola vez**. Son 24 letras y números en grupos de 4; los espacios dan igual.

No es tu contraseña de WordPress: sirve solo para que el taller cargue productos, no sirve para entrar al administrador y la podés revocar cuando quieras sin cambiar tu contraseña. **No la pegues en el chat:** va solo en la terminal (paso 3). Si se te escapó en el chat, revocala y creá otra.

## 3. Instalá el conector

### Linux

1. Conseguí el instalador (en Claude: `/taller-3d:instalar`, o [INSTALACION.md](INSTALACION.md), sección A) y, en una terminal, corré `bash instalar.sh`. Si el taller ya estaba instalado, saltea lo que ya está.
2. En **«Cargar productos en tu tienda (opcional)»** contestá `s`.
3. Escribí la dirección de tu tienda (por ejemplo `mitienda.com.ar`): primero la revisa. Si redirige a otra dirección (con o sin www), te ofrece usar esa.
4. Escribí tu usuario de WordPress y pegá la contraseña de aplicación con **Ctrl+Shift+V**. No se ve mientras la pegás: es normal.
5. Tiene que decir **«Listo: la tienda https://… quedó conectada»**.
6. En **«Conexión con la app de Claude»** contestá `s`. Cuando te lo pida, cerrá la app de Claude del todo (**Salir** desde el ícono de la bandeja: cerrar la ventana no alcanza) y apretá Enter.
7. Abrí la app de Claude de nuevo.

### Windows (sin probar todavía en una PC real)

1. Hacé doble clic en `instalar-windows.bat` ([INSTALACION.md](INSTALACION.md), sección B).
2. En **«Cargar productos en tu tienda (opcional)»** contestá `s`. Si hace falta, baja uv (de Astral, con su huella verificada) y un Python 3.12 solo para el conector: el Python de tu sistema no se toca.
3. Escribí la dirección de tu tienda y tu usuario, y pegá la contraseña de aplicación con **Ctrl+V** o clic derecho. No se ve mientras la pegás.
4. En **«Conexión con la app de Claude»** contestá `s`. Cuando te lo pida, cerrá la app de Claude del todo (**Salir** desde el ícono junto al reloj) y apretá Enter.
5. Abrí la app de Claude de nuevo.

Queda `conectar-tienda.bat` en `%LOCALAPPDATA%\taller-3d`: con doble clic volvés a conectar la tienda (otra contraseña u otra tienda).

### macOS (a mano)

1. En la Terminal, fijate que tengas Python 3.9 o más nuevo: `python3 --version`. Si te ofrece instalar las herramientas de línea de comandos, aceptá.
2. Desde la carpeta `instalador` del plugin, copiá el conector y conectá la tienda (revisa la tienda y te pide la dirección, el usuario y la contraseña):
   ```bash
   mkdir -p ~/.local/share/taller-3d
   cp tienda_mcp.py ~/.local/share/taller-3d/
   python3 ~/.local/share/taller-3d/tienda_mcp.py configurar
   ```
3. Cerrá la app de Claude del todo (**Cmd+Q**) y abrí con TextEdit `~/Library/Application Support/Claude/claude_desktop_config.json`. Dentro de `"mcpServers"`, agregá esta entrada (separada de la anterior con una coma). Cambiá `TU_USUARIO` por el tuyo (en la Terminal: `whoami`):
   ```json
   "taller3d-tienda": {
     "command": "/usr/bin/python3",
     "args": ["-I", "/Users/TU_USUARIO/.local/share/taller-3d/tienda_mcp.py"],
     "env": { "TALLER3D_CARPETA": "/Users/TU_USUARIO/Documents/Taller 3D" }
   }
   ```
   Si usás un Python de python.org o de Homebrew, poné su ruta en `command` (te la da `command -v python3`).
4. Guardá el archivo y abrí la app de Claude.

## 4. Comprobá que anda

- En la app de Claude, preguntá **«¿está conectada mi tienda?»**. Claude contesta con la dirección y tu usuario, sin cambiar nada.
- Para la primera carga, armá la publicación de una pieza (`/taller-3d:publicar`), aprobá la vista previa y pedí que la cargue. Claude te da el enlace al borrador: revisalo en WordPress (**Productos → Borradores**) antes de publicarlo.
- Preguntá **«¿qué productos tengo publicados?»**: Claude te dice cuáles del panel están publicados y cuáles en borrador, sin cambiar nada.
- En el panel, sección **Publicaciones**: **«Cargala como borrador»**. La primera vez, la app te pide permiso para que el panel use el conector: aceptalo.

## Cambiar de tienda o de contraseña

- **Linux y macOS:** `python3 ~/.local/share/taller-3d/tienda_mcp.py configurar`. Para ver si anda: `… tienda_mcp.py probar`.
- **Windows:** doble clic en `conectar-tienda.bat` (en `%LOCALAPPDATA%\taller-3d`).

## Actualizar el conector

Cuando una versión nueva del taller cambia el conector (el CHANGELOG lo dice), Claude deja el `tienda_mcp.py` nuevo en `taller-3d/instalador/`, dentro de tu carpeta de trabajo. La conexión no se toca: no hace falta volver a poner la contraseña.

- **Linux y macOS:** en una terminal, `install -m 0644 "<tu carpeta de trabajo>/taller-3d/instalador/tienda_mcp.py" ~/.local/share/taller-3d/tienda_mcp.py` (o corré de nuevo el instalador, que saltea lo que ya está: en el paso de la tienda, `s` para instalarlo y `n` para no conectarla de nuevo).
- **Windows:** corré de nuevo el instalador (`instalar-windows.bat`) con la misma respuesta.
- Después, cerrá la app de Claude del todo (**Salir**) y abrila de nuevo, para que arranque el conector nuevo.

## Desconectar

- **Revocá la contraseña en WordPress:** **Usuarios → Perfil → Contraseñas de aplicación → Revocar** (la de «Taller 3D»). Desde ese momento el conector no entra más.
- El desinstalador del taller borra la conexión de tu PC y saca el conector de la app de Claude (Linux: `bash desinstalar.sh`; Windows: `desinstalar-windows.bat`). En macOS, borrá `~/.config/taller-3d/credenciales-tienda.json` y la entrada `taller3d-tienda` de la configuración de la app.

## Dónde queda cada cosa

| | Linux y macOS | Windows |
|---|---|---|
| El conector | `~/.local/share/taller-3d/tienda_mcp.py` | `%LOCALAPPDATA%\taller-3d\tienda_mcp.py` |
| La conexión (tienda, usuario y contraseña de aplicación) | `~/.config/taller-3d/credenciales-tienda.json`, que solo puede leer tu usuario | `%APPDATA%\taller-3d\credenciales-tienda.json` |

La conexión queda fuera de las carpetas que Claude puede ver, y los bloqueos del taller no le dejan leerla, traerla ni copiarla: Claude nunca te va a pedir la contraseña. En la carpeta de cada pieza queda `producto/tienda.json`, con el número del producto en la tienda y los enlaces (sin la contraseña). Para ver qué productos están publicados, el conector lee también el panel (`taller-3d/catalogo.json`) y nada más.

## Problemas comunes

| Lo que te dice | Qué hacer |
|---|---|
| «No veo WooCommerce» | Activá WooCommerce en **Plugins**. El conector es solo para tiendas WooCommerce. |
| «Las contraseñas de aplicación están apagadas», o en tu perfil no aparece esa sección | Las apaga un plugin de seguridad. En Wordfence: **Wordfence → All Options → Brute Force Protection**, destildá **«Disable WordPress application passwords»** y guardá. Otros plugins de seguridad tienen una opción parecida. También pasa si WordPress no ve el sitio en https. |
| «No encuentro la API de WordPress… Enlaces permanentes» | **Ajustes → Enlaces permanentes:** elegí cualquier opción menos «Simple» y guardá. |
| «La dirección redirige a …» | Usá la dirección exacta de tu tienda, con o sin www, como la ves en el navegador. El instalador te ofrece usarla. |
| «La tienda no reconoció la conexión» | O la contraseña se revocó (creá otra y conectá de nuevo), o el servidor no le pasa a WordPress el encabezado de autorización. Mirá **Herramientas → Salud del sitio**. En servidores Apache se arregla sumando al principio del archivo `.htaccess` (vos por FTP o tu hosting) la línea `SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1`. Si el sitio entero pide un usuario y una contraseña del hosting antes de abrir, las contraseñas de aplicación no andan. |
| «Tu usuario de WordPress no tiene permiso para cargar productos» (o para subir imágenes) | Conectá un usuario con rol Administrador o Gestor de la tienda. |
| «… contestó 403 con una página» o «puede ser un firewall» | Un firewall del hosting o un plugin de seguridad bloquea la API. Tiene que dejar pasar `/wp-json/` (pedíselo a tu hosting si no sabés cómo). |
| «En tu tienda no hay una categoría …» | Te dice cuáles hay: pedile a Claude que use una de esas o que cree la nueva (la crea solo con tu OK), y que lo vuelva a cargar. También la podés crear vos en **Productos → Categorías**. |
| «… ya está en tu tienda como publicado: no lo toqué» | Es a propósito: un producto publicado no se pisa. Decile a Claude qué querés cambiar y lo cambiás vos en WordPress. Si es solo la categoría, Claude te pregunta y, con tu OK, cambia eso y nada más. |
| «No pude conectarme…» | Revisá la dirección y que la PC tenga internet. |

Si sigue sin andar, escribí `/taller-3d:instalar` en Claude: revisa la conexión y te dice qué ve.
