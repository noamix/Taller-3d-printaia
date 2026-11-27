# Cambios

## 0.1.41 (26/11/2026)

**El panel se entera solo de lo que publicás en tu tienda.** Pregunta de Leo: «¿cuándo verificás si está publicado o si está en borrador?». Hasta ahora, solo al cargar el borrador o cuando él lo contaba; los esquineros decorativos y el anclaje figuraban en borrador horas después de publicados.

- **`estado_productos()`** (conector `taller3d-tienda`, solo lectura): el estado de cada producto en la tienda (borrador, publicado, pendiente de revisión, privado, programado, en la papelera o borrado), con su enlace si está publicado. Sin `ids`, revisa los que tiene anotados el panel (`taller-3d/catalogo.json`) y dice de qué pieza es cada uno; con `ids`, esos (hasta 100). Pregunta todos juntos y, los que no aparecen, de a uno: así distingue la papelera de un producto borrado. El conector pasa a la versión 0.3.0.
- **`catalogo.py estados-tienda`:** anota en el panel lo que dijo la tienda. Publicada o borrador se anota sola (con el enlace a la página del producto, o al administrador si es borrador); en la papelera o borrado no se toca: se pregunta y, con el OK, `--sacar <carpeta>` la deja en vista previa, sin número, y la pieza vuelve a su paso sin la tienda. Si no cambió nada, no escribe.
- **Cuándo:** al empezar cada conversación con el taller (si hay conector y piezas en la tienda) y antes de rehacer el panel. Si algo cambió, Claude rehace el panel y lo dice en una línea. Las skills `impresion-3d`, `panel` y `publicar`, `MANUAL.md`, `TIENDA-WOOCOMMERCE.md` (con una sección nueva, «Actualizar el conector») y `SECURITY.md` lo explican.
- La línea de `catalogo.py agregar` dice «En la tienda (publicada)» cuando lo está (antes decía siempre «borrador»).
- **Probado con la tienda real:** el 26/11, en printaia.com.ar, la consulta de la tienda (todos juntos con `include`, `status=any` y solo los campos necesarios) devolvió los 4 productos del panel publicados, y un número que no existe dio 404, que el conector toma como borrado. Con eso el panel anotó publicado el esquinero de volutas (publicado a las 05:23).
- 1 prueba nueva (126 en total, 1 se saltea): estados desde el panel y por número, papelera y borrado, enlaces de otro sitio, datos malos, que no cambia nada en la tienda, y `estados-tienda` (anota, no reescribe sin cambios, pregunta y saca con `--sacar`).
- **Para tenerlo:** el conector nuevo queda en `taller-3d/instalador/tienda_mcp.py` de tu carpeta de trabajo; instalalo con el comando de «Actualizar el conector» (`TIENDA-WOOCOMMERCE.md`) y reiniciá la app de Claude.

## 0.1.40 (26/11/2026)

**«Publicar» queda en la tarjeta hasta que la pieza está en la tienda.** Pedido de Leo: «no aparece el botón publicar… habíamos quedado que aun sin imprimir el botón tiene que estar».

- **Panel:** con la publicación armada (vista previa), la tarjeta de la pieza sigue teniendo «Publicar», que ahora la carga en la tienda como borrador: hace lo mismo que «Cargala como borrador» de «Publicaciones». En claude.ai lleva la carpeta de la pieza, así que si la página puede usar `taller3d-tienda` la carga sin pasar por el chat y después le avisa a Claude para que la anote; si no, le manda el pedido a Claude. Antes, al armar la publicación el botón desaparecía de la tarjeta y había que buscarlo en «Publicaciones». Con el borrador en la tienda o publicada, ya no está.
- El paso que sigue de una pieza con la publicación armada lo dice: «cargarla en la tienda con «Publicar»: queda como borrador».
- `MANUAL.md`, las skills `panel` y `publicar` y `references/panel-al-costado.md` lo explican.
- `test_publicar_sin_imprimir` cubre el botón con la publicación armada, en el panel al costado y en `panel.html`, y que desaparece con el borrador cargado (125 pruebas, 1 se saltea).

## 0.1.39 (23/11/2026)

**Botón «Publicar» en cada pieza, impresa o no.** Pedido de Leo: «quisiera que exista un botón que diga publicar que no dependa de si ya lo imprimí… hay productos que yo sé que van a funcionar porque los conozco o bien porque yo ya subo el STL».

- **Panel:** «Publicar» está en cada pieza con modelo (diseñada, lista para imprimir o impresa) hasta que tiene su publicación; después la siguen los botones de «Publicaciones». Antes, «Publicala» aparecía recién con la pieza impresa. Sin imprimir, el pedido dice «sin imprimirla antes»; sin laminar, también «Laminala solo para sacar el tiempo, los gramos y el costo», y lleva la impresora elegida arriba, como los botones que arrancan una pieza.
- **Publicada sin imprimir está terminada:** pasa a «Terminadas» con «En la tienda, sin imprimir: cuando te la compren, el G-code ya está listo», y sigue teniendo «Abrila en Orca» y «Ya la imprimí». Con la publicación armada sin imprimir, el paso que sigue es verla y cargarla como borrador; con el borrador en la tienda, revisarlo y publicarlo.
- **`/publicar`:** sin G-code y con ese pedido, lamina la pieza sin preguntar (secciones 3 y 4 de `/pieza`), solo para el costo. Las fotos son de producto hechas en la computadora y la descripción lo aclara; se dice una vez, sin insistir en imprimirla.
- `MANUAL.md`, las skills `panel` y `publicar` y `references/panel-al-costado.md` lo explican.
- 1 prueba nueva (125 en total, 1 se saltea): los botones en cada paso, la impresora en el pedido sin laminar, y la pieza con la publicación armada, en borrador y publicada sin imprimir.

## 0.1.38 (23/11/2026)

- **Panel: volver atrás «Ya la imprimí» ahora sí la saca de impresas.** `catalogo.py agregar --estado disenada` o `--estado laminada` (a mano, por ejemplo después de tocar «Ya la imprimí» por error) borra la marca de impresa que se guardaba aunque cambiara el paso; antes la pieza seguía figurando como impresa y terminada. Lo que deduce el paso solo (con el G-code, por ejemplo) no la borra. Prueba nueva en `test_panel_por_linea_de_comandos`.

## 0.1.37 (23/11/2026)

**Los productos van a las categorías que les corresponden en tu tienda.** Pedido de Leo: «cuando lo subís podés agregarlo ya a las categorías que corresponde el producto?».

- **`categorias_tienda()`** (conector `taller3d-tienda`, solo lectura): las categorías de productos que tiene la tienda, con su número, dentro de cuál está («Padre › Hija») y cuántos productos tiene. `/publicar` la usa al armar la publicación para elegir, entre las que existen, la que corresponde a la pieza (o las que corresponden, hasta 5); `--categoria` de `producto_tienda.py` acepta varias, separadas por coma.
- Al cargar, las categorías se reconocen por nombre (sin importar acentos ni mayúsculas), por número o por «Padre › Hija». Si hay dos con el mismo nombre, no adivina: avisa cuáles son. Si no existe, avisa con la lista de las que hay. Al actualizar un borrador, si no encuentra ninguna, le deja las que ya tenía (antes las borraba).
- **`crear_categoria(nombre, padre)`:** crea una categoría nueva (arriba de todo o dentro de otra), solo cuando el usuario aprobó el nombre. Si ya hay una igual en ese lugar, usa esa.
- **`cambiar_categorias(carpeta)`:** le pone a un producto que ya está en la tienda las categorías de su publicación y no cambia nada más (ni el estado, ni el texto, ni el precio, ni las fotos). Para un producto publicado, solo con el OK del usuario.
- `/publicar`, la guía `TIENDA-WOOCOMMERCE.md`, `SECURITY.md` y la skill `impresion-3d` lo explican. El conector pasa a la versión 0.2.0.
- 4 pruebas nuevas (124 en total, 1 se saltea): categorías por nombre, número y ruta, ambiguas, inexistentes y que no se borran al actualizar; crear (dentro de otra, repetida, nombres malos); cambiar solo las categorías de un producto publicado; varias categorías en la ficha.

## 0.1.36 (23/11/2026)

**El conector de la tienda, para cualquiera con WordPress y WooCommerce.**

- **Guía nueva, `TIENDA-WOOCOMMERCE.md`:** qué hace y qué no, qué necesita la tienda, cómo crear la contraseña de aplicación, cómo instalarlo en Linux, Windows y macOS (a mano), cómo comprobar que anda, cambiar de tienda, desconectarla, dónde queda cada cosa y una tabla de problemas comunes (WooCommerce apagado, contraseñas de aplicación apagadas por un plugin de seguridad, enlaces permanentes «Simple», redirecciones, el encabezado de autorización que no llega, permisos, firewalls, categorías que no existen).
- **Se revisa la tienda antes de pedir la contraseña:** `tienda_mcp.py revisar` mira, sin contraseña y sin cambiar nada, lo que la tienda le muestra a cualquiera: que responda en https sin redirecciones, que tenga WooCommerce (`wc/v3`) y las contraseñas de aplicación habilitadas, y que la API de productos pida contraseña. `configurar` lo hace primero y, si falta algo, dice qué y no pide la contraseña; si la dirección redirige (con o sin www), ofrece usar la otra.
- **Windows:** `instalar.ps1` suma el paso «Cargar productos en tu tienda (opcional)»: copia el conector a `%LOCALAPPDATA%\taller-3d`, consigue un Python 3.12 propio con uv (sin tocar el del sistema), conecta la tienda, deja `conectar-tienda.bat` para volver a conectarla y agrega `taller3d-tienda` a la app de Claude junto con orca-mcp (si la app ya tenía orca-mcp, agrega solo el conector). La bajada de uv pasó a una función (`ConseguirUv`). `desinstalar.ps1` saca la entrada de la app y borra la conexión (sin pasar por la Papelera: es una contraseña). **Sin probar en una PC con Windows ni con PowerShell:** se revisó con una prueba nueva que cierra paréntesis, llaves y corchetes como los lee PowerShell, y que los dos `.ps1` siguen en UTF-8 con BOM y CRLF.
- **macOS:** instalación a mano en la guía (copiar el conector, `configurar` y la entrada para la app).
- **`/instalar`:** sección nueva «Conectar la tienda WooCommerce»: revisar la tienda sin contraseña (con `WebFetch` o el navegador), darle al usuario los pasos de la guía, nunca pedir ni aceptar la contraseña en el chat (si la pega, que la revoque y cree otra), y al volver comprobar con `estado_tienda` y declarar el conector en el panel. El instalador que se deja en la PC lleva también `TIENDA-WOOCOMMERCE.md`.
- Los mensajes del conector dicen cómo volver a conectar la tienda según el sistema (en Windows, `conectar-tienda.bat`). «Ojo: En tu tienda…» pasó a «Ojo: en tu tienda…».
- **Probado con una tienda real:** el 23/11, en printaia.com.ar (WordPress 7.1.5 y WooCommerce), la 0.1.35 cargó el kit de escuadras como borrador con sus 4 fotos; desde afuera, sin sesión, no se veía.
- 6 pruebas nuevas (121 en total, 1 se saltea): la revisión sin contraseña con una tienda de mentira (bien, sin WooCommerce, sin contraseñas de aplicación, API cerrada a visitantes, 404, otra cosa, redirección, http), `configurar` que no pide la contraseña si la tienda no sirve, los mensajes por sistema, el instalador de Windows y la guía.

## 0.1.35 (22/11/2026)

**Del botón a la tienda, sin escalas: el conector `taller3d-tienda`.**

- **`instalador/tienda_mcp.py`** (nuevo): servidor MCP local, solo con la biblioteca estándar de Python, que la app de Claude arranca como `taller3d-tienda`. `cargar_borrador(carpeta)` lee `producto/publicacion.json` de la pieza, sube sus fotos a la biblioteca de medios (las que ya subió no las repite), busca el producto por el número guardado o por SKU y lo crea o actualiza **siempre como borrador**; comprueba que quedó así y escribe `producto/tienda.json` (número, enlaces y fotos subidas, sin la contraseña). Un producto ya publicado no lo toca. Usa las categorías que existen y avisa las que faltan; las etiquetas las crea. `estado_tienda()` dice si la tienda está conectada. Habla solo con la tienda guardada, por https, y no sigue redirecciones.
- **La conexión se guarda una vez, en una terminal:** `tienda_mcp.py configurar` pide la dirección, el usuario y una contraseña de aplicación de WordPress (sin mostrarla), prueba la conexión y la guarda en `~/.config/taller-3d/credenciales-tienda.json` con permisos 600. `tienda_mcp.py probar` dice si anda.
- **Instalador de Linux:** paso nuevo «Cargar productos en tu tienda» (opcional): instala el programa, conecta la tienda y agrega `taller3d-tienda` a la app de Claude. El desinstalador quita la entrada y borra la conexión.
- **Panel:** en claude.ai, «Cargala como borrador» llama a `taller3d-tienda` desde la página si la app lo deja: el producto se carga sin pasar por el chat, la tarjeta muestra el resultado con el enlace al borrador y se le avisa a Claude para que lo anote. Si no se puede (celular, navegador, sin el programa), el pedido va a Claude, que usa el mismo conector.
- **Bloqueos:** no dejan traer, leer, copiar ni escribir `credenciales-tienda.json` (ni la carpeta `~/.config/taller-3d`) desde Claude.
- `/publicar` (sección 5) usa primero el conector; `/instalar` lo revisa con `estado_tienda`. El instalador se deja en `taller-3d/instalador/` dentro de la carpeta de trabajo (antes, `taller-3d-instalador/` en la raíz).
- 4 pruebas nuevas, con una tienda WooCommerce de mentira (115 en total). Sin probar todavía con una tienda real.

## 0.1.34 (22/11/2026)

**Una sola carpeta para todo: `Documentos/Taller 3D`.**

- La carpeta de trabajo es siempre `Taller 3D` dentro de los documentos del usuario (`Documentos/Taller 3D` en Linux, `Documentos\Taller 3D` en Windows, `Documents/Taller 3D` en macOS). Los instaladores ya no preguntan dónde guardar ni siguen usando la carpeta de una instalación anterior; si había un taller en otra, avisan («Antes usabas …») y no la tocan. `--carpeta-trabajo` y `-CarpetaTrabajo` quedan solo para probar el instalador.
- `/taller-3d:instalar` y la skill base usan esa carpeta sin preguntar. Si encuentran un taller en otra carpeta, o dos, ofrecen mudarlo.
- **`mudar_taller.py`** y la guía «Mudar un taller de otra carpeta» (`/taller-3d:instalar`, sección 3): une la configuración (manda la más completa y la otra completa lo que falte; quedan las impresoras de las dos), el catálogo (todas las piezas; avisa las carpetas repetidas) y el historial, y dice qué carpetas mover. No mueve ni borra archivos.
- En Linux sin `xdg-user-dir`, el instalador usa `~/Documents` si existe y no hay `~/Documentos`.
- 3 pruebas nuevas (111 en total).

## 0.1.33 (2026-11-22)

- **Daño y desgaste que se ven naturales:** para utilería y réplicas, los golpes, tajos y rayones ya no se hacen restando formas (dejaban cortes perfectos): se deforma la malla. `cad.py` suma `desgastar` con `marca_golpe` (hundimiento de bordes suaves con labio), `marca_tajo` (surco con el material corrido a un costado y astillados), `marca_rayon` (tiembla, cambia de hondo y se corta) y `marca_picadura`, y `deformar` para cualquier otra deformación. Una pared abollada conserva su espesor.
- **Piezas grandes en partes:** la guía de modelado explica cómo partir una pieza que apoya mal y unirla con tachas impresas (cuello con juego, agujeros iguales, tacha de media bola que se imprime parada), con un STL armado para verla.
- Las dos cosas salieron de diseñar un morrión español con golpes de batalla.

## 0.1.32 (2026-11-22)

- **Pieza desde un STL que ya tenés:** adjuntás el `.stl` en el chat (o decís en qué carpeta está) y sigue el mismo circuito que una pieza diseñada: revisión, configuración, G-code, proyecto de Orca, costo y publicación. En el panel hay un botón **Pieza desde un STL**. Claude no le cambia la forma; guarda tu archivo como `original.stl` y lamina `pieza.stl`, ya orientado.
- **Cómo apoyarla:** `revisar_stl.py --orientar` compara las seis caras de apoyo (superficie de apoyo, voladizos, alto y si entra en la cama) y dice qué rotación usar.
- **Unidades:** si el STL es diminuto, avisa que seguramente está en metros, pulgadas o centímetros y cómo escalarlo.
- **De quién es el modelo:** el panel guarda si el STL es tuyo o bajado, de dónde y con qué licencia, y lo muestra en la tarjeta. Para vender un modelo bajado la licencia tiene que permitir uso comercial.

## 0.1.31 (2026-11-22)

- **Sector «Publicaciones» en el panel:** cada pieza con la publicación armada tiene su tarjeta con la foto, el título, el precio, lo que ganás y dónde está: vista previa sin cargar, borrador en la tienda o publicada. «Ver cómo queda» abre la página del producto como se vería en la tienda (en `panel.html`, el archivo de la pieza; al costado del chat, se lo pide a Claude), y hay botones para cargarla como borrador y para cambiar el precio o el texto. También hay un filtro «Publicaciones».
- **Armar la publicación ya no marca la pieza como «En la tienda»:** ese paso se marca cuando se carga como borrador o cuando contás que la publicaste (`catalogo.py agregar --estado-publicacion`).
- `/taller-3d:publicar` anota la publicación en el panel apenas arma la vista previa.

## 0.1.30 (2026-11-22)

- **Publicar, más simple:** el primer paso de `/taller-3d:publicar` es un solo comando (`producto_tienda.py --opciones`) que dice qué falta configurar, cuánto cuesta la pieza y las tres opciones de margen. La carpeta `producto/` queda con tres archivos (`publicacion.json`, `ficha.md` y `vista-previa.html`) en vez de cinco: `producto.json` repetía lo que ya está en `publicacion.json`, y el CSV de WooCommerce sale solo si hace falta (`--csv`).
- **Cargar en la tienda, paso a paso:** con el conector de WooCommerce, Claude busca primero si el producto ya existe (por su número o su SKU) y lo actualiza en vez de crear otro, comprueba después de cargar que quedó como borrador, y anota el número del producto en el panel (`catalogo.py agregar --id-tienda`). Un producto ya publicado no se pisa sin preguntar. Si la herramienta no acepta fotos, el borrador queda sin fotos y te dice cuáles subir. Este camino todavía no se probó con una tienda real.
- **Instrucciones más cortas:** el panel al costado del chat y las fotos de producto con Blender pasaron a guías aparte, que Claude lee solo cuando las usa. Un pedido común al panel gasta menos.
- **Un solo formato para la plata** en el panel, la ficha y la vista previa («$ 12.300», sin centavos desde $ 100).
- **Configuración más limpia:** al guardar un dato de costos se van las claves viejas vacías de la tienda (`margen_pct`, `costo_hora_maquina`).

## 0.1.29 (2026-11-22)

- **Impuestos de la venta:** le decís cómo facturás (monotributo, responsable inscripto, exento o sin facturar) y si pagás Ingresos Brutos, y el precio de cada canal ya los descuenta: el margen que elegís es el que te queda de verdad. Si sos responsable inscripto, el precio sale con IVA incluido, el margen es sobre el precio sin IVA, la comisión se calcula sobre el precio con IVA (y su IVA no es costo, porque lo descontás) y las compras con factura A que digas (filamento, impresora, embalaje, luz) entran sin IVA. Lo guarda `costos.py impuestos`; «Tu taller» lo pide si falta.
- **Margen según la pieza:** opcionalmente, un precio mínimo por pieza y márgenes por escalones según el costo de la pieza (más margen en las chicas, menos en las grandes). Las tres opciones de margen de cada producto se arman alrededor del escalón de esa pieza. `costos.py margen` guarda el margen habitual, también como recargo sobre el costo (`--recargo 100` = el doble del costo = 50 % de margen), los escalones y el mínimo.
- **«Tu taller» pide el número:** los datos con monto o porcentaje («La Ender me costó $…») tienen un campo en el panel y se mandan completos. Antes, a Claude le llegaba la frase con «$…» sin el número.
- **El instalador se acuerda de tu carpeta de trabajo** aunque ya existiera, así una corrida sin `--carpeta-trabajo` no vuelve a `Documentos/Taller 3D` (Linux y Windows). **No escribe la configuración de la app de Claude mientras siga abierta** (la app la reescribe al cerrarse y se perdía el cambio): pide cerrarla del todo y, si sigue abierta, no la toca. Si la configuración del taller ya existía, anota tu ACEPTO (con respaldo). El desinstalador tampoco toca la configuración de la app con la app abierta.
- **`/taller-3d:instalar` revisa a qué carpeta atiende el programa que abre Orca** (con una sonda que no abre nada) y explica cómo arreglarlo si es otra.
- **`costos.py --help`** ya no se rompe por un «%» suelto en la ayuda.

## 0.1.28 (2026-11-22)

- **Las fotos de producto se hacen en tu PC si tenés el conector de Blender:** con Blender en segundo plano (nunca en la ventana que tengas abierta), una foto por vez. En una PC con un i5 de 6 núcleos, las cuatro tardaron unos 2 minutos, contra casi 7 en el espacio de Claude, y no hay que instalar Blender en cada conversación. Las fotos salen iguales. El fondo blanco y la sombra se arman en el espacio de Claude, porque el Blender de la PC no trae Pillow. Si el conector no está o falla, se hacen como antes.
- **`render_producto.py`:** `renderizar_crudos()` (solo Blender: renders y máscaras en crudo; usa la placa de video si Blender la encuentra) y `--desde-crudos` (solo Pillow: arma las fotos). Importa STL también en Blender 4.0 o anterior. El plugin trae `datos/vacio.blend` para abrir Blender en segundo plano.

## 0.1.27 (2026-11-22)

- **La publicación trae cuatro fotos desde ángulos distintos:** a tres cuartos con fondo blanco (la primera de Mercado Libre), desde el otro lado, de frente y desde arriba, numeradas en el orden de la galería (`producto-1-principal.jpg` … `producto-4-arriba.jpg`). Antes salían dos fotos del mismo ángulo. El otro lado se hace girando la pieza, así la luz y la sombra quedan iguales. La foto con fondo cálido para redes sale si se pide (toma `tienda`), ahora como `producto-5-tienda.jpg`.
- **`render_producto.py`:** toma nueva `atras` (con menos contraluz, para que no se queme lo que queda detrás); por defecto `principal,atras,frente,arriba` con 16 muestras (unos 7 minutos las cuatro con 2 núcleos). En la pieza desde una foto, el dorso de una cáscara se muestra con la toma `atras`.

## 0.1.26 (2026-11-22)

- **Vista previa de la publicación:** antes de cargar el producto, `/publicar` muestra cómo se vería la página en tu tienda (galería de fotos, título, precio, descripción y ficha técnica) y, abajo, lo que conviene revisar: si las fotos son ilustrativas, el título para Mercado Libre con sus caracteres, si la primera foto tiene fondo blanco, el precio y la ganancia en cada canal y quién escribió el texto. Se abre al costado del chat (siempre la misma página) y queda como `vista-previa.html` en la carpeta `producto/` de la pieza. Se aprueba con su botón o en el chat, también desde el celular; recién ahí se carga el borrador.
- **El texto de venta lo puede escribir tu Gemini gratis:** con `generadores_ia.textos = "gemini"`, Claude abre Gemini en tu navegador, con tu cuenta de Google, le pasa los datos de la pieza y las reglas, y usa su respuesta después de revisarla (`references/textos-con-gemini.md`). Si Gemini no está disponible, escribe Claude con las mismas reglas. Las medidas, el material, el peso y los cuidados no los escribe ninguna IA: salen de los informes de la pieza.
- **`textos_ia.py`:** arma el pedido para Gemini en una sola línea y revisa la respuesta: largo del título (60 caracteres para Mercado Libre), afirmaciones que no se pueden sostener (alimentos, lavavajillas, uso médico, chicos, certificaciones, garantía, irrompible), contactos y enlaces, promociones, menciones de la IA, exclamaciones, emojis y números que no están en los datos.
- **`producto_tienda.py`:** `--textos`, `--fotos-reales` y `--carpeta`; deja también `publicacion.json` y `vista-previa.html`, y si solo hay fotos renderizadas, la descripción aclara que son ilustrativas. Nuevo `vista_publicacion.py` para la página de claude.ai.

## 0.1.25 (2026-11-22)

- **La impresora se elige al arrancar cada pieza, entre todas las de tu Orca:** antes, la pregunta solo aparecía si había dos o más impresoras preparadas en el taller; con una sola preparada, Claude seguía con esa aunque tuvieras otra en Orca. Ahora cuenta las impresoras de Orca (también las que todavía no están preparadas en esta carpeta) y pregunta en cuál siempre que haya más de una y no la hayas dicho. Si elegís una sin preparar, Claude la prepara antes, la primera vez.
- **Selector "Imprimir en" en el panel** (en el archivo y al costado del chat): elegís la impresora de una lista con las preparadas y las de Orca sin preparar, o "Que me pregunte Claude". Los botones que arrancan una pieza ("Diseñala", "Dejala lista para imprimir", "Pieza desde una foto") se la dicen a Claude, y el navegador se acuerda de la que elegiste. Con una sola impresora, el panel dice cuál es.
- **"Tu taller" dice "Preparada en este taller"** y nombra las otras impresoras de Orca, que se preparan al elegirlas (no quedan como pendientes). La que está elegida en la ventana de Orca no le llega a Claude: el panel lo avisa.
- **`impresora.py detectar`** suma las impresoras de los perfiles `AUTO proceso @…` y `AUTO filamento @…`, aunque no esté conectada la carpeta `machine` ni los perfiles las nombren, y las junta con la copia de usuario del mismo modelo. Con `--json` guarda la lista para el panel (`catalogo.py html --impresoras-orca`) y para `costos.py estado --impresoras-orca`.

## 0.1.24 (2026-11-22)

- **"Tu taller" ya no tiene botón para el consumo:** como Claude lo busca o lo estima y lo guarda solo, el consumo de cada impresora queda tildado con su origen ("130 W (estimado)") y no se pide. Si todavía falta, dice que Claude lo busca solo. Si medís el real con un medidor de enchufe, se lo pasás en el chat.

## 0.1.23 (2026-11-22)

- **El consumo de la impresora se completa solo, también en las impresoras preparadas antes de la 0.1.19:** al empezar una conversación con el taller y al armar el panel, si a una impresora le falta el consumo, Claude lo busca en internet y, si el fabricante solo publica la potencia máxima, lo estima por el tamaño de la cama, sin preguntarte ni esperar a que toques el botón. "Falta el consumo" ya no queda en "Tu taller".

## 0.1.22 (2026-11-22)

- **El panel ya no da por impresa una pieza por una foto cualquiera:** solo cuenta `foto.jpg` (o `foto-2.jpg`, …) en la carpeta de la pieza, que es la foto de la pieza impresa. La foto de referencia de una pieza generada desde una foto se guarda como `referencia.jpg` y no la cambia de paso. Si no hay foto real ni foto de producto, la tarjeta muestra la primera vista (`vista…`).

## 0.1.21 (2026-11-22)

- **Pieza desde una foto** (`references/foto-a-3d.md`): para copiar algo que existe (una máscara, una figura, una escultura), el modelo 3D lo genera Hunyuan 3D de Tencent con tu cuenta, desde tu Chrome. Claude sube la foto, espera, baja el STL de tu carpeta de descargas (solo ese archivo) y lo deja imprimible. Probado de punta a punta con una máscara de piedra.
  - **Varias fotos:** Hunyuan acepta de 2 a 8 del mismo objeto (frente, costados, atrás) y el modelo sale más fiel. Si tenés una sola, las otras vistas se pueden generar con Nano Banana (Gemini o Flow) y las aprobás antes de usarlas.
  - **Primero una imagen:** si pedís algo por cómo se ve que no sale bien con Blender por código, Claude genera una imagen con tu Gemini o tu Flow, la aprobás y recién ahí la pasa a 3D, así no gastás puntos de Hunyuan en algo que no querías.
  - Antes de generar te dice cuántos puntos o imágenes gasta. El login y los captchas los hacés vos.
- **Lo generado y lo diseñado juntos:** en un pedido como "la máscara y un soporte para la mesa", Claude te dice antes qué parte hace cada herramienta. La parte diseñada se mide sobre el modelo generado: `cad.hueco_para` da el hueco con la forma exacta del borde de la pieza, sin trabas. Por defecto van separadas, cada una en su mejor posición para imprimir.
- **`engrosar_stl.py`:** los modelos de IA suelen salir como una cáscara de menos de 1 mm de pared. Este script los lleva a 2 mm moviendo solo la superficie de adentro, así el detalle de afuera no cambia (en la máscara se movió 0,08 mm como mucho). Rehace la malla con voxels, saca las sobras y respeta los huecos de una figura cerrada. Usa Blender para Python.
- **`revisar_stl.py`** avisa si la pieza es una cáscara fina (rechazo si la pared no llega a 0,6 mm) y escala: `--alto` la lleva parejo a un alto en mm (lo de IA viene sin unidades) y `--escala` multiplica las medidas.
- **El panel** tiene un botón "Pieza desde una foto": manda el pedido a Claude (o lo copia) y te recuerda adjuntar la foto en el chat, porque la página no puede mandar fotos.
- **`/instalar`** pregunta, si querés, si tenés cuenta en Hunyuan 3D y si usás Gemini o Flow (`generadores_ia` en `config.json`), y te recomienda apagar en Chrome "Preguntar dónde guardar cada archivo" para que los modelos se bajen solos.
- **Pendiente:** leer el acuerdo de servicio de Hunyuan 3D sobre el uso comercial de lo generado (la página no cargaba). Hasta entonces, `/publicar` te pide confirmarlo antes de vender una pieza generada.

## 0.1.20 (2026-11-22)

- **Con qué modelar, por regla y no por comodidad** (`references/modelado.md`):
  - lo que se describe con medidas (soporte, caja, adaptador) va por código, con `cad.py`;
  - lo que se describe por cómo se ve (una figura, un logo, texto, formas suaves) va en Blender por código o sale de un modelo que ya existe;
  - si tiene las dos cosas, cada parte va con su herramienta y se unen.

  Claude no arma con esferas, conos y cajas algo que tiene que verse bien: si el código no alcanza, lo dice y cambia de herramienta.
- **Antes de modelar algo conocido**, busca si ya existe en Printables, MakerWorld o Thingiverse y te lo ofrece con su licencia; si es para vender, solo sirven los de uso comercial. Personajes, mascotas de marcas y logos ajenos no se modelan ni se venden.
- **Blender por código en el espacio de Claude** (`bpy`), con una plantilla probada: bolas que se funden, curvas, texto en relieve, malla cerrada con Remesh y STL en mm. `cad.importar_stl` trae ese STL (o uno bajado) para unirlo a una pieza hecha por código.
- **Vista con foto para lo decorativo:** además de las cuatro vistas, una foto renderizada en unos 40 segundos. Claude la mira antes de mostrártela y te dice qué es aproximado.
- **`revisar_stl.py` mira las partes separadas:** una parte suelta en el aire (por ejemplo, una cabeza que no se fundió con el cuerpo) es RECHAZO, y una que toca la pieza sin estar unida es advertencia. Los huecos internos no cuentan.

## 0.1.19 (2026-11-22)

- **El consumo de la impresora se busca, no se pregunta.** Cuando una impresora entra al taller, o una cuenta de costo usa una que no lo tiene, Claude lo busca en internet:
  1. el consumo promedio que publica el fabricante;
  2. si no, una prueba publicada del mismo modelo, medida con un medidor de enchufe;
  3. si la ficha solo da la potencia nominal (la de la fuente, que es el máximo calentando), lo estima por el tamaño de la cama y el material que más usás, y te avisa que es estimado;
  4. te pregunta solo si no encuentra nada.
- `costos.py consumo` guarda el consumo con su origen, la fecha y la potencia nominal. Un dato medido por vos no se pisa con un estimado.
- En "Tu taller" del panel, el botón de una impresora sin consumo dice "Buscá el consumo de la … en internet"; si es estimado, el botón es para medir el real.
- **La impresora se elige antes de calcular nada.** Si tenés más de una y no dijiste cuál, `/pieza` la pregunta junto con las otras preguntas del principio, con la más conveniente primero (la que mejor encaja por tamaño y material, o la última que usaste) y en cada una su cama, si es cerrada y si ya está preparada. No pregunta si tenés una sola, si la nombraste o si para la pieza sirve una sola: te dice cuál y por qué.

## 0.1.18 (2026-11-21)

Correcciones del instalador de Linux, de la primera prueba en una PC real.

- En el modo prueba (`--prueba`), el paso "Abrir Orca desde Claude y desde el panel" se salteaba porque el lanzador de Orca todavía no existía. Ahora muestra lo que haría.
- Si ya tenías el taller instalado, el final dice que fue una actualización y qué hacer: reiniciar la app y escribir `/taller-3d:instalar`. Antes repetía los pasos de una instalación nueva.
- Recuerda usar `--carpeta-trabajo` si la carpeta que toma no es la que usás con Claude. Toma la de una instalación anterior, y el programa que abre Orca solo abre proyectos de esa carpeta.

## 0.1.17 (2026-11-21)

- **"Abrila en Orca" abre Orca de verdad** (Linux). El instalador puede agregar `taller3d-orca` (`instalador/abrir_orca.py`), un programa chico del taller que la app de Claude arranca como servidor MCP local. Hace una sola cosa: abrir en la ventana de Orca el proyecto `.3mf` de una pieza de tu carpeta de trabajo.
  - **Desde Claude:** cuando pedís ver la pieza, o tocás el botón del panel y el pedido llega al chat, Claude la abre con ese programa.
  - **Directo desde el panel al costado:** si la app de escritorio deja que la página use el programa, el botón abre Orca sin pasar por el chat. La primera vez la app te pide permiso. Si no puede, el pedido va a Claude como antes.
  - **Seguridad:**
    - solo abre `.3mf` de tu carpeta, sin scripts, con el Orca que el instalador configuró;
    - no lamina, no imprime y no escribe nada;
    - rechaza rutas de afuera, enlaces y nombres de archivo armados para colar comandos.
  - **Para tenerlo:** corré de nuevo el instalador en Linux (saltea lo que ya está) y reiniciá la app de Claude. En Windows todavía no está: el botón le pasa el pedido a Claude, que te da el enlace al `.3mf`.

## 0.1.16 (2026-11-21)

Correcciones de una revisión independiente de la 0.1.15.

- **Bloqueo en Windows:** una ruta escrita con la barra doble (`C://Users/...`) pasaba como dirección web y dejaba copiar entera la carpeta de datos de Orca, con `OrcaSlicer.conf`. Ahora se bloquea igual que `C:/Users/...`.
- **Precio cerca del tope del cargo fijo** (Mercado Libre): salía más caro de lo necesario, por ejemplo $ 22.100 en vez de $ 20.000. Ahora el precio nunca baja cuando el costo sube.
- **Panel:**
  - el enlace a la tienda y las imágenes se revisan también al armar la página;
  - el nombre de la pieza va en el pedido en una sola línea y recortado, y Claude lo toma como dato, no como orden;
  - una entrada rara en el índice ya no rompe la página.
- **Fotos de producto:**
  - la cámara se acerca hasta que la pieza llena el cuadro, así la foto de 1200 px tiene detalle de 1200 px (antes se agrandaba hasta 1,45 veces);
  - lee mejor los colores ("verde azulado" es verde, nombres en inglés) y avisa si no reconoce uno.
- **Costos:**
  - el precio del kWh puede ser menor que 1, para otras monedas;
  - acepta valores escritos como "15 %" o "0,18", y el precio del filamento también como número;
  - la boleta vieja se mide por su período;
  - avisa cuando el G-code es de una impresora que no está en la configuración;
  - `costos.py luz` no escribe nada si no encuentra la configuración;
  - la revisión del G-code muestra todas las partes del costo y lo que falta.
- La regla de "nada a internet" nombra el panel al costado como segunda excepción, y la pregunta para activarlo avisa que lleva costos y precios.

## 0.1.15 (2026-11-21)

- **Enlaces a tu PC:** cada vez que Claude te dice dónde quedó algo (la carpeta de la pieza, el G-code, el `.3mf`, el panel o las fotos de producto), te deja un enlace para ir directo. El del `.3mf` lo abre con el programa que tengas para esos archivos.
- **Los botones del panel al costado sí le mandan el pedido a Claude** (probado): le llega a la conversación que publicó el panel. Claude te contesta en el comentario antes de volver a publicar el panel, porque al republicarlo los comentarios de antes pueden desaparecer. Si tocás dos veces el mismo botón, lo hace una sola vez.

## 0.1.14 (2026-11-21)

- **Costo real de cada pieza** (`costos.py`, `references/costos.md`): material, luz, desgaste de la impresora, las que salen mal, tu tiempo y embalaje. La luz sale de tu boleta: mandale una foto o el PDF y saca el precio del kWh (el del último escalón más impuestos, o el promedio sin los cargos fijos si la boleta no lo separa). Guarda solo los números de la tarifa, nada personal. Cada impresora tiene su consumo (medido con un medidor de enchufe, o estimado con su fuente) y su precio, repartido en sus horas de vida. El tiempo es el de Orca más el calentamiento.
- **Precio por canal, con el margen sobre el precio:** tu tienda, Mercado Libre (comisión, cuotas, IVA sobre la comisión y cargo fijo de las ventas baratas) u otros. El `margen_pct` de antes era un recargo sobre el costo: se convierte (un recargo del 50 % es un margen del 33 %) y avisa.
- **El margen se elige en cada producto:** `/taller-3d:publicar` te pregunta con tres opciones (una más baja, tu habitual y una más alta), cada una con el precio y lo que ganás, o le decís un precio y te muestra el margen real que te deja en cada canal.
- **Fotos de producto con Blender** (`render_producto.py`), en el espacio de Claude: plástico del color y el tipo de tu filamento, líneas de capa, luz de estudio. Salen cuadradas y sin texto: la principal con fondo blanco puro y sin sombra, como pide Mercado Libre, y otra con sombra suave para tu tienda (y, si querés, de frente y desde arriba). La imagen simple de antes (`vista_previa.py --producto`) ahora también sale con fondo blanco y sin texto (la leyenda es opcional).
- **La guía:** al empezar sin un pedido concreto, Claude te ofrece opciones para tocar con lo que sigue; en `/taller-3d:pieza` ves las etapas en la lista de tareas; y cada vez que te toca algo, termina con "Te toca: …".
- **El panel dice a quién le toca** ("Le toca a Claude" o "Te toca"), trae botones con el pedido para cada pieza, un campo para anotar ideas y la caja "Tu taller" con lo que falta para los costos. En el archivo, los botones copian el pedido.
- **El panel al costado del chat:** en claude.ai, Claude puede publicar el panel como página privada en tu cuenta, al lado del chat, y lo actualiza solo. Sus botones están listos para mandarle el pedido a Claude ("Enviar a Claude"); mientras claude.ai no deje que una página despierte el chat, lo copian.
- `revisar_gcode.py --config` calcula el costo con tu configuración; la ficha del producto muestra el costo por partes y el precio por canal.

## 0.1.13 (2026-11-21)

- **El panel del taller** (`/taller-3d:panel`, reemplaza a `/taller-3d:catalogo`). `panel.html`, en la carpeta de trabajo, muestra cada idea y pieza con su recorrido (Idea → Diseño → Lista para imprimir → Impresa → En la tienda), qué sigue, para qué impresora es, su vista, datos y archivos. Arriba dice cuántas hay pendientes, en proceso y terminadas, con filtros y buscador; primero va "Para hacer" (lo más avanzado primero) y después las terminadas, por mes. Una pieza impresa ya cuenta como terminada: publicarla es opcional.
- **Ideas para después:** "anotá esta idea: …" la deja pendiente en el panel con lo que ya se sabe (medidas, uso). Cuando se hace, pasa a la pieza con su nombre y su nota.
- Al empezar a usar el taller, Claude dice en una línea lo pendiente ("Tenés 2 ideas pendientes y 1 lista para imprimir").
- El `catalogo.html` de antes se reemplaza una vez por un acceso al panel, así el favorito viejo sigue sirviendo.

## 0.1.12 (2026-11-21)

- **Proyecto de Orca de cada pieza.** Junto con el G-code queda un `.3mf`: con doble clic, Orca abre la pieza en el centro de la cama con la impresora, el filamento y el proceso AUTO elegidos, y con tu tipo de cama real (por línea de comandos Orca usa Cool Plate). Lo arma `proyecto_3mf.py` con el STL y la configuración completa que Orca escribe en el G-code, porque orca-mcp no exporta proyectos. Se probó en la ventana de Orca 2.5.1: abre con los tres perfiles sin cambios, y Orca por línea de comandos lo lamina con la misma configuración. Si Orca estaba abierto desde antes de crear los AUTO, hay que cerrarlo: si no, los muestra como cambios sobre el perfil de sistema.
- **La impresora va en el nombre** de la carpeta de la pieza y del G-code (`impresiones/2026-11-21_soporte-router_ender-3-v3-plus/soporte-router_ender-3-v3-plus.gcode`), porque un G-code solo sirve para la impresora para la que se laminó. Las vueltas de prueba de Orca quedan aparte, en `laminado/`. `catalogo.py carpeta` arma los nombres, y el catálogo muestra la impresora de cada pieza.
- **Abrir Orca con la pieza:** si Claude tiene terminal en la PC, pregunta antes y lo abre con el proyecto. Imprimir sigue siendo tuyo: nunca usa la pestaña Dispositivo ni los botones Imprimir o Enviar.
- El bloqueo de la terminal ya no frena direcciones web como `https://github.com/OrcaSlicer/OrcaSlicer` (las tomaba por la carpeta de datos de Orca). `file://` sigue contando como ruta.

## 0.1.11 (2026-11-21)

Correcciones de la prueba con la Creality Hi en una PC real.

- **El bloqueo de la terminal ya no frena comandos que solo nombran la carpeta de perfiles de Orca.** Un script que arma un `config.json` con esa ruta adentro ya pasa: ahora se mira a dónde escribe (`open(..., "w")`, `write_text`, `shutil.copy`, `Set-Content -Path`), no lo que escribe. Escribir de verdad en esa carpeta sigue bloqueado.
- Un comodín (`cat carpeta/*`) solo cuenta como intento de leer `OrcaSlicer.conf` si apunta a la carpeta de datos de Orca, no a otra que se llame parecido (como `OrcaSlicer Claude`).
- **`M5001`, el timelapse de Creality** (Hi, SPARKX i7), ya no sale como comando desconocido: la revisión lo explica y revisa el movimiento o la pausa que va detrás como cualquier otro (una posición fuera de la cama se rechaza igual).
- `novedades_orca.py` ya no da como "ya no están" las claves que simplemente no trae un G-code de la misma versión de Orca (por ejemplo, las `filament_*` de retracción): eso depende de la impresora y del filamento. Solo se fija en las que faltan cuando el G-code es de otra versión.

## 0.1.10 (2026-11-21)

- **Carpeta de trabajo más fácil.** Antes de preguntar, `/taller-3d:instalar` se fija si el instalador ya la creó. Si no existe, la crea: con la terminal de la PC, directamente; si no, te da a elegir entre que la cree Claude (con un permiso sobre Documentos que dura esa conversación y se usa solo para la carpeta nueva) o crearla vos desde el **+** → **Agregar carpeta**, con los pasos exactos, y así queda creada y conectada a la vez.
- **Una sola carpeta de perfiles de Orca:** se conecta `user/default`, que tiene adentro `process`, `filament` y `machine`. Sirve aunque `machine` todavía no exista, y ahí se puede guardar después la copia de la impresora. Si ya tenías conectadas `process` y `filament` por separado, siguen sirviendo. Los instaladores muestran esa sola ruta.
- La guía y el README dicen dónde está **Buscar actualizaciones** (Plugins › Agregar › Administrar marketplaces): en un marketplace agregado desde la app, la sincronización automática no se dispara sola.

## 0.1.9 (2026-11-21)

Correcciones de una revisión independiente de la 0.1.8.

- **`OrcaSlicer.conf`, mejor protegido.** Ya no se puede sacar copiando, comprimiendo o buscando en toda la carpeta de datos de Orca, ni con comodines, nombres partidos o la copia `.bak` que Orca hace en Windows. Para leer la lista de impresoras solo pasan los dos comandos fijos de la guía, con la ruta absoluta. De la carpeta de datos de Orca solo se traen los perfiles (`user/` y `system/`). En Claude Code, `Read` y `Grep` también quedan bloqueados para ese archivo.
- El bloqueo ya no frena comandos inofensivos que solo nombran el archivo (buscarlo en el código, un mensaje de commit) o miran si existe (`ls`, `stat`, `Test-Path`).
- **La revisión del G-code no usa los límites de otra impresora.** Si el G-code dice el modelo, solo sirven los datos de ese modelo: una A1 mini ya no toma los de una A1. Sin modelo, la impresora tiene que estar al final del nombre del perfil, sin distinguir mayúsculas. Si no coincide ninguna, o coinciden dos, usa límites genéricos y ahora lo avisa.
- El nombre con el que se reconocen los perfiles de una impresora ahora es el modelo completo (`Bambu Lab A1 mini`, no `Lab A1 mini`).
- `impresora.py detectar` agrupa bien las boquillas entre paréntesis (`Creality K1 (0.4 nozzle)`), `HF0.4`, mayúsculas distintas y copias de copias, y no se cae con datos raros ni con archivos guardados por PowerShell (UTF-16).
- Perfiles `AUTO` sin impresora: `@K1` ya no se confunde con una K1 Max, ni `@A1` con una A1 mini.
- **Copia de la impresora:** lo más seguro es guardarla desde Orca, que además crea la carpeta `machine` si no existe. Claude la puede crear con `perfil_orca.py crear --tipo maquina --base-id <setting_id>`, sin necesitar los datos completos de la impresora.
- Los comandos para leer la lista de Orca ignoran la línea de control (`# MD5 checksum`) que Orca agrega en Windows.

## 0.1.8 (2026-11-21)

Correcciones de una prueba real con varias impresoras en Orca.

- **Ve todas las impresoras de Orca, no solo las que tienen copia de usuario.** `impresora.py detectar` junta las copias de usuario (carpeta `machine`), las impresoras que nombran tus perfiles en `compatible_printers` y, si Claude tiene terminal en tu PC, la lista de Orca y la impresora elegida, leídas ahí mismo de `OrcaSlicer.conf`. Para saber el modelo usa `compatible_printers`, no `inherits`, que puede traer nombres viejos.
- **Pregunta en cuál trabajar** poniendo primero la elegida en Orca o la última usada, marca cuáles tienen copia y avisa que elegir una impresora en la ventana de Orca no le llega a Claude.
- **Crea la copia de usuario** de la impresora si no la tiene (`perfil_orca.py crear --tipo maquina`), en la carpeta `machine`; después hay que reiniciar Orca. También la podés guardar vos en Orca.
- La carpeta `machine` de los perfiles de Orca se pide junto con `process` y `filament`, en un solo pedido. Los instaladores la muestran al final.
- **`OrcaSlicer.conf` no se trae ni se lee entero:** guarda la IP y el código de acceso de las impresoras en red. Un bloqueo nuevo impide traerlo con `device_stage_files` o leerlo entero por terminal; solo se aceptan los comandos que sacan `models` y `presets.machine`.
- `/taller-3d:instalar` comprueba que la carpeta de trabajo exista antes de pedir el permiso (la app solo conecta carpetas que existen) y, si no existe, te pide que la crees.
- Los perfiles `AUTO` de una impresora con copia de usuario ya no salen como "sin impresora" aunque esa impresora no esté preparada en el taller (`novedades_orca.py perfiles --maquinas`).
- El nombre corto de una impresora para reconocer sus perfiles ya no puede ser algo como "Hi" (de "Creality Hi"), que coincidía con "High Flow": queda el modelo completo y se compara como palabra entera.
- **Comandos con prefijo:** en la app se escriben `/taller-3d:instalar`, `/taller-3d:pieza`, etc. Se corrigieron README, INSTALACION, el manual, la ayuda, el cierre de `/taller-3d:instalar`, los instaladores y el flyer.

## 0.1.7 (2026-11-21)

- **El plugin ya no trae impresoras cargadas.** Se borraron los datos fijos de la Creality Ender-3 V3 Plus: cada persona tiene las suyas, y no se pueden guardar todas.
- **Elegir la impresora:** el taller lista las impresoras que tenés en Orca y, si hay varias, te pregunta en cuál querés trabajar (la última usada aparece primera). En `/instalar` se prepara solo la que elegís; las demás, cuando las uses.
- **Investigar y configurar:** la primera vez que usás una impresora, Claude busca en internet sus datos oficiales (temperaturas máximas, volumen, cerramiento) y sus perfiles de OrcaSlicer, pregunta lo que no encuentre (no inventa límites), arma los perfiles AUTO óptimos y comprueba con un cubo de prueba que los datos coincidan con lo que usa Orca. Quedan en `taller-3d/impresoras/<id>.json` de tu carpeta de trabajo.
- **Si una pieza no entra** en la impresora elegida, te dice en cuál de tus otras impresoras entra (`revisar_stl.py --otras`).
- Nuevo `impresora.py` (`validar`, `desde-gcode`, `comparar`) y `references/impresoras.md`.
- Los scripts ya no suponen ninguna impresora: sin sus datos, las temperaturas se controlan con límites genéricos (300 °C de boquilla, 120 °C de cama) y el área no se revisa. El bloqueo automático usa los datos de la impresora si están en el espacio de Claude.
- Configuraciones de antes: si `datos` apunta a la Ender-3 V3 Plus del plugin, `/impresoras` la vuelve a preparar.
- 52 pruebas automáticas, con una impresora inventada.

## 0.1.6 (2026-11-21)

- El catálogo de parámetros va en partes de menos de 200 KB, con un parámetro por línea.
- El README cuenta qué corre el plugin, qué toca, qué baja y qué manda.
- Nombre visible "Taller 3D". Se quitó el campo `network` de `plugin.json`, que Claude no lee.
- El directorio de plugins de Anthropic solo acepta scripts y bloqueos automáticos de organizaciones verificadas: por ahora el taller se distribuye solo por GitHub.
- Instalación desde GitHub: el README, `INSTALACION.md` y el manual explican cómo sumarlo en la app de Claude o en Claude Code y cómo recibir las versiones nuevas (en Claude Code las actualizaciones automáticas de este marketplace hay que activarlas). El instalador también se puede bajar del repositorio con **Code → Download ZIP**. El archivo `.plugin` queda como alternativa, sin actualizaciones.

## 0.1.5 (2026-11-21)

- **Catálogo de piezas** (`/catalogo` y `catalogo.py`): `catalogo.html` en la carpeta de trabajo muestra todas las piezas con su vista (o la foto real, si la mandaste), medidas, material, tiempo, gramos, costo, precio, estado y enlaces a sus archivos, ordenadas por mes, con buscador y filtros. Se actualiza solo cuando `/pieza`, `/diseno` o `/publicar` guardan algo, y "armá el catálogo" suma las piezas que ya tenías. El índice queda en `taller-3d/catalogo.json`.
- La página funciona sin internet y escapa todo lo que muestra; los enlaces a la tienda solo se aceptan con `http` o `https`.
- 46 pruebas automáticas.

## 0.1.4 (2026-11-21)

- **Licencia GNU AGPL 3.0** (`LICENSE`), con encabezado de licencia en cada script y `AVISOS-DE-TERCEROS.md`, que detalla qué sale de OrcaSlicer (el catálogo de parámetros) y las licencias de lo que usa o instala el taller.
- **Listo para GitHub:** `.claude-plugin/marketplace.json` convierte el repositorio en un marketplace; el README explica cómo sumarlo desde Claude, desde Claude Code o con el archivo.
- Contacto por GitHub (Issues y reporte privado de seguridad); el mail del autor ya no figura en el plugin.
- **Los instaladores revisan, antes de cambiar nada, que la PC alcance:** sistema, procesador, memoria (4 GB mínimo, 8 GB recomendado), placa de video (OpenGL 3.3 en Linux; en Windows, driver, máquina virtual o placa vieja), disco libre, internet y, en Windows, permisos para instalar. Si algo no alcanza, se detienen sin tocar nada; si alcanza justo, avisan.
- Linux: el AppImage de Orca necesita `fusermount` (paquete `fuse3`); si falta, el instalador lo ofrece, y si no se instala, Orca abre extrayéndose (más lento).
- **Los instaladores preguntan dónde guardar tus archivos** (Enter = `Documentos/Taller 3D`); si ya habías instalado, usan la misma carpeta. `/instalar` pregunta lo mismo.

### Correcciones de seguridad (revisión independiente)

- **Bloqueos que se podían esquivar:**
  - `device_commit_files` con `fileUuid` en lugar de `stagedPath` pasaba sin revisión. Ahora los G-code, proyectos y perfiles tienen que ir con `stagedPath`, y si el archivo no se puede leer o revisar, no se escribe (falla cerrado).
  - La revisión del G-code leía mal líneas que el firmware sí ejecuta: con número de línea y suma de control (`N10 M104 S400*45`), con los parámetros pegados (`M104S400`, `M302P1`) o con la letra repetida. Ahora las lee igual que el firmware. Se suman M149, M301, M304, G92 Z y M221 por encima del 200 % (rechazo), y M81 y M221 por encima del 120 % (aviso).
  - En los perfiles, una temperatura con un espacio al final (`"400 "`) no se controlaba. Ahora sí, y también las de espera, purga y torre. El G-code de adentro del perfil (inicio, fin, cambio de capa o de filamento) pasa por la misma revisión que el laminado.
- **Más cobertura del bloqueo automático:**
  - `Write`, `Edit` y `MultiEdit` (Claude Code), y `device_bash` en la PC.
  - Más extensiones: `.g`, `.gc`, proyectos `.3mf` y `.gcode.3mf`. El G-code binario (`.bgcode`) se rechaza, porque no se puede leer.
  - Rutas con `..`, los perfiles que vienen con Orca, `orca_plugins` y `OrcaSlicer.conf`.
  - Escribir, mover o borrar en la carpeta de Orca desde la terminal.
  - Más formas de subir archivos: `curl -sF`, rclone, lftp, nube y otras. `ftp` en el medio de otra palabra ya no da falso positivo.
- **Desinstaladores:**
  - Linux: las confirmaciones leían líneas de la lista de lo instalado. Solo se quita lo que está dentro de tu carpeta personal; sin papelera, va a una carpeta en tu casa. Se toleran configuraciones de la app con `mcpServers` vacío.
  - Windows: los datos de Orca se copian de vuelta antes de sacar la unión, y si algo falla queda como estaba. Al instalar, si no se puede crear la unión, se devuelve la carpeta. Solo se deshacen las entradas conocidas, y nada fuera de su lugar.
- **Instaladores:**
  - Ya no se cortan en silencio cuando falta OpenGL o `ldconfig`. Si algo falla a mitad de camino, avisan qué quedó y cómo deshacerlo.
  - El lanzador acepta rutas con espacios, comillas o `$`. Con Orca de Flatpak, los temporales de orca-mcp van a una carpeta que el Flatpak ve.
  - Antes de tocar la configuración se espera a que la app de Claude esté cerrada, reconocida por su ruta y no por el nombre, que comparte con Claude Code. En Windows, la app de la Tienda que todavía lee la configuración de la clásica parte de una copia de esa.
  - El registro de Windows se lee clave por clave. El instalador de Orca ya no espera a que cierres Orca. Las opciones sin valor dan un error claro.
- `SECURITY.md` dice con precisión qué se verifica con huella y qué no (orca-mcp viene de PyPI en versión fija, sin huella propia).
- Los datos que salen de OrcaSlicer llevan su aviso de origen y fecha de modificación.
- 45 pruebas automáticas.

## 0.1.3 (2026-11-21)

- **Instalador para Windows** (`instalar-windows.bat` + `instalar.ps1`, y su desinstalador): OrcaSlicer 2.5.1 oficial x64 o ARM64 con huella SHA-256 y firma digital verificadas, orca-mcp con uv (bajado y verificado si hace falta), carpeta de trabajo, entrada en la app de Claude con respaldo, modo prueba, registro y lista de lo instalado. Revisado con PowerShell 7 (sintaxis, compatibilidad con Windows PowerShell 5.1 y funciones); falta probarlo en una PC con Windows.
- En Windows, la app de Claude (MSIX) no puede crear archivos dentro de AppData que Orca vea: el instalador ofrece mover los datos de Orca a `C:\Users\<usuario>\OrcaSlicer` con una unión de carpetas, y el desinstalador los devuelve.
- Los dos instaladores **revisan primero qué hay** y saltean lo que ya está. Usan el Orca que ya tengas (AppImage, Flatpak, del sistema, instalado, portable o en un contenedor) y preguntan la ruta si no lo encuentran (`--orca` / `-Orca`). El de Linux avisa si corre en WSL y, con Orca de Flatpak, ofrece darle acceso solo a la carpeta de trabajo.
- La entrada de orca-mcp ahora indica también la carpeta de datos de Orca (`ORCASLICER_CONFIG_DIR`).
- **`/diseno`:** pedidos de solo diseño paramétrico (STL, `pieza.py`, vista y `parametros.md`), sin laminar y sin necesitar la PC. `revisar_stl.py --impresora ninguna` revisa la malla sin impresora.
- **Publicación en paralelo:** al terminar una pieza, `/pieza` ofrece armar el borrador de la tienda en el momento, con imagen ilustrativa (`vista_previa.py --producto --color`) hasta tener la foto real. Se aprueba también desde el celular.
- **Plugins de Orca:** guía (`references/plugins-orca.md`) con los que sirven al taller y sus riesgos; ante pedidos como llaveros, carteles o floreros, Claude busca en el Plugin Hub y los sugiere, sin instalarlos.
- **Novedades de Orca** (`novedades_orca.py`): después de cada laminado compara el Orca del usuario con las 750 claves de la 2.5.1; una vez por mes recuerda revisar versiones y plugins nuevos; detecta claves viejas en perfiles y perfiles TEST o AUTO que sobran. Lo aprendido queda en `taller-3d/novedades-orca.json`.
- Seguridad: los perfiles que escribe Claude no pueden llevar scripts de posprocesado ni plugins (`post_process`, `plugins`, `slicing_pipeline_plugin`), porque Orca los ejecuta al laminar; al copiar un perfil base se quitan y se avisa.
- El bloqueo automático también revisa perfiles en rutas de Windows y de Orca portable (`data_dir`).
- 34 pruebas automáticas.

## 0.1.2 (2026-11-21)

- Manual de uso (`MANUAL.md`): cómo pedir una pieza, ejemplos, el circuito completo, qué decide el usuario, dónde quedan los archivos y preguntas frecuentes.
- Comando `/ayuda`, que explica el taller a partir del manual.
- `/publicar` revisa la licencia de los modelos bajados de internet antes de cargarlos a la venta.

## 0.1.1 (2026-11-21)

- Contacto del autor y de seguridad (README, SECURITY.md y plugin.json).

## 0.1.0 (2026-11-21)

Primera versión.

- Skills: `impresion-3d` (conocimiento y reglas), `/pieza`, `/calibrar`, `/impresoras`, `/publicar`, `/instalar`, `/restaurar`.
- Scripts: CAD por código (`cad.py`), revisión de mallas (`revisar_stl.py`), vista previa (`vista_previa.py`), perfiles de Orca validados contra el catálogo (`perfil_orca.py`), revisión de seguridad de G-code con costo (`revisar_gcode.py`) y ficha de producto para tiendas (`producto_tienda.py`).
- Catálogo de los 1015 parámetros de OrcaSlicer 2.5.1 en español.
- Datos de la Creality Ender-3 V3 Plus y rangos de materiales.
- Bloqueos automáticos de seguridad (hooks).
- Instalador y desinstalador para Linux con versiones fijas y verificación SHA-256.
- 29 pruebas automáticas de los scripts y del guardia.
- Probado de punta a punta en una Ender-3 V3 Plus real: modelo, perfiles AUTO, laminado con orca-mcp y revisión APROBADA.
- Por línea de comandos Orca ignora el tipo de cama del proceso y usa "Cool Plate": el `AUTO filamento` copia las temperaturas de la cama real (`perfil_orca.py --cama`) y `revisar_gcode.py --cama-primera-capa` lo verifica.
