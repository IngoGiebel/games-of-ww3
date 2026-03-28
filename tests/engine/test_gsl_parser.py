"""Tests for the GSL Lark parser.

Verifies that the GSL grammar can parse all major rule patterns
from RULE_ENGINE_CONCEPT.md.
"""

import pytest
from gww3.engine.parser.gsl_parser import parse_rule


class TestBasicParsing:
    """Test basic GSL rule patterns."""

    def test_invariant_rule(self):
        """Invariant: landlocked → no navy."""
        tree = parse_rule("""MATCH (N:Nation)
IF N.is_landlocked
    THEN
        N.naval_projection = 0  ⟨1.00, 1.00⟩
""")
        assert tree is not None
        assert tree.data == "start"

    def test_top_level_effect(self):
        """Top-level effect without IF."""
        tree = parse_rule("""MATCH (N:Nation)
N.national_morale += 𝒩(0.5, 0.1)  ⟨0.50, 0.85⟩
""")
        assert tree is not None

    def test_let_binding(self):
        """LET variable binding with arithmetic."""
        tree = parse_rule("""MATCH (A:Nation)─[:SANCTIONS]→(B:Nation)
MATCH (A)─[:TRADES {volume: v}]→(B)
LET dependency = v / B.gdp_nominal
""")
        assert tree is not None

    def test_sanctions_full(self):
        """Full sanctions rule with MATCH + LET + IF + distributions."""
        tree = parse_rule("""MATCH (A:Nation)─[:SANCTIONS]→(B:Nation)
MATCH (A)─[:TRADES {volume: v}]→(B)
LET dependency = v / B.gdp_nominal
IF dependency > 0.3
    THEN
        B.gdp_nominal ×= 𝐿𝑁(-0.05, 0.02)  ⟨0.85, 0.90⟩
        B.stability -= 5.0  ⟨0.80, 0.85⟩
""")
        assert tree is not None


class TestNestedBlocks:
    """Test indentation-based nesting."""

    def test_nested_if_else(self):
        """Nested IF/THEN/ELSE."""
        tree = parse_rule("""MATCH (N:Nation)
IF N.population > 100000000
    THEN
        IF N.gdp_nominal > 1000000000000
            THEN
                N.stability += 5.0  ⟨0.90, 0.85⟩
            ELSE
                N.stability -= 3.0  ⟨0.80, 0.80⟩
""")
        assert tree is not None

    def test_multiple_effects(self):
        """Multiple effects in one THEN block."""
        tree = parse_rule("""MATCH (A:Nation)─[:AT_WAR_WITH]→(B:Nation)
IF A.manpower_active > 100000
    THEN
        A.war_weariness += 𝛽(2, 5)  ⟨0.90, 0.85⟩
        B.war_weariness += 𝛽(3, 5)  ⟨0.90, 0.85⟩
        A.gdp_nominal ×= 𝐿𝑁(-0.01, 0.005)  ⟨0.80, 0.90⟩
        B.gdp_nominal ×= 𝐿𝑁(-0.02, 0.01)  ⟨0.85, 0.90⟩
""")
        assert tree is not None


class TestDistributions:
    """Test all distribution types."""

    def test_normal(self):
        tree = parse_rule("""MATCH (N:Nation)
N.stability += 𝒩(5.0, 2.0)  ⟨0.80, 0.85⟩
""")
        assert tree is not None

    def test_lognormal(self):
        tree = parse_rule("""MATCH (N:Nation)
N.gdp_nominal ×= 𝐿𝑁(-0.05, 0.02)  ⟨0.85, 0.90⟩
""")
        assert tree is not None

    def test_beta(self):
        tree = parse_rule("""MATCH (N:Nation)
N.war_weariness += 𝛽(2, 5)  ⟨0.75, 0.80⟩
""")
        assert tree is not None

    def test_uniform(self):
        tree = parse_rule("""MATCH (N:Nation)
N.stability += 𝒰(0, 10)  ⟨0.50, 0.50⟩
""")
        assert tree is not None

    def test_bernoulli(self):
        tree = parse_rule("""MATCH (N:Nation)
IF ℬ(0.1) > 0
    THEN
        N.stability -= 20.0  ⟨1.00, 1.00⟩
""")
        assert tree is not None

    def test_ascii_fallback_LN(self):
        tree = parse_rule("""MATCH (N:Nation)
N.gdp_nominal ×= LN(-0.05, 0.02)  ⟨0.85, 0.90⟩
""")
        assert tree is not None


class TestOperators:
    """Test comparison and logical operators."""

    def test_and_operator(self):
        tree = parse_rule("""MATCH (N:Nation)
IF N.stability > 50 ∧ N.gdp_nominal > 1e12
    THEN
        N.national_morale += 1.0  ⟨0.50, 0.85⟩
""")
        assert tree is not None

    def test_or_operator(self):
        tree = parse_rule("""MATCH (N:Nation)
IF N.nuclear_warheads > 0 ∨ N.manpower_active > 1000000
    THEN
        N.stability += 2.0  ⟨0.60, 0.85⟩
""")
        assert tree is not None

    def test_comparison_operators(self):
        """Test >, <, >=, <=, ==, !=."""
        for op in [">", "<", ">=", "<=", "==", "!="]:
            tree = parse_rule(f"""MATCH (N:Nation)
IF N.stability {op} 50
    THEN
        N.national_morale += 1.0
""")
            assert tree is not None, f"Failed for operator {op}"


class TestEffectTypes:
    """Test all effect operator types."""

    def test_add(self):
        tree = parse_rule("""MATCH (N:Nation)
N.stability += 5.0  ⟨0.90, 0.85⟩
""")
        assert tree is not None

    def test_sub(self):
        tree = parse_rule("""MATCH (N:Nation)
N.stability -= 5.0  ⟨0.90, 0.85⟩
""")
        assert tree is not None

    def test_mod_unicode(self):
        tree = parse_rule("""MATCH (N:Nation)
N.gdp_nominal ×= 0.95  ⟨0.85, 0.90⟩
""")
        assert tree is not None

    def test_mod_ascii(self):
        tree = parse_rule("""MATCH (N:Nation)
N.gdp_nominal *= 0.95  ⟨0.85, 0.90⟩
""")
        assert tree is not None

    def test_set(self):
        tree = parse_rule("""MATCH (N:Nation)
N.naval_projection = 0
""")
        assert tree is not None


class TestComplexRules:
    """Test complex real-world rule patterns."""

    def test_war_economic_damage(self):
        tree = parse_rule("""MATCH (A:Nation)─[:AT_WAR_WITH]→(B:Nation)
LET cost_ratio = A.military_spending_abs / A.gdp_nominal
IF cost_ratio > 0.1
    THEN
        A.gdp_nominal ×= 𝐿𝑁(-0.03, 0.01)  ⟨0.85, 0.90⟩
        A.inflation_rate += 𝒩(2.0, 0.5)  ⟨0.80, 0.85⟩
        A.stability -= 𝒩(3.0, 1.0)  ⟨0.75, 0.80⟩
""")
        assert tree is not None

    def test_trade_dependency(self):
        tree = parse_rule("""MATCH (A:Nation)─[:TRADES {volume: v}]→(B:Nation)
LET dep = v / A.gdp_nominal
IF dep > 0.2
    THEN
        A.stability -= 𝒩(1.0, 0.5)  ⟨0.60, 0.85⟩
""")
        assert tree is not None

    def test_nuclear_deterrence(self):
        tree = parse_rule("""MATCH (A:Nation)─[:AT_WAR_WITH]→(B:Nation)
IF A.nuclear_warheads > 100 ∧ B.nuclear_warheads > 100
    THEN
        A.war_weariness += 𝛽(5, 2)  ⟨0.95, 0.95⟩
        B.war_weariness += 𝛽(5, 2)  ⟨0.95, 0.95⟩
""")
        assert tree is not None

    def test_inflation_spiral(self):
        tree = parse_rule("""MATCH (N:Nation)
IF N.inflation_rate > 50
    THEN
        N.stability -= 𝒩(10.0, 3.0)  ⟨0.90, 0.85⟩
        N.gdp_nominal ×= 𝐿𝑁(-0.1, 0.03)  ⟨0.85, 0.90⟩
        N.national_morale -= 𝒩(5.0, 2.0)  ⟨0.85, 0.85⟩
""")
        assert tree is not None

    def test_alliance_strength(self):
        tree = parse_rule("""MATCH (A:Nation)─[:MEMBER_OF]→(alliance:Alliance)←[:MEMBER_OF]─(B:Nation)
IF A.stability > 70 ∧ B.stability > 70
    THEN
        A.national_morale += 𝒩(1.0, 0.3)  ⟨0.60, 0.85⟩
""")
        assert tree is not None
