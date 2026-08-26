# Verified FlexScript snippets

Unlike `../flexsim_http_examples.txt` (written before we had a real
FlexSim 2027 instance to test against, so it's labeled pseudo-code),
everything in this folder has actually been run inside FlexSim 2027
against the running bridge and confirmed working. Treat this as the
ground truth for FlexScript syntax on this model/version — every gotcha
below cost real debugging time and is worth reading before extending the
integration to a different FlexSim model.

**Start here:** [`final_telemetry_custom_code.fsc`](final_telemetry_custom_code.fsc)
is the complete, working script — paste it into the Process Flow's
`Custom Code` block. Everything else in this file explains *why* it's
written the way it is.

## Prerequisite: Windows Firewall

FlexSim 2027 was blocked from all network access (including localhost) by
two Windows Firewall rules named **"FlexSIM"** (Inbound + Outbound,
Action = Block). Until these are disabled, every HTTP call from FlexScript
fails silently — no FlexScript error, no bridge log entry, nothing.

```powershell
Get-NetFirewallRule -DisplayName '*FlexSim*' | Select-Object DisplayName, Direction, Action, Enabled
Disable-NetFirewallRule -DisplayName 'FlexSIM'   # requires an elevated PowerShell
```

## The FlexScript HTTP API (Http.Request / Http.Response)

- Confirmed via the Script Console's autocomplete, not guessed.
- `Http.Request` properties: `host`, `port`, `path`, `method`, `data`,
  `headers`, `timeout`, `useSSL`, `statusCallback`, `successCallback`,
  `failCallback`, and the methods `send(...)` / `sendAndWait(...)`.
- `Http.Response` properties: `statusCode`, `data`, `headers`,
  `receivedBytes`, `totalBytes`, `value`.
- **The method enum is case-sensitive and easy to get wrong.** The correct
  form is `Http.Method.Post` / `Http.Method.Get` (capital `Method`, only
  the first letter of `Post`/`Get` capitalized). Both a plain string
  (`"POST"`) and `Http.method.POST` (wrong case) compile and run *without
  any error*, but silently send a `GET` request instead — this was the
  single most time-consuming failure mode, since nothing in the FlexScript
  console indicates it happened. Always verify by checking the bridge's
  own access log, not just "no error in FlexSim".
- `sendAndWait()` blocks and returns an `Http.Response` synchronously.
  `send()` is asynchronous and uses `successCallback`/`failCallback`.
- `print()` output in the Script Console never visibly appeared anywhere
  we found. The reliable way to check a call succeeded is to end the
  script with a bare `resp.statusCode;` as the last statement (still
  needs the trailing `;`) and cross-check the bridge's own log.

## Reading real model data

- Object names (`Queue1`, `Processor1`, ...) are **not** usable as bare
  identifiers in the Script Console or a Process Flow Custom Code block —
  that only works inside an object's own trigger context. Look the object
  up first: `Model.find("Queue1")`, which returns a `treenode`.
- `simtime()` does not exist. Current simulation time is `Model.time`
  (a property, not a function call).
- **Nested objects need their full path, and `Model.find` fails silently
  if you get it wrong.** `Queue1`–`Queue4`, `Processor1`, `Processor2`,
  `TaskExecuter3`, `TaskExecuter4`, `Source1`, `Source2` all live nested
  under a `Plane1` group in `DG-FT-01.fsm`, not at the model root.
  `Model.find("Queue1")` does *not* error — it just quietly resolves to a
  different, empty node, so `content(Model.find("Queue1"))` always read 0
  even while the real Queue1 (visible in its own Statistics panel) was
  sitting at content=295 and climbing. The fix is
  `Model.find("Plane1/Queue1")`. **How to find any object's real path:**
  click it once (not double-click) in the 3D view or Tree and read the
  bottom status bar — it prints `Object: /Plane1/Queue1 Position [...]`.
- For a `TaskExecuter`, declaring the variable as the generic type first
  makes `.location`, `.location.x/.y/.z` etc. resolve correctly:
  ```
  TaskExecuter te4 = Model.find("Plane1/TaskExecuter4");
  double x = te4.location.x;
  ```
  Skipping the typed declaration (`Model.find(...).location.x` directly)
  throws `Property "location" ... Label does not exist` — FlexScript
  treats `.location` as a generic Label lookup on an untyped treenode
  instead of the built-in class property.
- No built-in "current speed" property was found on `TaskExecuter`
  (`.navigator` only exposes `.getCost(...)`). The final script computes
  speed itself each cycle from displacement between samples
  (`distance / dt`), stored in Model Parameters (`TE3PrevX`, `TE3PrevY`,
  `TE3PrevSampleTime`, etc.) so it persists across cycles.
- No confirmed built-in FlexScript function for processor utilization
  either (`stats.state()` / `getstatetableutilization()` exist per the
  docs but weren't verified against this model). The final script
  computes it itself: accumulate busy-time each cycle
  (`Model.parameters.ProcNBusy += dt` while `content(...) > 0`) and
  divide by `Model.time`.

## Model Parameters as global variables

`Model.parameters.<Name>` (Model Parameter Tables → Parameters) is the
way to persist a value across Custom Code executions (running totals,
previous-sample tracking, etc.) — confirmed working, but with two sharp
edges:

- **Type matters.** A parameter created as `Integer` silently *rounds*
  any value you assign (`Unable to set Proc6Busy to 267.51; using 268
  instead` — no error, just quiet data corruption). Use **`Continuous`**
  for anything that needs to hold a fractional value (busy-time
  accumulators, previous positions, previous timestamps).
- **Bounds matter.** New parameters default to `Lower Bound = 1`, which
  clamps any attempt to set the value to `0` (`Unable to set
  LastSampleTime to 0; using 1 instead`). Set `Lower Bound` to something
  safely below your minimum (e.g. `-999999`) and `Upper Bound` to
  something safely above your maximum (e.g. `999999999`) for every
  parameter used as a counter or accumulator.
- **Parameter names can't contain `-`.** FlexScript parses `Model.
  parameters.Ramp-East` as subtraction (`Model.parameters.Ramp` minus
  `East`), not as one identifier. Use `RampEast`, not `Ramp-East`.

## Throughput counting via Photo Eye triggers

FlexSim has no single built-in "items in / items out" counter readily
reachable from FlexScript for an arbitrary point in a conveyor line. The
approach used here: existing `PhotoEye` objects (`PE1`–`PE16` in this
model, already present for conveyor logic) each get one line of code in
their **`On Cover`** trigger (found via the object's Properties panel →
Triggers, not guessed — the trigger is *not* called "On Block"):

```
Model.parameters.<CounterName> = Model.parameters.<CounterName> + 1;
```

Renamed the counters to match what they physically represent
(`RampEast`, `RampWest`, `Merger`, `PreSort1`–`PreSort6`,
`Oddevenmerger`, `Odd`, `Even` for entry/sort points; `Out1`–`Out3` for
exit points) rather than keeping the generic `PE1`–`PE16` names, since
the counter names are what end up on the dashboard.

Multiple Photo Eyes can be edited at once: select several in the
`Edit Selected Objects` panel and use its Triggers section — confirmed
faster than editing each of 16 objects individually.

## Files

- **`final_telemetry_custom_code.fsc`** — the complete, current script.
  Sends real queue contents (including the `Plane1`-nested ones),
  computed processor utilization, computed robot speed/position for both
  `TaskExecuter3`/`TaskExecuter4`, and all throughput counters, every 5
  simulated seconds via a Process Flow loop (`Source` → `Custom Code` →
  `Delay(5s)` → back to `Custom Code`).
- `test_post_telemetry.fsc` — minimal first working POST (hard-coded
  payload), kept for reference as the smallest possible working example.
- `test_post_telemetry_real_queues.fsc` — an earlier, superseded version
  that reads real queue contents but predates the `Plane1` path fix and
  the processors/robots/counters additions. Kept for history; use
  `final_telemetry_custom_code.fsc` instead.

## Real object paths in DG-FT-01.fsm

- Under `Plane1` (the Inbound/Outbound intake cell): `Queue1`–`Queue4`,
  `Processor1`, `Processor2`, `Source1`, `Source2`, `TaskExecuter3`,
  `TaskExecuter4` — all need the `Plane1/` prefix in `Model.find(...)`.
- At the model root (no prefix needed): `Queue6`, `Queue7`, `Queue12`,
  `Queue13`, `Queue14`, `Queue15`, `Processor3`–`Processor7`, `Sink1`–
  `Sink4`, `Dispatcher2`–`Dispatcher4`, `PE1`–`PE16`, `DP3`–`DP17`, plus
  many `StraightConveyor*`/`CurvedConveyor*`/`EntryTransfer*`/
  `ExitTransfer*`.

If you extend this to another FlexSim model, don't assume root-level
paths — click each object once and check the status bar first.
