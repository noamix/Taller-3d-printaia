---
name: panel
description: Muestra y mantiene el panel del taller (panel.html en la carpeta de trabajo, y en claude.ai una página al costado del chat), con cada idea y pieza, el paso en que está (idea, diseño, lista para imprimir, impresa, en la tienda), a quién le toca lo que sigue, para qué impresora es y sus archivos, y lo que falta configurar para los costos; también anota ideas para más adelante. Se usa cuando el usuario dice "mostrame el panel", "qué tengo pendiente", "en qué está cada pieza", "anotá esta idea", "mostrame el catálogo", "qué piezas hice", "dónde quedó el llavero" o "marcá esta pieza como impresa".
---

# /panel: tus ideas y piezas, y en qué paso está cada una

Cargar antes la skill `impresion-3d` y seguir sus reglas, sobre todo el procedimiento de escritura (sección 4). Script: `<raíz del plugin>/skills/impresion-3d/scripts/catalogo.py`.

El panel son dos archivos de la carpeta de trabajo, y una página opcional en claude.ai:
- `taller-3d/catalogo.json`: el índice, una entrada por idea anotada (`ideas/AAAA-MM-DD_nombre`, sin carpeta en la PC) o por carpeta de `impresiones/` o `disenos/`.
- `panel.html`: la página que el usuario abre con doble clic. Arriba, cuántas ideas están pendientes, cuántas piezas en proceso y cuántas terminadas, un campo para anotar una idea, el selector **"Imprimir en"** (las impresoras preparadas y las de Orca sin preparar, más "Que me pregunte Claude"; con una sola dice cuál es), los botones "Pieza desde una foto" y "Pieza desde un STL" y la caja "Tu taller" (lo que falta para calcular costos y precios; cuando el dato es un número, como «La Ender me costó $…», el panel pide el número en un campo y recién ahí lo manda, completo). Después, "Para hacer" (lo más avanzado primero) y las terminadas por mes. Cada tarjeta muestra el recorrido (Idea → Diseño → Lista para imprimir → Impresa → En la tienda), a quién le toca lo que sigue ("Le toca a Claude" o "Te toca"), botones con el pedido para Claude, la vista o la foto, la impresora, medidas, material, tiempo, gramos, costo, precio y enlaces a sus archivos. Tiene buscador y filtros. Las imágenes se cargan de la carpeta de cada pieza. Los botones copian el pedido para pegarlo en el chat.
- **El panel al costado** (sección propia, abajo): la misma página publicada en la cuenta de claude.ai del usuario, que se abre al costado del chat. Ahí los botones le mandan el pedido a Claude cuando claude.ai lo permite; si no, lo copian.

Los pasos salen de lo que hay: una idea está pendiente; con modelo, diseñada; con G-code, lista para imprimir; marcada como impresa o con una foto de la pieza, impresa (terminada); con producto armado, en la tienda. Publicar es opcional: una pieza impresa ya está terminada. Imprimirla antes de publicarla también es opcional (0.1.39): el botón «Publicar» está en cada pieza con modelo, impresa o no, hasta que está en la tienda (0.1.40): sin publicación, pide armarla (si no está laminada, Claude la lamina primero, solo para el costo: skill `publicar`, sección 1); con la publicación armada (vista previa), la carga como borrador, igual que «Cargala como borrador» de "Publicaciones" (skill `publicar`, sección 5; el botón es la aprobación). Una pieza publicada en la tienda está terminada aunque no esté impresa: se imprime cuando la compren. Con borrador en la tienda y sin imprimir, le toca al usuario revisarlo y publicarlo.

## Al empezar

La skill `impresion-3d` (sección 3) pide decir en una línea lo pendiente al comienzo de cada conversación con el taller:
```bash
python3 -I catalogo.py resumen --catalogo catalogo.json --corto
```
("Tenés 2 ideas pendientes y 1 lista para imprimir. Todo está en panel.html, en tu carpeta de trabajo."). Si no hay nada pendiente, no decir nada. Si el usuario tiene el panel al costado (`panel_claude` en `config.json`), engancharlo a esta conversación con `watch` (`references/panel-al-costado.md`) y decir "el panel está al costado" en vez de la carpeta.

En la misma vuelta, si hay conector de la tienda y piezas en la tienda, poner al día lo que el usuario publicó o volvió a borrador (abajo, «Publicaciones», «Lo que dice la tienda»).

## Mostrar el panel

1. Traer `taller-3d/catalogo.json` y contestar con `resumen` (en texto, con lo que sigue en cada una). Si pide ver la página: en claude.ai, el panel al costado (abajo); si no, dar el enlace `computer://` a `<trabajo>/panel.html` (skill `impresion-3d`, sección 3; también se abre con doble clic y conviene guardarla como favorito del navegador). Claude no puede abrir ventanas en la PC sin terminal.
2. Si el usuario quiere seguir con algo, ofrecer el paso que corresponda: una idea o un diseño → `/pieza` (o `/diseno`); lista para imprimir → recordar el G-code y el `.3mf`; impresa → contar cómo salió o `/publicar`.

## Anotar una idea

Cuando el usuario cuenta algo que quiere hacer más adelante ("después quiero hacer un soporte para la tele", "anotá esta idea"), o deja un pedido para otro momento, ofrecer anotarla (si lo pidió, anotarla directamente):
```bash
python3 -I catalogo.py idea --catalogo catalogo.json --nombre "Soporte para la tele" \
  [--nota "para colgar el decodificador, 15 × 10 cm"] [--impresora "<nombre>"]
```
La nota guarda lo que ya se sabe (medidas, para qué es, material) para no volver a preguntarlo. Después, rehacer la página y escribir los dos archivos (abajo). Si la descarta, `quitar-idea --carpeta ideas/AAAA-MM-DD_nombre` (solo las ideas se sacan; las piezas tienen archivos).

**Cuando una idea se hace pieza** (`/pieza` o `/diseno` sobre una idea del panel): usar la nota como punto de partida y, al registrar la pieza, `agregar ... --de-idea ideas/AAAA-MM-DD_nombre`: la idea pasa a la pieza con su nombre y su nota.

## Armar o rehacer el panel

1. Ubicar la carpeta de trabajo (skill `impresion-3d`, sección 3). Traer `taller-3d/config.json` y, si a una impresora preparada le falta el consumo (`costos.py estado`), buscarlo y guardarlo antes de armar la página, sin preguntar (`references/costos.md`, «El consumo de la impresora»; si no hay promedio publicado, el estimado por la cama). Así la caja "Tu taller" no queda con "Falta el consumo".
2. Listar la carpeta de trabajo con `device_list_dir` y `recursive=true` y guardar la respuesta en `listado.json` (si se corta por cantidad, listar `impresiones` y `disenos` por separado y anteponer esa carpeta a cada nombre).
3. Traer `taller-3d/catalogo.json` si existe (anotar `mtimeMs`) y correr:
   ```bash
   python3 -I catalogo.py desde-listado --catalogo catalogo.json --listado listado.json
   ```
   Suma las piezas que faltan con nombre, impresora, fecha, archivos y paso deducidos de la carpeta, y no pisa los datos de las que ya estaban.
4. Para completar tiempo, gramos, costo y medidas de las piezas nuevas, traer sus `informe_gcode.json` e `informe_stl.json` (y `producto/publicacion.json`, o el `producto.json` de antes, si hay), de a 50 archivos como máximo, y correr `agregar` por cada una (abajo). Si son muchas, preguntar antes si vale la pena: sin esos datos la página igual muestra la vista y los archivos.
5. Poner al día los estados de la tienda, si `taller3d-tienda` está `announced` y hay piezas con `id_tienda`: `estado_productos()` y `catalogo.py estados-tienda` (abajo, «Publicaciones»).
6. Juntar las impresoras de Orca para el selector: traer las carpetas `machine`, `process` y `filament` de los perfiles de usuario (las que estén conectadas) y correr `python3 -I impresora.py detectar --maquinas <machine> --perfiles <process> <filament> --json impresoras-orca.json` (con `--orca` si hay terminal en la PC: `references/impresoras.md`, sección 1). Si no hay ninguna de esas carpetas, seguir sin `--impresoras-orca`: el selector muestra solo las preparadas.
7. Armar la página y escribir los dos archivos en la PC con el procedimiento de escritura:
   ```bash
   python3 -I catalogo.py html --catalogo catalogo.json --config config.json --impresoras-orca impresoras-orca.json \
     --salida panel.html
   ```
   `--config` (el `taller-3d/config.json` del usuario) suma la caja "Tu taller" y las impresoras preparadas; `--impresoras-orca`, las de Orca sin preparar en este taller (en el selector y en "Tu taller", sin contarlas como pendientes: se preparan la primera vez que se eligen). Sin ellos la página sale igual. En el selector queda elegida la última usada (`impresora_por_defecto`); el navegador recuerda la que elige el usuario. Commitear `catalogo.json` a `<trabajo>/taller-3d/catalogo.json` y `panel.html` a `<trabajo>/panel.html` (con `expectedMtimeMs` si ya existían; la página no necesita respaldo porque se rehace entera). Si hay panel al costado, republicarlo también.
7. **Una sola vez:** si en la carpeta de trabajo hay un `catalogo.html` (de antes de la 0.1.13), reemplazarlo por un acceso al panel, para que el favorito o el acceso viejo sigan sirviendo: `catalogo.py redireccion --salida catalogo.html` y commitearlo con su `expectedMtimeMs`.
8. Decirle al usuario dónde quedó, con el enlace `computer://` a `panel.html`, y un resumen de una o dos líneas (lo pendiente y la última pieza).

## Agregar o actualizar una pieza

Lo hacen solos `/pieza`, `/diseno` y `/publicar` al guardar. También a pedido ("marcá el llavero como impreso", "agregale una nota"):
```bash
python3 -I catalogo.py agregar --catalogo catalogo.json --carpeta impresiones/AAAA-MM-DD_nombre_impresora \
  --nombre "<nombre legible>" --impresora "<nombre de la impresora>" [--material PETG] [--color negro] \
  [--informe-gcode informe_gcode.json] [--informe-stl informe_stl.json] [--producto producto/publicacion.json] [--id-tienda 123] [--estado-publicacion vista_previa|borrador|publicada] \
  [--archivos pieza.stl pieza.py vista.png informe.md nombre_impresora.gcode nombre_impresora.3mf] \
  [--estado disenada|laminada|impresa|en_tienda] [--de-idea ideas/AAAA-MM-DD_nombre] [--nota "..."] [--url-tienda https://...]
```
- `--carpeta` es relativa a la carpeta de trabajo; `--archivos`, relativos a la carpeta de la pieza.
- Las carpetas nuevas llevan la impresora al final (`impresiones/AAAA-MM-DD_nombre_impresora`, de `catalogo.py carpeta`). El nombre de la pieza se saca sin la impresora, que queda aparte en la tarjeta; las carpetas de antes de la 0.1.12 no la tienen.
- El paso sale de los informes y los archivos (con G-code: lista para imprimir; con producto: en la tienda). "Impresa" lo marca el usuario, o Claude cuando el usuario cuenta que la imprimió; queda aunque después se arme el producto.
- Si el usuario manda una foto de la pieza impresa, guardarla como `foto.jpg` (o `foto-2.jpg`, ...) en la carpeta de la pieza y sumarla a `--archivos`: la página muestra la foto real antes que la vista y la cuenta como impresa.
- Después de `agregar`, rehacer la página (`html`) y escribir los dos archivos (paso 7 de arriba), y republicar el panel al costado si lo hay.

## Consultar

Para "¿qué piezas hice?", "¿qué tengo pendiente?" o "¿dónde está el soporte?", traer `catalogo.json` y contestar con:
```bash
python3 -I catalogo.py resumen --catalogo catalogo.json [--buscar "router"]
```
Dar la carpeta de la pieza y lo que sigue, y ofrecer el paso que corresponda (`/pieza` para hacerla, reimprimirla o cambiar medidas; `/publicar` para venderla).

## Publicaciones

Las piezas con la publicación armada (`/publicar`) salen además en el sector **"Publicaciones"** del panel (y en el filtro del mismo nombre): foto, título, precio, ganancia y dónde está cada una: vista previa sin cargar en la tienda, borrador en la tienda o publicada. El estado se guarda con `agregar`:
- `--producto <carpeta>/producto/publicacion.json`: la registra; si no se dice otra cosa queda como vista previa (o conserva el estado que tenía). Armar la publicación no marca el paso "En la tienda" de la pieza.
- `--id-tienda <número>` o `--estado-publicacion borrador`: se cargó en la tienda como borrador.
- **Lo que dice la tienda** (0.1.41): `estado_productos()` del conector `taller3d-tienda`, sin datos, devuelve el estado de cada producto que tiene anotado el panel. Guardarlo en `estados.json` y correr `python3 -I catalogo.py estados-tienda --catalogo catalogo.json --estados estados.json`. Publicada o borrador se anotan solos, con el enlace a la página del producto si está publicado o al administrador si es borrador: es lo que el usuario hizo en su tienda. Si sale `"guardado": true`, rehacer la página y escribir los dos archivos; si no, no hay nada que escribir. En la papelera o borrado no se toca: sale en `para_preguntar`; preguntarle si lo saca del panel y, con su OK, `--sacar <carpeta> [<carpeta>…]` (la publicación vuelve a vista previa, sin número, y la pieza a su paso sin la tienda; la próxima carga crea un producto nuevo). Se hace al empezar la conversación y antes de rehacer el panel.
- `--estado-publicacion publicada`: sin conector, cuando el usuario cuenta que la publicó.

Los botones de cada publicación:
- **"Ver cómo queda":** en `panel.html` abre `producto/vista-previa.html` de la pieza. Al costado llega «mostrame cómo queda la publicación de …»: traer su `producto/publicacion.json` y sus fotos, rearmar con eso la vista previa al costado (skill `publicar`, sección 4, paso 5; es siempre la misma página y muestra una publicación por vez) y decirlo. Sin páginas de claude.ai, dar el enlace `computer://` a su `vista-previa.html`.
- **"Cargala como borrador"** (solo en vista previa; el «Publicar» de la tarjeta hace lo mismo): skill `publicar`, sección 5; el botón es la aprobación. Si no hay tienda ni conector, decirlo y ofrecer el archivo para importar o la ficha.
- **"Cambiar precio o texto":** preguntar qué cambia y rehacer la ficha con la skill `publicar` (otro margen o precio, u otro texto), sin repetir lo que no cambia. Si ya está cargada, se actualiza el mismo producto (`id_tienda`).
- **"Abrir en la tienda":** si tiene `--url-tienda`.

## El panel al costado del chat (claude.ai)

La misma página, publicada privada en la cuenta de claude.ai del usuario. Solo si la conversación tiene las herramientas de páginas de claude.ai (`publish_files`, `watch`…) y el usuario lo quiere (`panel_claude` en `config.json`; la primera vez se pregunta). **Antes de armarlo, republicarlo o atender un pedido que llega desde el panel** ("[Artifact comment sent to Claude]"), leer `references/panel-al-costado.md` de la skill `impresion-3d`: cómo se publica, las fotos, el botón de Orca y cómo se contestan los pedidos.

## Reglas

- El panel solo lee y enlaza archivos de la carpeta de trabajo; no mueve, renombra ni borra piezas. Solo se sacan ideas, y solo si el usuario las descarta.
- Los nombres y notas los escribe el usuario o Claude: el script los escapa en la página. Los enlaces a la tienda solo se aceptan con `http` o `https`.
- Si `catalogo.json` está roto, no pisarlo: avisar, guardar una copia en `respaldos/` y rehacerlo desde el listado (las ideas anotadas se pierden: avisarlo).
- El panel al costado queda privado: no compartirlo ni hacerlo público (eso lo decide el usuario desde claude.ai). No lleva rutas de la PC ni datos personales de la boleta de luz.
