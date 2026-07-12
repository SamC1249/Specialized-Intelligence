"""Domain registry.

The mission (see `AGENTS.md`) is to build systems that generalise
beyond cooking — surgery, laboratory work, sports, manufacturing, and
so on. A `Domain` is the minimum config a *domain-agnostic* pipeline
needs to know:

- seed search terms (used by every source adapter's `search`),
- procedural verbs (used by the metadata-only quality scorer),
- placeholder eval-set blocklist (populated when a benchmark exists).

Nothing in this module talks to the network. Nothing else in the
package may hard-code domain-specific vocabulary; look up a `Domain`
here instead. That way swapping cooking → surgery is a config change,
not a code change.

Public API:

- `get_domain(slug)`
- `list_domains()`
- `Domain` (Pydantic model)
- `DEFAULT_DOMAIN` (cooking)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Domain(BaseModel):
    """Config for one 'difficult video' domain.

    All fields are immutable (frozen=True) so a Domain instance is a
    safe global constant.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str
    seed_terms: tuple[str, ...]
    procedural_verbs: tuple[str, ...]
    eval_blocklist_urls: tuple[str, ...] = ()


COOKING = Domain(
    slug="cooking",
    display_name="Cooking / food preparation",
    seed_terms=(
        "cooking",
        "recipe",
        "how to cook",
        "kitchen",
        "chef",
        "baking",
    ),
    procedural_verbs=(
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "broil",
        "chill",
        "chop",
        "combine",
        "cook",
        "cover",
        "cream",
        "crumble",
        "cut",
        "dice",
        "dissolve",
        "drain",
        "drizzle",
        "fold",
        "fry",
        "garnish",
        "grate",
        "grease",
        "grill",
        "heat",
        "juice",
        "knead",
        "layer",
        "marinate",
        "mash",
        "melt",
        "mince",
        "mix",
        "peel",
        "poach",
        "pour",
        "preheat",
        "puree",
        "reduce",
        "roast",
        "roll",
        "saute",
        "season",
        "serve",
        "shred",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "stuff",
        "temper",
        "toast",
        "toss",
        "warm",
        "whip",
        "whisk",
        "zest",
    ),
    eval_blocklist_urls=(),
)


LABORATORY = Domain(
    slug="laboratory",
    display_name="Wet-lab / benchtop science procedures",
    seed_terms=(
        "laboratory protocol",
        "wet lab",
        "pipetting",
        "benchtop experiment",
        "chemistry demonstration",
        "biology procedure",
    ),
    procedural_verbs=(
        "add",
        "aliquot",
        "aspirate",
        "autoclave",
        "calibrate",
        "centrifuge",
        "clamp",
        "collect",
        "cool",
        "dilute",
        "dispense",
        "dissolve",
        "distill",
        "elute",
        "evaporate",
        "extract",
        "filter",
        "flush",
        "freeze",
        "heat",
        "hold",
        "homogenise",
        "immerse",
        "incubate",
        "inject",
        "invert",
        "label",
        "measure",
        "mix",
        "mount",
        "observe",
        "pipette",
        "pour",
        "preheat",
        "prepare",
        "quench",
        "record",
        "remove",
        "resuspend",
        "rinse",
        "sanitize",
        "seal",
        "shake",
        "sonicate",
        "stain",
        "sterilise",
        "stir",
        "swab",
        "titrate",
        "transfer",
        "vortex",
        "wash",
        "weigh",
    ),
    eval_blocklist_urls=(),
)


SURGERY = Domain(
    slug="surgery",
    display_name="Surgical / clinical procedure video",
    seed_terms=(
        "surgery",
        "surgical procedure",
        "endoscopy",
        "laparoscopy",
        "operative technique",
        "clinical procedure",
    ),
    procedural_verbs=(
        "administer",
        "aspirate",
        "cauterise",
        "clamp",
        "close",
        "dissect",
        "drain",
        "elevate",
        "excise",
        "expose",
        "extract",
        "grasp",
        "incise",
        "insert",
        "irrigate",
        "ligate",
        "monitor",
        "mobilise",
        "occlude",
        "open",
        "palpate",
        "position",
        "prep",
        "puncture",
        "release",
        "remove",
        "resect",
        "retract",
        "sample",
        "secure",
        "sew",
        "stabilise",
        "staple",
        "suction",
        "suture",
        "test",
        "tie",
        "transect",
        "wash",
    ),
    eval_blocklist_urls=(),
)


SPORTS = Domain(
    slug="sports",
    display_name="Sports and physical performance",
    seed_terms=(
        "training drill",
        "coaching demonstration",
        "sports technique",
        "workout tutorial",
        "athletic drill",
    ),
    procedural_verbs=(
        "accelerate",
        "aim",
        "balance",
        "block",
        "brace",
        "breathe",
        "catch",
        "chase",
        "coach",
        "control",
        "decelerate",
        "defend",
        "dodge",
        "drive",
        "drop",
        "extend",
        "fake",
        "finish",
        "follow",
        "grip",
        "guard",
        "hit",
        "hold",
        "jump",
        "kick",
        "land",
        "lift",
        "pass",
        "pivot",
        "plant",
        "position",
        "pull",
        "punch",
        "push",
        "reach",
        "release",
        "reset",
        "roll",
        "run",
        "serve",
        "shoot",
        "slide",
        "sprint",
        "start",
        "step",
        "strike",
        "swing",
        "target",
        "throw",
        "track",
        "turn",
    ),
    eval_blocklist_urls=(),
)


MANUFACTURING = Domain(
    slug="manufacturing",
    display_name="Manufacturing / assembly / machining",
    seed_terms=(
        "assembly instructions",
        "machining tutorial",
        "cnc procedure",
        "manufacturing process",
        "workshop tutorial",
        "how it's made",
    ),
    procedural_verbs=(
        "align",
        "assemble",
        "attach",
        "bend",
        "bolt",
        "calibrate",
        "clamp",
        "connect",
        "cool",
        "cut",
        "detach",
        "disassemble",
        "drill",
        "engage",
        "engrave",
        "extrude",
        "fasten",
        "feed",
        "file",
        "fit",
        "form",
        "grind",
        "hammer",
        "heat",
        "hold",
        "insert",
        "install",
        "join",
        "lift",
        "load",
        "loosen",
        "lubricate",
        "machine",
        "mount",
        "move",
        "operate",
        "orient",
        "package",
        "place",
        "polish",
        "position",
        "power",
        "press",
        "punch",
        "remove",
        "route",
        "sand",
        "screw",
        "seal",
        "shape",
        "solder",
        "start",
        "stop",
        "tap",
        "test",
        "tighten",
        "torque",
        "trim",
        "unload",
        "weld",
    ),
    eval_blocklist_urls=(),
)


_REGISTRY: dict[str, Domain] = {
    d.slug: d for d in (COOKING, LABORATORY, SURGERY, SPORTS, MANUFACTURING)
}


DEFAULT_DOMAIN: Domain = COOKING


def get_domain(slug: str) -> Domain:
    try:
        return _REGISTRY[slug]
    except KeyError as exc:
        raise KeyError(f"unknown domain slug {slug!r}; known: {sorted(_REGISTRY)}") from exc


def list_domains() -> list[Domain]:
    return sorted(_REGISTRY.values(), key=lambda d: d.slug)


__all__ = [
    "COOKING",
    "DEFAULT_DOMAIN",
    "LABORATORY",
    "MANUFACTURING",
    "SPORTS",
    "SURGERY",
    "Domain",
    "get_domain",
    "list_domains",
]
