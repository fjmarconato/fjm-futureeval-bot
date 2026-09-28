# FJM FutureEval Bot - Operacion

## Objetivo

Operar un unico bot elegible en FutureEval y MiniBench sin intervencion humana
en los pronosticos activos. El objetivo economico es obtener al menos USD 80 por
temporada o un premio MiniBench de USD 50 cada dos meses.

## Controles

- `main.py` no publica por defecto. Publicar requiere `--publish`.
- Los secretos nunca se guardan en el repositorio.
- El workflow competitivo omite preguntas ya pronosticadas.
- Las preguntas y predicciones se ejecutan en serie para evitar bloqueos por
  rafagas desde las direcciones compartidas de GitHub Actions.
- Cada tanda competitiva procesa como maximo cinco preguntas nuevas entre
  FutureEval y MiniBench, no cinco por torneo.
- Un ciclo diario refresca hasta cinco pronosticos con
  al menos 72 horas de antiguedad, siempre despues de cubrir preguntas nuevas.
- Un monitor cada 30 minutos abre una incidencia en GitHub si no hubo una
  ejecucion exitosa en 45 minutos y la cierra cuando el bot se recupera.
- La cobertura normal se mantiene mediante dispatch encadenado cada ocho
  minutos despues de una ejecucion correcta. El cron de tres horas es solo un
  bootstrap de recuperacion porque GitHub puede demorar o descartar schedules.
- Toda publicacion programada depende de la variable
  `COMPETITIVE_AUTOMATION_ENABLED=true`; mantenerla en `false` durante el
  preflight.
- La publicacion manual o programada en `tournament` se rechaza antes de
  consultar Metaculus si `RESEARCH_MODEL` esta vacio o configurado como
  `no_research`/`None`. Primero probar un proveedor de investigacion con una
  ejecucion seca.
- Si `FORECAST_MODELS` declara varios modelos, la publicacion tambien exige al
  menos tantas predicciones por informe como modelos distintos; asi cada
  modelo aporta al forecast de cada pregunta.
- Con `RESEARCH_MODEL=smart-searcher/gemini/gemini-3.5-flash-lite`, el
  investigador usa Exa para una busqueda y cinco fuentes por pregunta. Si el
  informe falla o queda vacio, intenta `FALLBACK_RESEARCH_MODEL` una vez. Si
  ambos informes fallan, consulta Exa directamente con el texto de la pregunta
  y entrega fragmentos fechados y enlazados, sin inventar una sintesis.
  Requiere `EXA_API_KEY` como secreto; sin ella, la publicacion competitiva
  falla antes de llamar a Metaculus. El plan gratuito de Exa corta las
  solicitudes cuando se agota el credito mensual.
- Cada ejecucion del workflow registra modo, publicacion, limite de preguntas
  y modelos efectivos en el resumen de GitHub Actions; no registra secretos.
- En una ejecucion manual, `use_next_config` decide si se aplica esa
  configuracion y `max_questions` prevalece siempre. La fecha de activacion
  afecta solo a las ejecuciones programadas. Los overrides de investigacion,
  pronostico y parser afectan solo a esa ejecucion manual. El limite permitido
  es 1 a 5.
- Metaculus Cup queda manual porque los bots no son elegibles para premios alli.
- Cada ronda usa una version congelada del motor.
- Los cambios de calibracion se realizan entre rondas cerradas, no sobre
  preguntas activas vistas por una persona.

## Alta unica

1. Crear una cuenta personal en Metaculus y aceptar sus terminos.
2. En `Settings -> My Forecasting Bots`, crear un unico bot elegible.
3. Guardar su token como secreto GitHub `METACULUS_TOKEN`.
4. Solicitar los creditos patrocinados y guardar las credenciales recibidas
   como secretos, nunca como variables ni archivos.
5. Ejecutar manualmente `Test Bot` y comprobar los comentarios y pronosticos en
   `bot-testing-area`.
6. Habilitar el workflow competitivo solo despues de esa comprobacion.

## Modelos y presupuesto

Los modelos se configuran con variables GitHub para poder rotarlos sin tocar
secretos:

- `FORECAST_MODEL`
- `FALLBACK_FORECAST_MODEL` (lista ordenada separada por comas)
- `PARSER_MODEL`
- `RESEARCH_MODEL`
- `FALLBACK_RESEARCH_MODEL`
- `PREDICTIONS_PER_RESEARCH_REPORT` (actual: `1`)
- `RESEARCH_REPORTS_PER_QUESTION` (inicial: `1`)
- `MAX_QUESTIONS_PER_RUN` (limite: `1` a `5`)

La configuracion para Otono 2026 usa `gemini/gemini-3.6-flash` para
pronosticar, `gemini/gemini-3.5-flash-lite` para investigar con Exa y parsear,
`gemini/gemini-3.5-flash` como respaldo de investigacion, y
`gemini/gemini-3.8-flash,gemini/gemini-3.5-flash-lite` como respaldos ordenados
de pronostico. La clave de Google se guarda como secreto, no como variable del
repositorio.

El torneo competitivo debe usar el slug `fall-futureeval-2026` (proyecto
`33121`). El codigo rechaza explicitamente los identificadores de Verano 2026.
No se activa una temporada con `no_research`: esa configuracion queda limitada
a pruebas tecnicas mientras se renuevan AskNews o los creditos patrocinados.

Mientras la cuota siga en el nivel gratuito, cada pregunta usa una sola
estimacion. Ante un 429, 503 u otro error del modelo principal, se intenta
cada respaldo de pronostico en orden; los errores de una pregunta no cancelan
los resultados validos de las demas. No se activa un ensamble mayor sin cuota
verificada.

La configuracion competitiva objetivo, una vez recibida y probada la clave
patrocinada, es un ensamble de tres miembros: `openai/gpt-5.6-sol`,
`gemini/gemini-3.6-flash` y `openai/gpt-5.6-terra`. Se activa con
`FORECAST_MODELS` y `PREDICTIONS_PER_RESEARCH_REPORT=3`; no debe activarse sin
una prueba remota exitosa de cada proveedor.

Metaculus rechazo la solicitud de creditos LLM para Otono 2026. Un correo del
27 de septiembre de `ben@metaculus.com`, enviado y firmado por `metaculus.com`,
confirmo que el bot aun puede optar a premios. Esto confirma elegibilidad
potencial, no inscripcion efectiva en un leaderboard, puntaje ni cobro. El
ensamble patrocinado anterior queda pospuesto. El 27 de
septiembre se agrego `EXA_API_KEY` como secreto de GitHub en el plan gratuito
de Exa, sin medio de pago, con USD 20 de saldo inicial y USD 10 mensuales. Tres
ejecuciones secas (dos sobre FutureEval) confirmaron investigacion con Exa y
pronostico con Gemini 3.1 Flash-Lite; no publicaron nada. La prueba adicional
con Gemini 3.6 para investigacion fallo por un 503 transitorio antes de llamar
a Exa. El precio que muestra `forecasting-tools` es una estimacion de tarifa
paga, no una factura verificada.

El 28 de septiembre se comparo la huella SHA-256 de `GOOGLE_API_KEY` en
GitHub con las claves de Google AI Studio sin revelar sus valores. La
[verificacion #2](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36464446973)
confirmo que el secreto existente corresponde a `fede`, del proyecto
`My First Project`, que AI Studio muestra en nivel gratuito. No corresponde
a la clave del otro proyecto gratuito `Gemini API` ([verificacion #1](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36464274787)).
No se reemplazo el secreto ni se toco el proyecto de pospago. La cuota
gratuita puede agotarse o devolver errores; no contratar un plan pago ni
consumir saldo propio sin decision expresa.

La [prueba seca #1077](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36464575061)
del 28 de septiembre encontro cero preguntas elegibles en FutureEval y
MiniBench, por lo que no valido el recorrido completo. La
[prueba seca #1078](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36464819027)
en `bot-testing-area` encontro una pregunta y fuentes de Exa, pero fallo por
un `503` transitorio de Gemini 3.1 Flash-Lite al generar el informe de
investigacion. Ninguna prueba publico pronosticos.

La [prueba seca #1079](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36465708863)
completo el recorrido en `bot-testing-area` con investigacion Exa,
`gemini/gemini-3.5-flash-lite` para investigacion, pronostico y parser, y
`max_questions=1`. Produjo un pronostico numerico para una pregunta, sin
errores y con `publish=false`; no lo publico. Es una validacion tecnica, no
una medicion de rendimiento competitivo. El costo de USD 0.02227 por
pregunta indicado en el log es una estimacion de tarifa paga del paquete,
no un cargo verificado. La configuracion programada no cambio con estos
overrides manuales; FutureEval y MiniBench tenian cero preguntas elegibles
en la prueba #1077.

La [prueba seca #1085](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36498974488)
completo el recorrido de una pregunta en `bot-testing-area`: investigacion
con Exa y Gemini 3.5 Flash-Lite, pronostico con Gemini 3.8 Flash y cero
errores, con `publish=false`. Es una prueba de funcionamiento, no una
comparacion de puntaje entre modelos. La
[prueba seca #1086](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36499121630)
encontro cero preguntas elegibles tanto en FutureEval como en MiniBench. El
workflow de calidad #30 paso con el cambio de respaldo de investigacion. No
se publico ningun pronostico ni se habilito la automatizacion competitiva.

La [prueba seca #1087](https://github.com/fjmarconato/fjm-futureeval-bot/actions/runs/36499550637)
fallo antes de pronosticar: el primer investigador devolvio una consulta mal
formada y el segundo, un informe sin fuentes utiles. Por eso se agrego la
busqueda directa de Exa como tercer nivel. La prueba local de esa ruta usa
fuentes simuladas; falta confirmar la ruta con Exa real en GitHub Actions.

El 27 de septiembre se corrigio el workflow de calidad y paso su ejecucion
remota #23. La automatizacion competitiva permanece deshabilitada; no hay
evidencia de premio o dinero cobrado.

La prueba remota del 10 de agosto confirmo que `gemini/gemini-3.6-flash`
funciona. Google Search grounding devolvio `429 RESOURCE_EXHAUSTED` y el proxy
patrocinado de Metaculus no tenia allowance para `gpt-5` ni
`gpt-4o-search-preview`; por eso esas opciones quedan desactivadas.

## Criterio de corte

La MiniBench actual sirve como prueba tecnica por el ingreso tardio. En las dos
proximas rondas completas, el bot debe lograr al menos una posicion dentro del
20% superior. Si ambas quedan por debajo de la mediana, se detiene. Si queda
entre la mediana y el 20% superior, se permite una tercera ronda. Solo se escala
el gasto si alcanza el 20% superior o una estimacion de premio de USD 50.
