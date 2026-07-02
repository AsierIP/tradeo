# Director-Claw Chat Report Protocol

Director coordination happens in the ChatGPT project chat unless Asier explicitly
authorizes another channel for a specific task. Do not send Gmail reports for this
workflow.

Every report must contain only the new answer for the current task. Do not quote,
paste, summarize, or include prior thread history.

The first line must use this exact shape:

```text
AQUI CLAW - Tarea <ID> - Fase <fase> - Estado <OK/BLOCKED/NEEDS_DIRECTOR>
```

## A. Resumen ejecutivo

- Decision solicitada al Director.
- Resultado en una frase.
- Riesgo principal detectado.

## B. Repo y PR

- Base main SHA.
- Rama.
- Head commit SHA.
- PR URL or compare URL.
- Archivos tocados.
- Archivos NO tocados por seguridad.

## C. Cambios realizados

- Lista corta por archivo.
- Por que se hizo.
- Que queda fuera de scope.

## D. Validacion exacta

Use a table with:

| Comando | Exit code | Resultado | Tests |
| --- | ---: | --- | --- |

Include exact commands, exit codes, and concise outcomes. Do not paste large logs;
give paths or short summaries.

## E. Seguridad

Always include:

- live_allowed=false
- paper_allowed=false unless explicitly authorized by Asier/Director for the task
- orders_allowed=false
- order_code_changed=false, or explain exactly why order code changed
- gates_relaxed=false
- ibkr_readonly=true or not_checked
- paper_trades=0 or not_checked
- ib_fills=0 or not_checked
- kill_switch state if available
- execution_automation_flags_all_false=true

## F. Research Metrics

Only include when the task touches research:

- universe_file
- product_policy
- selected_count
- readiness status and coverage
- exact wave manifest
- windows, clusters, accepted, rejected, persisted_candidates
- top blockers
- top near-miss with OOS/PF/DD/cost/FDR/WRC/SPA
- proposed scientific decision

## G. Artifacts

- Concrete generated paths.
- Approximate sizes for large files.
- Hashes for audit artifacts when applicable.

## H. Bloqueos y decision requerida

- What could not be done.
- Why.
- Recommended next action.

## Standing Rules

- Use exact numbers, paths, and SHAs.
- Write `not_checked` for any field that was not verified.
- Do not mix a new report with old text.
- Do not paste long logs.
- Do not request or imply merge before Director evaluation.
