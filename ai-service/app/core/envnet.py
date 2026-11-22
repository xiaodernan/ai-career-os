"""The one door through which the ai-service builds an outbound HTTP client.

The service has two outbound needs: the provider calls (LLM, embedding, voice) that share
one pooled client for the life of the process, and the ingestion fetch that pulls stored
bytes back from the backend. Both read the same ambient ``HTTP_PROXY`` / ``NO_PROXY`` pair,
and both therefore belong behind one constructor that knows how operators actually spell
that pair.

The spelling is the problem. ``NO_PROXY`` is written by curl conventions and by Windows'
system-proxy bypass list, both of which put an IPv6 loopback in brackets -- ``[::1]`` --
because a bare ``::1`` in a comma-separated list is ambiguous about where the address ends.
httpx 0.28.1 splits every entry on ``:`` and reads what follows as a port, so the last
colon of ``[::1]`` leaves ``:1]`` standing where a port number belongs, and construction
raises ``InvalidURL: Invalid port: ':1]'``.

That is raised by *construction*, before a socket exists, so the whole AI surface answers 500
on the first call and ``/health`` -- which asks the same factories whether they can build
what the deployment named -- fails with it too. A bypass list typed for a different program
closes the engine's door, and the message names neither the variable nor the fix.

So the bracket is stripped here, which is a spelling change and not a semantic one: ``[::1]``
and ``::1`` are the same host, and only the second parses. Anything this cannot translate
without guessing -- a bracket carrying its own port, an IPv6 CIDR -- is refused with a
message that says which variable, what it holds, and what shape works, because the shape of
this failure is the thing an operator has to act on.
"""

import logging
import os
import re

import httpx

log = logging.getLogger(__name__)

#: Both spellings Windows and POSIX tooling write; the second is what most HTTP stacks read.
PROXY_BYPASS_VARS = ("NO_PROXY", "no_proxy")

# A bracketed literal whose closing bracket is not followed by `:port`: the one shape whose
# meaning is unchanged by removing the brackets.
_BRACKETED_HOST = re.compile(r"\[([^\],]+)\](?!:)")


class ProxyEnvError(ValueError):
    """The ambient proxy environment cannot be read, so no outbound call can be made.

    A ``ValueError`` subclass on purpose: nothing catching the provider factory's failures
    has to learn a new family. What answers a reader is ``register_refusal_handlers``, which
    maps this to the ``AI_EGRESS_ENV_UNREADABLE`` envelope so the 503 carries the same
    sentence the log carries.
    """


def normalize_proxy_bypass(environ: dict | None = None) -> list[tuple[str, str, str]]:
    """Rewrite the bracket form in the bypass list, in place; return what changed.

    Reads and writes the process environment by default, because that is what httpx reads at
    construction: normalizing a copy would leave the client to fail on the original.
    """
    env = os.environ if environ is None else environ
    changed: list[tuple[str, str, str]] = []
    for name in PROXY_BYPASS_VARS:
        raw = env.get(name)
        if not raw:
            continue
        fixed = _BRACKETED_HOST.sub(r"\1", raw)
        if fixed != raw:
            env[name] = fixed
            changed.append((name, raw, fixed))
    return changed


def client(**kwargs) -> httpx.AsyncClient:
    """Build an httpx client against a bypass list that has been made readable.

    Every keyword goes to ``httpx.AsyncClient`` untouched, so a caller keeps its own limits
    and timeouts: this door changes how the environment is read, never what the client does.
    """
    for name, raw, fixed in normalize_proxy_bypass():
        log.info("%s carried a bracketed literal; httpx reads only the bare form (%s -> %s)",
                 name, raw, fixed)
    try:
        return httpx.AsyncClient(**kwargs)
    except httpx.InvalidURL as exc:
        reason = _unreadable(exc)
        # Logged before raised: the request that carries this sentence to a reader may be
        # the last one anyone sees, and the process that needs fixing keeps serving.
        log.warning("%s", reason)
        raise ProxyEnvError(reason) from exc


def _unreadable(exc: httpx.InvalidURL) -> str:
    """The sentence an operator reads: which variable, what it holds, what shape works."""
    held = ", ".join(f"{name}={os.environ[name]!r}" for name in PROXY_BYPASS_VARS
                     if os.environ.get(name))
    return (f"the outbound client could not be built: httpx refused the proxy environment "
            f"({exc}). A bypass list may hold bare hosts, dot-suffixed domains and IPv6 "
            f"literals without brackets; this process was given {held or 'nothing'}")
