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
- Cada tanda competitiva procesa como maximo tres preguntas nuevas.
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
- `PARSER_MODEL`
- `RESEARCH_MODEL`
- `PREDICTIONS_PER_RESEARCH_REPORT` (inicial: `2`)
- `RESEARCH_REPORTS_PER_QUESTION` (inicial: `1`)
- `MAX_QUESTIONS_PER_RUN` (inicial: `3`)

No se compra credito propio durante la validacion sin una decision expresa.

## Criterio de corte

La MiniBench actual sirve como prueba tecnica por el ingreso tardio. En las dos
proximas rondas completas, el bot debe lograr al menos una posicion dentro del
20% superior. Si ambas quedan por debajo de la mediana, se detiene. Si queda
entre la mediana y el 20% superior, se permite una tercera ronda. Solo se escala
el gasto si alcanza el 20% superior o una estimacion de premio de USD 50.
