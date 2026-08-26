# FlexSim Integration Guide

This document explains, at a conceptual level, how a FlexSim 2027 model
should communicate with the `flexsim-digital-twin-bridge` Python service
running locally on `http://127.0.0.1:8000`.

No undocumented FlexSim functionality is assumed here. FlexSim 2027 is
understood to provide HTTP request capability and JSON handling utilities
in FlexScript; the exact function names are not guaranteed by this
document and must be confirmed against the official FlexSim 2027
reference manual. Where exact syntax cannot be guaranteed, examples are
clearly labeled as pseudo-code — see `flexsim_http_examples.txt` in this
folder.

## Integration workflow

FlexSim should perform the following steps, typically driven by periodic
triggers (e.g. a Timer object or a periodic Event/Listener) in the model:

1. **Serialize relevant model state to JSON.**
   Build a JSON object describing the current state of the objects you
   want to expose: queues (by content/count), processors (state and
   utilization), conveyors, sources, sinks, and AGVs/mobile robots
   (position, speed, state, battery). Object names are used as dictionary
   keys — the bridge does not require or assume any specific FlexSim
   object naming scheme.

2. **POST telemetry to the bridge.**

   ```text
   POST http://127.0.0.1:8000/api/v1/telemetry
   Content-Type: application/json
   ```

   The body must match the schema documented in the main project README
   (`simulation_time`, `model_status`, `queues`, `processors`, `robots`,
   and optionally `conveyors`, `sources`, `sinks`). The bridge validates
   the payload and responds with `{"accepted": true}` on success, or an
   HTTP 422 with validation details if the payload is malformed.

3. **Poll for pending commands.**

   ```text
   GET http://127.0.0.1:8000/api/v1/commands/next
   ```

   This returns the oldest pending command as JSON, or `{"command":
   null}` if none is queued. A command has the shape:

   ```json
   {
     "command_id": "...",
     "target": "AGV1",
     "command": "stop",
     "parameters": {},
     "status": "pending",
     "created_at": "...",
     "updated_at": "..."
   }
   ```

4. **Execute the received command** against the named `target` object
   inside the FlexSim model, using whatever FlexScript logic is
   appropriate for that command name and parameters. This mapping
   (command name → FlexScript action) is model-specific and is not
   defined by the bridge.

5. **Send acknowledgment** once the command has been attempted:

   ```text
   POST http://127.0.0.1:8000/api/v1/commands/{command_id}/ack
   Content-Type: application/json

   {
     "status": "executed",
     "message": "Command applied successfully"
   }
   ```

   Use `"status": "failed"` with a descriptive `message` if the command
   could not be applied. `"received"` may be sent immediately upon
   picking up a command, followed later by `"executed"` or `"failed"`,
   if a two-phase acknowledgment is useful for a given model.

## Suggested polling cadence

- Telemetry: send on every simulation tick that matters to your use case,
  or on a fixed wall-clock/sim-time interval (e.g. every 0.5–1 simulated
  seconds) to avoid flooding the bridge.
- Commands: poll `/api/v1/commands/next` on a similar periodic interval.
  There is currently no push mechanism (e.g. WebSockets) — polling is the
  Phase 1 design choice for simplicity and debuggability.

## See also

- `flexsim_http_examples.txt` — pseudo-FlexScript examples for the steps
  above, clearly labeled as pseudo-code.
- Main project `README.md` — full API reference, curl/PowerShell examples,
  and Swagger UI instructions (`http://127.0.0.1:8000/docs`) for testing
  the bridge independently of FlexSim.
