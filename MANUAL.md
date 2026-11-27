# Manual de uso de taller-3d

Cómo pedirle una pieza a Claude y qué pasa desde que la pedís hasta que la imprimís.

## Antes de empezar (una sola vez)

1. Sumá el plugin desde el menú de **Claude Desktop**, la app de escritorio, con la dirección de GitHub `noamix/Taller-3d-printaia` (no se hace desde el chat), e instalá lo necesario en tu PC (ver [INSTALACION.md](INSTALACION.md)).
2. En Claude escribí `/taller-3d:instalar`: revisa que todo ande, te pregunta en qué impresora de tu Orca querés trabajar, investiga sus datos oficiales (también cuánto consume) y la configura, y hace una pieza de prueba.
3. La primera vez te pide que leas el [aviso de uso](DISCLAIMER.md) y escribas ACEPTO.

La PC tiene que estar prendida y con la app de Claude abierta, porque ahí están tu Orca y tus carpetas. Con eso, podés pedir piezas desde la PC o desde el celular.

## Tres maneras de pedir

| Querés… | Pedilo así | Qué recibís |
|---|---|---|
| **Solo el diseño** (lo imprimís en otro lado, lo mandás a un servicio o querés el archivo) | "Diseñame…", "necesito el STL de…", `/taller-3d:diseno` | Modelo paramétrico: STL, archivo editable con las medidas arriba y una vista. No hace falta la PC. |
| **La pieza lista para imprimir** en tu impresora | "Haceme…", "imprimime…", `/taller-3d:pieza` | Todo lo anterior más la configuración, el G-code revisado y el costo. |
| **La pieza y su publicación** en tu tienda | "…y publicala", o decí que sí cuando Claude te lo ofrece | Además, el borrador del producto con fotos, descripción y el precio con el margen que elijas. |

Si no queda claro cuál querés, Claude te lo pregunta una sola vez.

## Cómo pedir una pieza

Escribí qué necesitás con tus palabras, como se lo pedirías a alguien que sabe imprimir. Cuanto más claro el pedido, menos preguntas y mejor resultado.

Un buen pedido dice:

- **Qué es y para qué sirve:** "un soporte para colgar el router en la pared".
- **Las medidas que importan:** tomalas con calibre si la pieza tiene que encastrar en algo.
- **Dónde va a estar:** adentro, al sol, cerca de una fuente de calor o en contacto con agua.
- **Cuánto esfuerzo hace:** "sostiene 600 g", "se abre y se cierra todos los días".
- **Material y color,** si tenés preferencia.
- **Fotos o un dibujo,** si ayudan, con una regla al lado.

### Ejemplos

- "Haceme un soporte para colgar el router en la pared. El router mide 250 × 180 × 40 mm y pesa 600 g. En PETG negro, con dos agujeros para tornillos de 4 mm."
- "Necesito una tapa a presión para un tarro. El borde mide 82,5 mm de diámetro por fuera (medido con calibre). Que no se salga sola."
- "Se rompió esta traba de la persiana (te mando foto con regla). Mide 40 × 12 mm y el agujero es de 6 mm. Va al sol."
- "Te paso este STL que bajé de Printables. Es decorativo: quiero que quede lo más lindo posible."
- "Imprimime 10 separadores de 10 mm de alto para tornillos M3."
- "Diseñame un organizador para cajón de 3 divisiones, 300 × 120 × 50 mm. Solo el STL, que lo imprimo en un servicio. Que pueda cambiar la cantidad de divisiones."
- "Quiero hacer llaveros con nombre para vender." Si hay un plugin de Orca que lo hace, Claude te lo sugiere (y te dice de quién es y qué riesgos tiene); si preferís, lo diseña él.
- "Te mando la foto de esta máscara: quiero una copia de 18 cm y un soporte para ponerla en la mesa." El modelo de la máscara lo genera una IA desde la foto (ver abajo) y el soporte lo diseña Claude a medida de la máscara.

También podés escribir `/taller-3d:pieza` y Claude te guía.

### Pieza desde una foto

Para copiar algo que existe (una máscara, una figura, una escultura, un adorno), adjuntá la foto y decí de qué tamaño la querés. El modelo 3D lo genera **Hunyuan 3D** de Tencent con tu cuenta, desde tu Chrome: Claude sube la foto, espera unos minutos, baja el STL, lo lleva al tamaño que pediste, le engrosa las paredes si salió hueco y fino, y te lo muestra diciéndote qué copió bien y qué no.

- **Más fotos, mejor:** si podés, mandá varias del mismo objeto (frente, costados y atrás), con fondo liso y buena luz. Si tenés una sola, el dorso lo inventa la IA; si querés, Claude puede generar las otras vistas con Nano Banana (Gemini o Flow) y te las muestra antes de usarlas.
- **Sin foto:** si pedís algo por cómo se ve que no sale bien con Blender (una persona, un animal con detalle), Claude genera primero una imagen con tu Gemini o tu Flow, la aprobás y recién ahí la pasa a 3D.
- **Lo que gasta:** cada modelo usa puntos de tu cuenta de Hunyuan, que tiene un cupo por día, y cada imagen usa del cupo de Gemini o Flow. Claude te avisa antes.
- **Lo que necesitás:** tu cuenta de Hunyuan 3D con la sesión abierta en Chrome (entrar y los captchas los hacés vos) y, en Chrome, apagado "Preguntar dónde guardar cada archivo" (Configuración → Descargas), para que los modelos se bajen solos.
- **Con algo diseñado al lado** (un soporte, una base con nombre): Claude te dice antes qué parte hace cada herramienta. La parte diseñada se mide sobre el modelo generado: por ejemplo, la base trae un hueco con la forma exacta del borde de la máscara. Por defecto van separadas, así cada una se imprime en su mejor posición.
- **Para vender:** confirmá que podés vender lo que generó Hunyuan (sus términos de uso) y que el objeto de la foto no es de otro.

### Pieza desde un STL que ya tenés

Si ya tenés el modelo (lo hiciste vos, te lo pasaron o lo bajaste), no hace falta diseñar nada: adjuntá el `.stl` en el chat, o decile a Claude en qué carpeta está, y pedí «dejame este STL listo para imprimir». En el panel está el botón **Pieza desde un STL**. Claude lo revisa (que esté cerrado, cuánto mide, si entra en tu impresora), elige cómo apoyarlo en la cama y te lo muestra antes de seguir. Después hace lo mismo que con una pieza diseñada: la configuración, el G-code revisado, el proyecto de Orca, el costo y, si querés, la publicación.

Te va a preguntar si el modelo es tuyo o bajado. Imprimir para vos un modelo bajado no tiene vueltas; para **venderlo** la licencia tiene que permitir uso comercial. Por ahora solo STL: un `.3mf`, `.obj` o `.step` hay que exportarlo como STL (en Orca, clic derecho sobre la pieza → Exportar como STL).

### Si no sabés algo

No pasa nada: Claude te pregunta lo que falta. Lo único que no inventa son las medidas: si una importa y no la sabés, te va a pedir que la midas.

## El circuito

```
 1. Pedido (texto, foto, medidas o STL)
        ↓
 2. Preguntas rápidas (uso, lugar, material, prioridad, medidas)
        ↓
 3. Diseño + vista previa ── ¿la aprobás? ── no → cambios y otra vista
        │                      (si hay un plugin de Orca que lo hace, te lo sugiere)
        ├── ¿solo el diseño? → STL + archivo editable y listo (/taller-3d:diseno)
        ↓ sí, para imprimir
 4. Configuración según el uso (perfiles de trabajo AUTO)
        ↓
 5. Laminado en tu Orca ⇄ ajustes (hasta 3 vueltas)
        ↓
 6. Revisión de seguridad ── no pasa → se corrige; no se entrega
        ↓ pasa
 7. Entrega en tu carpeta (G-code, modelo, vista, informe, costo real)
        ├── en paralelo, si tenés tienda: borrador de la publicación
        │   (fotos de producto, descripción, el margen que elegís) → lo aprobás vos
        ↓
 8. Imprimís vos (USB o app de la impresora)
        ↓
 9. Contás cómo salió → Claude ajusta y aprende
        ↓
10. Foto real de la pieza → va primera en la publicación
    y publicás el producto cuando quieras
```

### Paso a paso

1. **Pedido.** Texto, foto, medidas o un STL que ya tengas.
2. **Preguntas rápidas,** con opciones para tocar: en qué impresora (si en tu Orca tenés más de una y no lo dijiste, aunque en el taller haya una sola preparada; la más conveniente aparece primera, y si elegís una que todavía no está preparada, Claude la prepara antes), para qué es, dónde va, qué material y qué priorizás (calidad, resistencia, velocidad o ahorro de material). Además, las medidas que falten. La impresora se elige antes que nada porque de ella depende todo lo demás: si entra, los ajustes, el tiempo y el costo.
3. **Diseño y vista previa.** Claude diseña la pieza con medidas exactas y te muestra una imagen con cuatro vistas y las medidas. Si es decorativa (una figura, algo con texto o con formas suaves), la hace en Blender y te muestra además una foto renderizada; si es algo conocido, antes te muestra modelos que ya existen, con su licencia. **Vos la aprobás** o pedís cambios ("más alta", "agujeros de 5 mm", "redondeá los bordes"). Si trajiste un STL, revisa que esté sano y que entre en la cama.
4. **Configuración.** Elige los ajustes según el uso: paredes, relleno, velocidades, temperaturas, soportes y orientación. Los guarda en dos perfiles de trabajo llamados "AUTO". **Tus perfiles no se tocan.**
5. **Laminado.** Lamina en tu Orca y mira el resultado: tiempo, gramos, voladizos y temperaturas. Si algo no cierra, ajusta y vuelve a laminar, hasta tres veces antes de consultarte.
6. **Revisión de seguridad.** Revisa el G-code: temperaturas, que no salga de la cama, que no tenga comandos que cambien la configuración de la impresora y que apague todo al terminar. **Si no pasa, no se entrega.**
7. **Entrega.** Deja todo en una carpeta con el nombre de la pieza y de la impresora (te deja un enlace para ir directo a la carpeta y otro al `.3mf`), y te resume tiempo, gramos, costo real (con lo que cargaste; si falta algo, te dice qué), las decisiones con el porqué y qué mirar durante la impresión. **Para verla o tocarla en Orca, abrí el proyecto (`.3mf`) con doble clic:** se abre con tu impresora, el filamento, el proceso AUTO y tu tipo de cama ya elegidos. Si Claude tiene terminal en tu PC, te pregunta si querés que te abra Orca con la pieza.
   **En paralelo, la publicación:** si tenés tienda configurada, Claude te ofrece armar el producto en ese momento: fotos de producto hechas con Blender desde cuatro ángulos (la primera con fondo blanco, como pide Mercado Libre; si tenés el conector de Blender en la app de Claude, se hacen en tu PC, más rápido), la descripción y el precio con el tiempo y los gramos reales. **Te pregunta qué margen querés en ese producto**, con tres opciones y lo que ganás en cada canal, o le decís un precio. El texto de venta lo puede escribir tu Gemini gratis (Claude lo revisa contra los datos de la pieza) o Claude. Antes de cargarlo te muestra una **vista previa** de cómo se vería la página del producto en tu tienda, con lo que conviene revisar: si las fotos son ilustrativas, el título para Mercado Libre, el precio y la ganancia en cada canal. Lo aprobás vos con el botón de la vista previa o en el chat, también desde la app de Claude en el celular, y queda como borrador.
8. **Imprimís vos.** Pasás el G-code a la impresora (por USB o con la app de la marca) y la arrancás desde ahí. **Claude nunca arranca una impresión.** Mirá la primera capa completa y no dejes la impresora sola.
9. **Contale cómo salió.** Mandale una foto, aunque haya salido bien. Si algo falló, lo diagnostica y lo corrige. Lo que funcionó queda anotado y mejora las próximas piezas.
10. **Vender.** Cuando tengas la pieza impresa, mandale la foto: la suma al producto como imagen principal (las fotos de Blender son ilustrativas). El borrador lo publicás vos desde tu tienda. Si no lo armaste antes, `/taller-3d:publicar` lo hace en cualquier momento, también sin imprimirla (o el botón «Publicar» del panel).

## Qué decidís vos

- Aprobar el diseño antes de laminar.
- El material y la prioridad.
- Cualquier cambio en tus propios perfiles de Orca (siempre con respaldo).
- Arrancar la impresión.
- El margen de cada producto (o su precio).
- Publicar el producto: queda en borrador hasta que lo publiques vos.
- Instalar plugins de Orca: Claude solo los sugiere.

## Cargar productos en tu tienda (WooCommerce)

Si vendés en una tienda WooCommerce (WordPress), el botón «Cargala como borrador» del panel (o pedírselo a Claude) carga el producto directo en tu tienda, con título, textos, precio, peso, medidas y fotos, **siempre como borrador**: lo revisás y lo publicás vos desde la tienda. Si ya está publicado, no lo toca. Cada vez que trabajás con Claude, el conector mira (sin cambiar nada) qué productos del panel ya publicaste y lo anota.

Se conecta una sola vez, con el instalador del taller en Linux y Windows (en macOS, a mano). La guía completa, con lo que necesita tu tienda y qué hacer si algo falla, es [TIENDA-WOOCOMMERCE.md](TIENDA-WOOCOMMERCE.md). En corto:
1. En tu WordPress: **Usuarios → Perfil → Contraseñas de aplicación**, nombre «Taller 3D» → **Añadir**. Copiá la contraseña: WordPress la muestra una sola vez.
2. Corré el instalador (Linux: `bash instalar.sh` en una terminal; Windows: doble clic en `instalar-windows.bat`). En «Cargar productos en tu tienda» contestá **s**: primero revisa tu tienda y después te pide la dirección, tu usuario y la contraseña (pegala: no se ve al escribirla). En «Conexión con la app de Claude» contestá **s** y cerrá la app del todo cuando te lo pida.
3. Abrí la app de Claude y preguntá «¿está conectada mi tienda?».

La contraseña no pasa por el chat: queda en tu PC, en un archivo que solo lee tu usuario. Para cambiarla o conectar otra tienda: `python3 ~/.local/share/taller-3d/tienda_mcp.py configurar` (Windows: `conectar-tienda.bat`); para ver si anda: `… tienda_mcp.py probar`. Para desconectarla, revocá la contraseña en WordPress (el desinstalador también borra la conexión de tu PC).

## Dónde quedan tus archivos

En tu carpeta de trabajo, que es siempre **`Taller 3D` dentro de tus documentos** (`Documentos/Taller 3D`; en Windows, `Documentos\Taller 3D`). Todas las piezas van ahí, una carpeta por pieza dentro de `impresiones`. Si tenías un taller en otra carpeta (de antes de la versión 0.1.34), pedile a Claude que lo mude: "mudá mi taller a Taller 3D".

```
panel.html              el panel del taller: tus ideas y piezas y en qué paso está cada una (doble clic)
impresiones/2026-11-21_soporte-router_ender-3-v3-plus/
    soporte-router_ender-3-v3-plus.gcode   lo que se imprime (solo en esa impresora)
    soporte-router_ender-3-v3-plus.3mf     el proyecto de Orca: abrilo con doble clic
    pieza.py            modelo editable (las medidas están arriba de todo)
    pieza.stl           el modelo
    vista.png           la vista previa
    informe.md          tiempo, gramos, costo, decisiones y qué mirar
    producto/           la publicación: fotos de producto, ficha, precio y vista-previa.html
    config_usada.json   configuración usada y por qué
    laminado/           las vueltas de prueba de Orca (se pueden borrar)
disenos/2026-11-21_organizador/
    pieza.py, pieza.stl, vista.png, parametros.md   pedidos de solo diseño
respaldos/              copias de lo que se cambió
calibraciones/          resultados de calibración por filamento
taller-3d/              tu configuración, el historial, el índice del panel, los aprendizajes y las novedades de tu Orca
```

## El panel del taller

`panel.html`, en tu carpeta de trabajo, es tu administrador: abrilo con doble clic (conviene guardarlo como favorito del navegador). Cada idea y cada pieza es una tarjeta con su recorrido:

```
Idea → Diseño → Lista para imprimir → Impresa → En la tienda
```

- Arriba, cuántas ideas están **pendientes**, cuántas piezas **en proceso** y cuántas **terminadas**, con filtros y un buscador.
- Primero va **"Para hacer"** (lo más avanzado primero) y después las terminadas, por mes.
- Cada tarjeta dice **a quién le toca lo que sigue**: "Le toca a Claude: dejarla lista para imprimir" o "Te toca: imprimirla". Tiene botones con el pedido ("Diseñala", "Ya la imprimí", "Publicar"…), para qué impresora es, la vista (o la foto de la pieza impresa), medidas, material, tiempo, gramos, costo, precio y los archivos.
- **Publicar, impresa o no:** el botón «Publicar» está en cada pieza con modelo, la hayas impreso o no (hay productos que sabés que andan, o un STL que ya probaste), hasta que la pieza está en tu tienda. Si no está laminada, Claude la lamina primero, solo para sacar el tiempo, los gramos y el costo. Con la publicación ya armada, «Publicar» la carga en tu tienda como borrador (lo mismo que «Cargala como borrador» de Publicaciones). La publicación lleva fotos de producto hechas en la computadora, aclaradas como ilustrativas; ves cómo queda antes de que se cargue, se carga como borrador y la publicás vos.
- **Publicaciones:** las piezas a las que les armaste la publicación, con su foto, su precio, lo que ganás y dónde está cada una (vista previa, borrador en la tienda o publicada). «Ver cómo queda» abre la página del producto como se vería en tu tienda. Cuando publicás un producto en tu tienda (o lo volvés a borrador), el panel se entera solo la próxima vez que trabajás con Claude, si tenés el conector de la tienda; si lo mandaste a la papelera o lo borraste, Claude te pregunta si lo saca del panel.
- **Tu taller:** arriba, lo que falta para que los costos y precios sean reales (la boleta de luz, cuánto pagaste la impresora, tu hora…), con un botón para cada cosa. El consumo de cada impresora no te lo pide: Claude lo busca en internet o, si no lo encuentra, lo estima por el tamaño de la cama, y lo guarda solo (si medís el real con un medidor de enchufe, pasáselo en el chat).
- **Imprimir en:** arriba elegís la impresora para lo que pidas: las de tu Orca, también las que todavía no están preparadas en el taller, o "Que me pregunte Claude". Los botones que arrancan una pieza ("Diseñala", "Dejala lista para imprimir", "Pieza desde una foto", "Pieza desde un STL", y "Publicar" en una pieza sin laminar) se la dicen a Claude, y el navegador se acuerda de la que elegiste. La que elegís en la ventana de Orca no le llega a Claude.
- En el archivo, los botones copian el pedido para que lo pegues en el chat.
- **Borrar:** cada tarjeta tiene «Borrar», para sacar una pieza con todo lo guardado (su carpeta entera: modelo, G-code, proyecto de Orca, fotos y publicación) o una idea. El botón no borra: Claude te muestra qué se borra (cuántos archivos y cuánto ocupa, y si está en tu tienda) y te pide confirmación. Con tu sí, la carpeta va a la papelera de tu PC, así que la recuperás desde ahí hasta que la vacíes, y la pieza sale del panel. El producto de la tienda no se toca: si lo querés sacar, lo pasás a borrador o a la papelera desde tu tienda. Por ahora la papelera la maneja Claude solo en Linux; en Windows y macOS te da el enlace a la carpeta para que la borres vos.
- **Ideas para después:** contale a Claude "anotá esta idea: un soporte para la tele, 15 × 10 cm" y queda pendiente con lo que ya se sabe. Cuando la quieras hacer, pedila por su nombre.
- **Pieza desde una foto:** el botón de arriba manda el pedido a Claude (o lo copia) y te recuerda adjuntar la foto en el chat: la página no puede mandar fotos.
- Al empezar a usar el taller, Claude te dice en una línea qué tenés pendiente.

Se actualiza solo cada vez que Claude anota una idea o guarda, lamina o publica una pieza. Una pieza impresa ya está terminada: publicarla es opcional. Una publicada en tu tienda también, aunque no la hayas impreso: el G-code queda listo para cuando te la compren. Si tenías piezas de antes, pedí "armá el panel" y las suma.

### El panel al costado del chat

En claude.ai y en la app de Claude, el panel también puede estar **al costado del chat**: Claude lo publica en tu cuenta (es privado: lo ves solo vos) y se actualiza solo. La primera vez te pregunta si lo querés.

Ahí **los botones le mandan el pedido directo a Claude**: tocás "Ya la imprimí" o "Publicar" y le llega a la conversación que publicó el panel, que lo hace y te contesta. Si en ese momento Claude está trabajando en otra cosa, lo hace cuando termina. Si la página no puede mandarlo (por ejemplo, desde una conversación que ya no está), el botón copia el pedido para que lo pegues en el chat.

### La guía

- Al empezar sin un pedido concreto ("hola", "¿qué hacemos?"), Claude te ofrece opciones para tocar con lo que sigue: la pieza que tenés para imprimir, una idea anotada, lo que falta configurar o algo nuevo.
- Mientras hace una pieza, ves las etapas en la lista de tareas (entender, modelo, configuración, laminar y revisar, entregar).
- Cada vez que te toca hacer algo, termina con **"Te toca: …"**: qué hacer y cómo.

## Cambiar una pieza ya hecha

Pedilo con tus palabras: "Hacé el soporte del router 1 cm más ancho" o "el agujero salió justo, agrandalo 0,2 mm". Claude edita el modelo, vuelve a laminar y lo revisa. Si sabés algo de programación, también podés cambiar las medidas en `pieza.py`.

## Otros pedidos

Los comandos llevan el nombre del plugin adelante (`/taller-3d:...`): si escribís `/pieza` a secas, no corre. Con tus palabras también funciona.

| Para… | Decí o usá |
|---|---|
| Solo el diseño, sin imprimir | `/taller-3d:diseno` o "necesito el STL de…" |
| Calibrar un rollo nuevo | `/taller-3d:calibrar` o "calibrá el PETG nuevo" |
| Trabajar con otra impresora | `/taller-3d:impresoras`, o decilo en el pedido ("en la Bambu") |
| Vender una pieza | `/taller-3d:publicar` |
| Ver tus ideas y piezas y qué sigue en cada una | `/taller-3d:panel` o "¿qué tengo pendiente?" |
| Anotar una idea para más adelante | "Anotá esta idea: …" |
| Volver atrás un cambio de perfil | `/taller-3d:restaurar` |
| Revisar que todo ande | `/taller-3d:instalar` |
| Una duda de configuración | "¿Qué es la costura en bisel?", "¿por qué salen hilos?" |
| Volver a ver este manual | `/taller-3d:ayuda` |

## Lo que el taller no hace (todavía)

- No arranca impresiones ni controla la impresora.
- No garantiza piezas para uso médico, de seguridad o en contacto con alimentos.
- Para figuras, formas orgánicas o texto en relieve necesita Blender, un plugin de Orca, un modelo existente o generarlo por IA desde una foto (con tu cuenta de Hunyuan 3D): el diseño por código es para piezas funcionales.
- Lo que la IA genera desde una sola foto de frente pierde los detalles finos grabados (quedan en el color, no en el relieve) y el dorso es inventado.
- No imprime roscas: usa tornillos pasantes, tuercas o insertos de latón.
- Un encastre muy justo puede necesitar una prueba. Si calibrás la tolerancia con `/taller-3d:calibrar`, acierta más a la primera.

## Preguntas frecuentes

**¿Puedo pedir desde el celular?** Sí, con la PC prendida y la app de Claude abierta en la PC.

**¿Necesito la PC para un diseño?** No. Con `/taller-3d:diseno` Claude te manda el STL y el archivo editable por el chat. La PC hace falta para laminar y para dejar los archivos en tu carpeta.

**¿Se entera de las novedades de Orca?** Sí. Después de cada laminado compara tu Orca con lo que conoce (parámetros nuevos o que ya no están) y una vez por mes revisa si salió una versión nueva o hay plugins útiles. Te avisa solo lo que te sirve; nunca instala ni actualiza nada solo.

**¿Puedo aprobar desde el celular?** Sí: la conversación es la misma en la PC y en la app de Claude del celular.

**¿Tengo que tener Orca abierto?** No. Si lo tenés abierto, cerralo y volvé a abrirlo para ver los perfiles nuevos; después abrí el proyecto `.3mf` de la pieza.

**Abrí el proyecto de una pieza vieja y Orca marca cambios (↺) en los perfiles AUTO. ¿Está mal?** No: los AUTO se rehacen en cada pieza, y el proyecto trae los ajustes con que se hizo esa. Si la volvés a laminar desde ahí, sale igual que la primera vez.

**El panel dice que tengo una impresora preparada, pero en Orca tengo otra elegida.** "Preparada" es la que el taller ya configuró en tu carpeta de trabajo (sus datos y sus perfiles AUTO). Lo que elegís en la ventana de Orca no le llega a Claude: elegí la impresora en "Imprimir en", arriba del panel, o decila en el pedido. Si todavía no está preparada, Claude la prepara la primera vez (unos minutos).

**¿Por qué la carpeta y el G-code dicen el nombre de la impresora?** Porque un G-code sirve solo para la impresora para la que se laminó: así no se confunde, ni en la PC ni en la pantalla de la impresora.

**¿Claude me puede abrir Orca?** Sí, en Linux, si corrés de nuevo el instalador del taller y aceptás el paso "Abrir Orca desde Claude y desde el panel" (después reiniciá la app de Claude). Así Claude te abre Orca con la pieza, y el botón "Abrila en Orca" del panel la abre directo (la primera vez la app te pide permiso). Si no está, tocá el enlace o abrí el `.3mf` con doble clic. Imprimir es siempre tuyo: Claude no usa la pestaña Dispositivo ni los botones Imprimir o Enviar.

**¿Gasta mi plan de Claude?** Sí: diseñar y ajustar consume uso de tu plan. Un pedido claro y con medidas ahorra vueltas.

**¿Cómo calcula el costo?** Suma el material (gramos de Orca × precio del kilo), la luz (el consumo de tu impresora × las horas, con el precio del kWh de tu boleta), el desgaste de la impresora (lo que la pagaste repartido en sus horas de vida), las que salen mal (10 % si no le decís otra cosa), tu tiempo y el embalaje. Si falta un dato, te dice cuál y la frase para dárselo.

**¿Cuándo usa Blender y cuándo código?** Depende de cómo se describe la pieza. Si se describe con medidas (un soporte, una caja, un adaptador), la hace por código, con medidas exactas. Si se describe por cómo se ve (una figura, un logo, texto, una forma suave), la hace en Blender o te ofrece un modelo que ya existe. Si tiene las dos cosas, hace cada parte con su herramienta y las une. No arma con esferas y cajas algo que tiene que verse bien: si el código no alcanza, te lo dice y cambia de herramienta. La revisión rechaza las partes que quedan sueltas en el aire. Personajes y marcas ajenas no los modela.

**¿Por qué la máscara que generó la IA vino hueca y Claude la engrosó?** Hunyuan suele devolver figuras como una cáscara de menos de 1 mm de pared, que se rompe o no se imprime bien. Claude la engrosa a 2 mm hacia adentro, así la cara de afuera, donde está el detalle, no cambia (te dice cuánto se movió: casi nada).

**¿De dónde saca cuánto consume mi impresora?** Lo busca en internet cuando preparás la impresora: el consumo promedio que publica el fabricante o una prueba medida del mismo modelo. Si la ficha solo dice la potencia ("350 W"), eso es el máximo calentando, no lo que gasta imprimiendo: lo estima por el tamaño de la cama y te avisa que es estimado. Te pregunta solo si no encuentra nada. Si tenés un medidor de enchufe, medí una impresión entera y pasale los kWh y las horas: es el mejor dato.

**¿Para qué quiere mi boleta de luz?** Para sacar lo que te cuesta de verdad cada kWh. Guarda solo los números de la tarifa (kWh, cargos, impuestos, período y empresa): nunca tu nombre, tu dirección ni tus números de cliente o de medidor.

**¿Cómo pone el precio?** Con tu margen **sobre el precio**: de cada venta, qué parte te queda después de las comisiones y los impuestos. Un 40 % quiere decir que de cada $ 1.000 te quedan $ 400 de ganancia. Ojo: un recargo del 50 % sobre el costo es un margen del 33 %, y «el doble del costo» (recargo del 100 %) es un margen del 50 %; un margen del 100 % no existe, porque el precio daría infinito. El precio sale por canal (tu tienda, Mercado Libre con su comisión e IVA…), y en cada producto elegís el margen o le decís un precio y te muestra cuánto ganás en cada canal.

**¿Cuenta los impuestos?** Sí, si le decís cómo facturás. Ingresos Brutos (y cualquier tasa que pagues como porcentaje de lo que vendés) se resta del precio igual que la comisión, así el margen que elegís es el que te queda de verdad. Si sos responsable inscripto, el precio sale con IVA incluido, la ganancia se calcula sin IVA y las compras con factura A (filamento, impresora, embalaje) entran sin IVA, porque lo descontás. Con monotributo, el precio es el final y la cuota mensual la cubre el margen. Las retenciones de Mercado Libre no se cuentan: son pagos a cuenta. Claude no da consejo impositivo: si dudás de tu situación, confirmala con tu contador.

**¿Puedo cobrar distinto las piezas chicas y las grandes?** Sí, si querés. Lo que hacen los servicios de impresión es un **precio mínimo por pieza** (así una pieza chiquita no se vende por monedas) y, a veces, otro margen según el tamaño. El taller tiene las dos cosas: un mínimo por pieza y márgenes por escalones según el costo de la pieza (por ejemplo, 60 % en las que cuestan hasta $ 5.000, 50 % hasta $ 20.000 y 40 % en las más caras). Se lo pedís a Claude y en cada producto igual podés elegir otro.

**¿Las fotos de producto son reales?** Son renders 3D de tu pieza, con el color y el tipo de plástico, para tener la publicación lista antes de imprimir. La descripción aclara que son ilustrativas; cuando la imprimas, mandale una foto real y va primera.

**¿Quién escribe el texto de la publicación?** Si en la instalación elegiste Gemini, lo escribe tu Gemini gratis, en el navegador y con tu cuenta de Google; si no, Claude. En los dos casos Claude lo revisa antes de usarlo: que no invente medidas ni usos, que no prometa cosas que no se pueden sostener (apto para alimentos, irrompible, garantías) y que el título entre en Mercado Libre. Las medidas, el material y los cuidados no los escribe ninguna IA: salen de los datos reales de la pieza. Si Gemini no está disponible, escribe Claude y te lo dice.

**¿Puedo vender piezas de modelos bajados de internet?** Solo si la licencia del modelo lo permite: muchos son de uso no comercial. Revisala antes de publicar.

**¿Y si la pieza sale mal?** Mandale una foto y contale qué pasó: lo diagnostica, corrige el perfil o el modelo y lo anota para la próxima.

**¿Qué pasa con mis perfiles de Orca?** Solo se reescriben los "AUTO". Los tuyos se cambian únicamente si lo aprobás, siempre con respaldo, y `/taller-3d:restaurar` los vuelve atrás.
