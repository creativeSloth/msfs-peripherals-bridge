"""Comment-preserving reader/writer for profile YAML files.

The GUI Mapper editor (Stufe B) edits a profile in place and writes it back.
``profiles/piper_arrow.yaml`` is ~40 % comments and uses a deliberate compact
style (``source``/``action``/``transform`` as one-line *flow* maps, long lines
left unwrapped) — none of that may be lost on a round-trip. PyYAML's
``safe_dump`` throws all of it away, so this module uses ``ruamel.yaml`` in
round-trip mode.

Design:

* **Edits update the existing nodes in place** (:func:`_sync`) so every comment,
  quote and flow/block style on unchanged parts survives; only the keys that
  actually change are rewritten.
* **New nodes** (added bindings, seeded ``local_vars``) are built with
  :func:`_node`, which mirrors the profiles' convention: an all-scalar map (a
  ``source``/``action``/``transform``) is emitted as a compact flow map, nested
  structures (the binding container, a ``sequence`` action) as block.

The functions are pure data transforms on the loaded document, so they unit-test
without a display. Validate the result with :func:`validate` before saving to
catch an edit the mapping engine would reject.

Known limitation: ruamel does not record an author's *manual line breaks inside a
flow collection*, so the few hand-wrapped multi-line flow maps in piper_arrow's
``outputs`` (the AP selector table, the radio banks) collapse to one line each on
the first save. That is a one-time, semantically-null reformat confined to those
blocks; comments, quotes, structure and every ``bindings`` line are byte-exact.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.emitter import Emitter

from .models import Profile


class _PaddedEmitter(Emitter):
    """Emit flow mappings with inner padding: ``{ a: 1 }`` not ``{a: 1}``.

    ruamel's round-trip preserves flow *style* but not the brace padding, so a
    plain dump would reflow every ``source``/``action``/``transform`` line in the
    hand-authored profiles into a noisy diff. This pads only the flow-*map* braces
    (the opening ``{`` gains a trailing space, the closing ``}`` a leading one) to
    match the profiles' style; keys, values, separators and flow *sequences* are
    untouched — sequences are left alone so an empty ``[]`` (e.g. an unset
    ``aircraft_match``) is not turned into ``[  ]``. The ``flow_context`` token
    stays ``'{'`` so ruamel's internal assertions are unaffected.
    """

    def write_indicator(
        self, indicator, need_whitespace, whitespace=False, indention=False
    ) -> None:
        if isinstance(indicator, str):
            if indicator.endswith("{"):
                indicator = indicator + " "
            elif indicator == "}":
                indicator = " " + indicator
        super().write_indicator(indicator, need_whitespace, whitespace, indention)


def _yaml() -> YAML:
    """A round-trip YAML configured to match the profiles' formatting."""
    y = YAML()  # round-trip mode: keeps comments, quotes, flow style
    y.preserve_quotes = True
    y.Emitter = _PaddedEmitter  # pad flow-map braces to match the profiles
    # Profiles have long single-line flow maps (e.g. a transform) — never wrap.
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _node(value: object) -> object:
    """Convert a plain dict/list/scalar into a ruamel node for insertion.

    An all-scalar map is set to flow style (``{ kind: axis, code: 0 }``) to match
    the profiles' compact ``source``/``action``/``transform`` lines; anything with
    nested structure stays block.
    """
    if isinstance(value, dict):
        m = CommentedMap()
        for k, v in value.items():
            m[k] = _node(v)
        if value and all(not isinstance(v, (dict, list)) for v in value.values()):
            m.fa.set_flow_style()
        return m
    if isinstance(value, list):
        s = CommentedSeq()
        for v in value:
            s.append(_node(v))
        return s
    return value


def _sync(target: object, desired: object) -> object:
    """Make ``target`` match ``desired`` while preserving comments/style.

    Recursively updates the existing ruamel node in place: shared keys are
    synced (so their comments and flow/block style survive), keys absent from
    ``desired`` are removed, new keys are inserted as :func:`_node`. On a type
    change the node is replaced wholesale.
    """
    if isinstance(desired, dict):
        if not isinstance(target, CommentedMap):
            return _node(desired)
        for key in [k for k in target if k not in desired]:
            del target[key]
        for key, val in desired.items():
            target[key] = _sync(target[key], val) if key in target else _node(val)
        return target
    if isinstance(desired, list):
        if not isinstance(target, CommentedSeq):
            return _node(desired)
        while len(target) > len(desired):
            target.pop()
        for i, val in enumerate(desired):
            if i < len(target):
                target[i] = _sync(target[i], val)
            else:
                target.append(_node(val))
        return target
    return desired  # scalar: replace by value


# --------------------------------------------------------------------------- #
# load / dump
# --------------------------------------------------------------------------- #
def load(path: Path) -> CommentedMap:
    """Load a profile YAML into a round-trip document (comments preserved)."""
    return _yaml().load(path.read_text(encoding="utf-8"))


def dumps(data: CommentedMap) -> str:
    """Serialise a round-trip document back to a YAML string."""
    import io

    buf = io.StringIO()
    _yaml().dump(data, buf)
    return buf.getvalue()


def dump(data: CommentedMap, path: Path) -> None:
    """Write a round-trip document back to ``path``."""
    path.write_text(dumps(data), encoding="utf-8")


def validate(data: CommentedMap) -> Profile:
    """Parse the document through the Pydantic model, raising on any error.

    Call before saving so an edit the mapping engine would reject fails loudly
    instead of writing a broken profile to disk.
    """
    return Profile.model_validate(data)


def new_profile(name: str, description: str = "") -> CommentedMap:
    """Build a fresh, minimal-but-valid profile document.

    Used by the GUI's "new profile" action: a bare skeleton (name, empty
    aircraft-match and bindings) the user then fills in via the Mapper editor.
    Passes :func:`validate` as-is and dumps in the profiles' compact style.
    """
    doc = CommentedMap()
    doc["name"] = name
    doc["description"] = description
    doc["aircraft_match"] = _node([])
    doc["bindings"] = CommentedMap()
    doc.yaml_set_start_comment(f"{name} — neues Profil (im Mapper-Tab bearbeiten)\n")
    return doc


# --------------------------------------------------------------------------- #
# binding edits
# --------------------------------------------------------------------------- #
def _bindings(data: CommentedMap, device_id: str) -> CommentedSeq:
    bindings = data.get("bindings")
    if not isinstance(bindings, CommentedMap) or device_id not in bindings:
        raise KeyError(f"no bindings for device '{device_id}'")
    return bindings[device_id]


def apply_binding_edit(
    data: CommentedMap, device_id: str, index: int, binding: dict
) -> None:
    """Replace the binding at ``(device_id, index)`` with ``binding`` in place.

    ``binding`` is the complete desired mapping (``name``/``source``/``action``
    and optional ``transform``); pass the full ``source`` (incl. any
    ``raw_min``/``raw_max``) since keys absent from it are removed.
    """
    seq = _bindings(data, device_id)
    seq[index] = _sync(seq[index], binding)


def add_binding(
    data: CommentedMap, device_id: str, binding: dict, index: int | None = None
) -> None:
    """Append (or insert at ``index``) a new binding for ``device_id``."""
    bindings = data.get("bindings")
    if not isinstance(bindings, CommentedMap):
        bindings = CommentedMap()
        data["bindings"] = bindings
    seq = bindings.get(device_id)
    if not isinstance(seq, CommentedSeq):
        seq = CommentedSeq()
        bindings[device_id] = seq
    item = _node(binding)
    if index is None:
        seq.append(item)
    else:
        seq.insert(index, item)


def remove_binding(data: CommentedMap, device_id: str, index: int) -> None:
    """Delete the binding at ``(device_id, index)``."""
    seq = _bindings(data, device_id)
    del seq[index]


# --------------------------------------------------------------------------- #
# local (virtual) variable declarations
# --------------------------------------------------------------------------- #
def set_local_vars(data: CommentedMap, local_vars: list[dict]) -> None:
    """Replace the ``local_vars:`` block (removed entirely when the list is empty).

    Each entry is a plain dict (``{name, unit, initial, persist, description}``);
    defaults may be omitted. Existing entries are synced in place so their
    comments survive.
    """
    if not local_vars:
        if "local_vars" in data:
            del data["local_vars"]
        return
    current = data.get("local_vars")
    data["local_vars"] = _sync(current if isinstance(current, CommentedSeq) else CommentedSeq(),
                               local_vars)
