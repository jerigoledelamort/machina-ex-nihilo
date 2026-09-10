/-
Mathesis REPL: persistent Lean process for the interactive backend (spec s14).

Protocol: JSON lines over stdin/stdout.
  -> {"op": "ping"}
  -> {"op": "verify", "source": "...", "update_env": false}
  -> {"op": "close"}
  <- {"ok": true/false, "status": "...", "messages": [...], "error": "..."}

Imports are loaded ONCE at startup from the command line:
  mathesis_repl --imports Mathesis.Basic,Init

Re-running `importModules (loadExts := true)` inside a live process is not
safe (initializer re-execution), so environment reset is done by the Python
wrapper by restarting the process.

Each "verify" runs the full frontend (parse -> elaborate -> kernel check)
against the current environment. On success (no errors) and update_env=true,
the resulting environment (with new declarations) is kept for subsequent
commands. Messages are returned in structured serialized form.
-/

import Lean
open Lean

namespace Mathesis.Repl

def jErr (msg : String) : Json :=
  Json.mkObj [("ok", Json.bool false), ("error", Json.str msg)]

def jOk (status : String) : Json :=
  Json.mkObj [("ok", Json.bool true), ("status", Json.str status)]

def ready : Json := jOk "ready"

def msgsToJson (log : MessageLog) : BaseIO Json := do
  let mut arr : Array Json := #[]
  for msg in log.reportedPlusUnreported.toList do
    let s ← msg.serialize
    arr := arr.push (toJson s)
  return .arr arr

def loadEnv (imports : List String) (opts : Options) : IO Environment := do
  let imps : Array Import := imports.toArray.map fun s => { module := s.toName }
  -- loadExts := true is essential: without it builtin/environment extensions
  -- from imported modules are not registered and elaboration breaks.
  importModules (imports := imps) (opts := opts) (loadExts := true)

def processSource (env : Environment) (opts : Options) (source : String) :
    IO (Json × Option Environment) := do
  try
    let (env', log) ← Lean.Elab.process source env opts
    let msgs ← msgsToJson log
    let hasErr := log.hasErrors
    let resp := Json.mkObj [
      ("ok", Json.bool true),
      ("status", Json.str (if hasErr then "error" else "success")),
      ("messages", msgs)]
    return (resp, if hasErr then none else some env')
  catch e =>
    return (jErr ("frontend: " ++ e.toString), none)

def getStrField (j : Json) (name : String) (default : String := "") : String :=
  ((j.getObjValD name).getStr?).toOption.getD default

def parseImportsArg (args : List String) : List String :=
  match args.find? (· == "--imports") with
  | some _ =>
    match args.dropWhile (· != "--imports") |>.drop 1 |>.head? with
    | some csv => csv.splitOn "," |>.map String.trim |>.filter (· != "")
    | none => ["Init"]
  | none => ["Init"]

def handle (envRef : IO.Ref Environment) (opts : Options) (j : Json) : IO Json := do
  match (j.getObjValD "op").getStr? with
  | .error e => pure (jErr ("op: " ++ e))
  | .ok "ping" => pure ready
  | .ok "verify" => do
    let source := getStrField j "source"
    let update := (j.getObjValD "update_env").getBool?.toBool
    let env ← envRef.get
    let (resp, envOut) ← processSource env opts source
    if update then
      match envOut with
      | some e' => envRef.set e'
      | none => pure ()
    pure resp
  | .ok "close" => pure (jOk "closing")
  | .ok _ => pure (jErr "unknown op")

unsafe def main (args : List String) : IO UInt32 := do
  enableInitializersExecution
  initSearchPath (← findSysroot)
  let opts : Options := {}
  let stdout ← IO.getStdout
  let stdin ← IO.getStdin
  let imports := parseImportsArg args
  match ← (loadEnv imports opts).toBaseIO with
  | .error e =>
    stdout.putStrLn (jErr ("init: " ++ e.toString)).compress
    stdout.flush
    return 1
  | .ok env0 =>
    let envRef ← IO.mkRef env0
    stdout.putStrLn ready.compress
    stdout.flush
    let mut eof := false
    while !eof do
      let line? ← stdin.getLine
      match line? with
      | "" => eof := true
      | line =>
        let parsed := Json.parse line.trimAscii.toString
        let resp : Json ←
          match parsed with
          | .error e => pure (jErr ("json: " ++ e))
          | .ok j => do
            let r ← handle envRef opts j
            if ((j.getObjValD "op").getStr?).toOption == some "close" then
              eof := true
            pure r
        stdout.putStrLn resp.compress
        stdout.flush
    return 0

end Mathesis.Repl

unsafe def main (args : List String) : IO UInt32 := Mathesis.Repl.main args
