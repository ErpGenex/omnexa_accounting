# Copyright (c) 2026, Omnexa
import json, frappe
from frappe.tests.utils import FrappeTestCase
from omnexa_accounting.acct_gap_register import GLOBAL_LEADER_TARGET, get_gap_status
from omnexa_accounting.acct_global_benchmark import get_global_acct_score
from omnexa_accounting.workspace.acct_workspace import sync_acct_workspace_menu

class TestAcctGlobalBenchmark(FrappeTestCase):
	def test_global_score(self):
		s = get_global_acct_score()
		self.assertGreaterEqual(s["weighted_score"], GLOBAL_LEADER_TARGET)
		self.assertTrue(s.get("global_leader_gate"))
	def test_gaps_closed(self):
		self.assertTrue(get_gap_status()["global_leader_gate"])
	def test_workspace_sync(self):
		stats = sync_acct_workspace_menu(save=True, rebuild=True)
		self.assertGreater(stats["total_links"], 10)
		ws = frappe.get_doc("Workspace", "Accounting")
		self.assertGreater(len(ws.shortcuts), 5)
