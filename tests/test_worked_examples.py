"""Golden tests: the 14 worked decisions + 3 preferred rankings from Worked_Examples.pdf.

This is the engine's scoreboard for the 40% "Decisions" bucket. Each case asserts the
scored facts (route, clubbing, consolidation grouping, item match, value, supplier,
price, suggestions). PO numbers are our own, so consolidation is asserted *relationally*
(which lines share a po_id), not by literal PO string.
"""
from datetime import date

from conftest import requires_data


def g(result, pr, line=1):
    return result["by_line"][(pr, line)]


@requires_data
class TestWorkedDecisions:

    def test_01_contract_po_beats_value(self, result):
        r = g(result, "PR-26-00019")
        assert r.resolved_item_code == "ITM-1002"
        assert (r.decision, r.route) == ("PO", "CONTRACT_PO")
        assert r.supplier_id == "S001"
        assert r.unit_price == "9169"
        assert r.group_value_inr == "137531"

    def test_02_pdf_only_contract(self, result):
        r = g(result, "PR-26-00045")
        assert r.resolved_item_code == "ITM-1037"
        assert r.route == "CONTRACT_PO"
        assert r.supplier_id == "S021"       # Pneumatic Point, PDF-only RC-2026-031
        assert r.unit_price == "2439"
        assert r.group_value_inr == "26829"

    def test_03_contract_ceiling_exhausted(self, result):
        a, b = g(result, "PR-26-00004"), g(result, "PR-26-00026")
        assert a.resolved_item_code == "ITM-1022"     # "brg 6308 ZZ" matched
        assert a.group_id == b.group_id               # clubbed
        assert a.route == "RFQ"                        # contract out of ceiling -> quotes
        assert a.group_value_inr == "220256"
        assert a.suggested_supplier_ids == "S014;S013;S016"

    def test_04_lowest_rate_contract_with_ceiling(self, result):
        a, b = g(result, "PR-26-00034"), g(result, "PR-26-00032")
        assert a.group_id == b.group_id
        assert a.route == "CONTRACT_PO"
        assert a.supplier_id == "S007"                # Precision Fasteners (RC-2026-013), not Unbrako
        assert a.unit_price == "7"
        assert a.group_value_inr == "32547"

    def test_05_split_prs_clubbed(self, result):
        lines = [g(result, p) for p in ("PR-26-00146", "PR-26-00144", "PR-26-00145")]
        gid = lines[0].group_id
        assert all(l.group_id == gid for l in lines)  # one requirement
        assert lines[0].route == "SPOT_PO"
        assert lines[0].supplier_id == "S024"
        assert lines[0].unit_price == "166"
        assert lines[0].group_value_inr == "126472"

    def test_06_same_item_different_plant_not_clubbed(self, result):
        a, b = g(result, "PR-26-00106"), g(result, "PR-26-00103")   # PUN1 vs CHK1
        assert a.resolved_item_code == b.resolved_item_code == "ITM-1044"
        assert a.group_id != b.group_id               # separate requirements
        assert a.route == "SPOT_PO" and a.supplier_id == "S027"
        assert a.group_value_inr == "156170"

    def test_07_free_text_item_matched(self, result):
        r = g(result, "PR-26-00088")
        assert r.resolved_item_code == "ITM-1035"     # "hyd hose 1/2 inch 2 wire"
        assert r.route == "SPOT_PO" and r.supplier_id == "S023"
        assert r.unit_price == "392"
        assert r.group_value_inr == "97955"

    def test_08_emergency_po(self, result):
        r = g(result, "PR-26-00059")
        assert r.resolved_item_code == "ITM-1026"
        assert r.route == "EMERGENCY_PO" and r.supplier_id == "S014"
        assert r.unit_price == "106"
        assert r.group_value_inr == "253184"

    def test_09_rfq_above_po_limit(self, result):
        r = g(result, "PR-26-00089")
        assert r.resolved_item_code == "ITM-1066"
        assert r.route == "RFQ"
        assert r.group_value_inr == "336562"
        assert r.suggested_supplier_ids == "S043;S044;S042"

    def test_10_small_but_never_bought_rfq(self, result):
        r = g(result, "PR-26-00050")
        assert r.resolved_item_code == "ITM-1006"
        assert r.route == "RFQ"                        # no proven supplier -> quotes
        assert r.group_value_inr == "80300"
        assert r.suggested_supplier_ids == "S003;S002;S005"

    def test_11_rfp(self, result):
        r = g(result, "PR-26-00100")
        assert r.resolved_item_code == "ITM-1034"
        assert r.route == "RFP"
        assert r.group_value_inr == "2070780"
        assert r.suggested_supplier_ids == "S020;S017;S019;S018"

    def test_12_capex(self, result):
        r = g(result, "PR-26-00047")
        assert r.resolved_item_code == "ITM-1071"      # "eot crane 5 ton" -> Capex item
        assert r.route == "CAPEX_SOURCING"
        assert r.group_value_inr == "6036704"
        assert r.suggested_supplier_ids == "S045;S047;S020;S048;S046"

    def test_13_new_item(self, result):
        r = g(result, "PR-26-00170")
        assert r.resolved_item_code == "NEW"
        assert r.route == "NEW_ITEM_SOURCING"
        assert r.group_value_inr == "141100"
        assert r.suggested_supplier_ids == ""          # new items get no suggestions

    def test_14_several_requirements_one_po(self, result):
        # Ex4 (PR-34+PR-32) and Ex14 (PR-31+PR-35) are two requirements consolidated onto ONE PO
        r31, r35 = g(result, "PR-26-00031"), g(result, "PR-26-00035")
        r34 = g(result, "PR-26-00034")
        assert r31.group_id == r35.group_id            # PR-31 & PR-35 clubbed
        assert r31.group_id != r34.group_id            # different requirement from PR-34
        assert r31.po_id and r31.po_id == r34.po_id    # but consolidated onto same PO
        assert r31.route == "CONTRACT_PO" and r31.supplier_id == "S007"
        assert r31.group_value_inr == "23227"


@requires_data
class TestPreferredLists:
    AS_OF = date(2026, 11, 1)

    def _ranked_ids(self, md, policy, item_code):
        from engine.core import PreferredEngine
        pe = PreferredEngine(md, policy)
        return [s.supplier_id for s, _, _ in pe.ranked_list(item_code, self.AS_OF)]

    def test_itm1048_nitrile_gloves(self, md, policy):
        ids = self._ranked_ids(md, policy, "ITM-1048")
        assert ids[:2] == ["S029", "S030"]
        assert "S031" not in ids              # Inactive excluded

    def test_itm1036_pneumatic_cylinder(self, md, policy):
        ids = self._ranked_ids(md, policy, "ITM-1036")
        assert ids[:3] == ["S023", "S022", "S024"]

    def test_itm1016_mig_wire(self, md, policy):
        ids = self._ranked_ids(md, policy, "ITM-1016")
        assert ids[:2] == ["S009", "S010"]


@requires_data
class TestInvariants:
    def test_no_blocked_or_inactive_supplier_used(self, result, md):
        banned = {s.supplier_id for s in md.suppliers if s.status in ("Blocked", "Inactive")}
        for row in result["rows"]:
            assert row.supplier_id not in banned
            for sid in (row.suggested_supplier_ids.split(";") if row.suggested_supplier_ids else []):
                assert sid not in banned

    def test_every_line_has_a_decision(self, result):
        for row in result["rows"]:
            assert row.decision in ("PO", "SOURCING_REQUEST")
            assert row.route
            assert row.group_id
