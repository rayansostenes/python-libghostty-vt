# 3. Callback binding lifetimes and the exception contract

Date: 2026-07-17

## Status

Accepted

## Context

libghostty-vt drives several effects through C function-pointer callbacks the
terminal invokes synchronously while parsing VT bytes (`ghostty_terminal_set`
with a `GHOSTTY_TERMINAL_OPT_*` option). The device domain is the first idiomatic
surface to cross that boundary: Python callables must be registered, invoked from
C with converted arguments, kept alive for exactly as long as the C side can call
them, and must never unwind a Python exception through the C stack. This is the
hardest binding shape in the library, and every later callback-using domain
(terminal effects, clipboard, size/color-scheme reports) will copy it, so the
lifetime and error handling are recorded here once.

## Decision

- **Registration** uses `ffi.callback(cdecl, fn, onerror=...)` (call form, not the
  decorator) so the wrapped function keeps its static type. The resulting cffi
  callback objects are stored on the owning Python object; the native terminal
  holds only raw pointers to them, so the owner is the sole thing keeping them
  alive. Handles are dropped only after the native resource is freed.
- **Ownership** follows the resource convention: the callback host owns the
  native handle, is a context manager, frees deterministically on `close()`, has a
  `weakref.finalize` fallback if the caller forgets, and guards use-after-close by
  raising a plain Python exception. Python callables never receive the raw
  `terminal`/`userdata` cdata — handlers take converted arguments and return
  idiomatic values, which the wrapper marshals into the C out-parameters.
- **Return-by-value strings** (`GhosttyString`) borrow a buffer that must outlive
  the callback return; the wrapper keeps each buffer alive on the host until the
  next feed, then releases it.
- **Exceptions are contained, not swallowed.** cffi's `onerror` hook stashes the
  first exception raised by any handler during a native call and lets the callback
  return its zeroed default, so the C stack is never unwound through. The
  driving method (e.g. `feed`) re-raises that exception after the native call
  returns and clears it, leaving the host usable. This is the documented contract:
  a handler error surfaces as a normal Python exception from the call that fed the
  bytes, never as a crash or a silently dropped error.

## Consequences

- Callback hosts are safe under GC pressure and interpreter shutdown: nothing the
  C side can call is collected before the handle is freed.
- Handler authors write ordinary Python (raise to abort, return a value to
  respond) without knowing anything about cffi, out-parameters, or the C stack.
- Later domains inherit a single pattern for registration, lifetime, string
  returns, and error surfacing rather than re-deriving it per callback.
- The contract is per-driving-call: only the first handler exception in a single
  native call is surfaced; subsequent handlers in that same call still run and
  return their defaults.
