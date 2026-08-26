# Verified FlexScript snippets

Unlike `../flexsim_http_examples.txt` (which is labeled pseudo-code because
it was written before we had a real FlexSim 2027 instance to test against),
everything in this folder has actually been run inside FlexSim 2027's
Script Console against the running `flexsim-digital-twin-bridge` and
confirmed working. Treat this as the ground truth for FlexScript HTTP
syntax on this machine/version.

## Prerequisite: Windows Firewall

FlexSim 2027 was blocked from all network access (including localhost) by
two Windows Firewall rules named **"FlexSIM"** (Inbound + Outbound,
Action = Block). Until these are disabled, every HTTP call from FlexScript
fails silently — no FlexScript error, no bridge log entry, nothing.

Check the rules:
```powershell
Get-NetFirewallRule -DisplayName '*FlexSim*' | Select-Object DisplayName, Direction, Action, Enabled
```

Disable them (requires an elevated/Administrator PowerShell):
```powershell
Disable-NetFirewallRule -DisplayName 'FlexSIM'
```

## The FlexScript HTTP API (as it actually behaves in FlexSim 2027)

- The class is `Http.Request` / `Http.Response` (confirmed via the Script
  Console's autocomplete, not guessed).
- `Http.Request` properties: `host`, `port`, `path`, `method`, `data`,
  `headers`, `timeout`, `useSSL`, `statusCallback`, `successCallback`,
  `failCallback`, and the methods `send(...)` / `sendAndWait(...)`.
- `Http.Response` properties: `statusCode`, `data`, `headers`,
  `receivedBytes`, `totalBytes`, `value`.
- **The method enum is case-sensitive and easy to get wrong.** The correct
  form is `Http.Method.Post` / `Http.Method.Get` (capital `Method`, and
  only the first letter of `Post`/`Get` capitalized). Both a plain string
  (`"POST"`) and `Http.method.POST` (wrong case) compile/run *without any
  error*, but silently send a `GET` request instead — this is the failure
  mode that cost the most time, since nothing in the FlexScript console
  indicates it happened. Always verify by checking the bridge's own access
  log, not just "no error in FlexSim".
- `sendAndWait()` blocks and returns an `Http.Response` synchronously —
  convenient for this kind of one-shot script/testing. `send()` is
  asynchronous and uses `successCallback`/`failCallback` instead.
- `print()` output in the Script Console did not visibly appear anywhere
  we found (not in the console's own output box, not in the "System
  Console" tab). We never resolved where it goes. The reliable way to
  check a call succeeded is to end the script with a bare
  `resp.statusCode;` as the last statement (still needs the trailing
  `;` — a bare expression without `;` is a syntax error) and to cross-check
  the bridge's log/access log directly.

## Reading real model data

- Object names (`Queue1`, `Processor1`, ...) are **not** usable as bare
  identifiers in the Script Console — that only works inside an object's
  own trigger context. In a standalone script you must look the object up
  first: `Model.find("Queue1")`, which returns a `treenode` that
  `content(...)` and other FlexScript commands accept.
- `simtime()` does not exist. The current simulation time is
  `Model.time` (a property, not a function call).

## Files

- `test_post_telemetry.fsc` — minimal working POST of a hard-coded
  telemetry payload to `/api/v1/telemetry`. Confirmed: `statusCode` 200,
  and the bridge logged `Telemetry received: sim_time=1.00
  status=running queues=0 processors=0 robots=0`.
- `test_post_telemetry_real_queues.fsc` — builds the JSON from real model
  data: `Model.time` for simulation time, and
  `content(Model.find("Queue1"))` etc. for each queue's item count.
  Confirmed working: the bridge received and stored real `queues` values
  for `Queue1`, `Queue6`, `Queue7`, `Queue12` (all 0 while the model was
  stopped at time 0 — run the model to see nonzero counts). This is the
  pattern to extend for processors and AGVs/task executers next.

## Real object names in DG-FT-01.fsm

Pulled from the FlexSim Tree view, for reference when building the real
(non-hard-coded) telemetry payload:

- Queues: `Queue1`, `Queue6`, `Queue7`, `Queue12`, `Queue13`, `Queue14`,
  `Queue15`
- Processors: `Processor1`–`Processor7`
- Racks: `Rack8`–`Rack13`
- Operators: `Operator10`–`Operator26`
- Sinks: `Sink1`–`Sink4`
- Dispatchers: `Dispatcher2`–`Dispatcher4`
- Conveyors: many `StraightConveyor*` / `CurvedConveyor*`
- Decision Points: `DP3`–`DP17`
- Transfers: many `EntryTransfer*` / `ExitTransfer*`
- Travel network: `AGVNetwork`, `ControlPoint1`–`ControlPoint4`
- Task executers: at least `TaskExecuter4` seen in the 3D view

No confirmed FlexScript function yet for reading processor utilization or
AGV/task-executer position/battery — `content(QueueName)` is the only
data-read function used so far (standard, well-documented FlexSim
function). Extending the payload to processors/robots is the next step.
