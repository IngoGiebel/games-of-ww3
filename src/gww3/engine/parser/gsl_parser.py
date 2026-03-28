"""GSL Parser — Lark-based parser for GWW3 Symbolic Logic rules.

Parses GSL rule text into an AST (Lark Tree). The AST is then transformed
into GSL dataclasses by the transformer module (Sprint 4.1).

Reference: docs/RULE_ENGINE_CONCEPT.md
Grammar: src/gww3/engine/parser/gsl.lark
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark
from lark.indenter import Indenter


class GSLIndenter(Indenter):
    """Indentation handler for GSL (4-space indent).

    Uses Lark's Indenter base class (not PythonIndenter) because
    GSL's _NL token includes trailing whitespace, which the Indenter
    uses to determine indentation level.
    """
    NL_type = "_NL"
    OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
    CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


_GRAMMAR_PATH = Path(__file__).parent / "gsl.lark"


def _build_parser() -> Lark:
    """Build the Lark parser from the .lark grammar file."""
    with open(_GRAMMAR_PATH) as f:
        grammar = f.read()
    return Lark(
        grammar,
        parser="lalr",
        postlex=GSLIndenter(),
        propagate_positions=True,
        maybe_placeholders=False,
    )


# Module-level parser singleton (built once on import)
_parser: Lark | None = None


def get_parser() -> Lark:
    """Get or build the GSL parser (singleton)."""
    global _parser
    if _parser is None:
        _parser = _build_parser()
    return _parser


def parse_rule(rule_text: str) -> "lark.Tree":
    """Parse a GSL rule string into a Lark AST.

    Args:
        rule_text: GSL rule text (may include rule header delimiters)

    Returns:
        Lark Tree representing the parsed AST

    Raises:
        lark.exceptions.LarkError: If the rule text is syntactically invalid
    """
    parser = get_parser()
    # Ensure trailing newline (required by indentation parser)
    if not rule_text.endswith("\n"):
        rule_text += "\n"
    return parser.parse(rule_text)


def parse_rule_file(path: str | Path) -> "lark.Tree":
    """Parse a GSL rule file."""
    with open(path) as f:
        return parse_rule(f.read())
