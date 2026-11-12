import json

from evally.app.store import Store
from evally.app.tools import TOOLS, run_tool
from evally.types import ToolCall


def call(name, **args):
    return run_tool(Store.from_seed(), ToolCall("c1", name, args))


def test_tools_are_declared():
    assert {t.name for t in TOOLS} == {"lookup_order", "check_stock", "start_return", "escalate_to_human"}


def test_lookup_requires_matching_email():
    ok = call("lookup_order", order_id="BB-1002", email="ben@example.com")
    assert not ok.is_error and json.loads(ok.content)["status"] == "shipped"
    wrong = call("lookup_order", order_id="BB-1002", email="someone@else.com")
    assert wrong.content == "No order found for that order id and email."


def test_check_stock_north_warehouse_errors():
    r = call("check_stock", isbn="9780000000028")  # Quiet Rivers, north warehouse
    assert r.is_error and "timeout" in r.content


def test_check_stock_east_warehouse_ok():
    r = call("check_stock", isbn="9780000000011")
    assert not r.is_error and json.loads(r.content)["in_stock"] == 12


def test_start_return_rejects_outside_30_days():
    r = call("start_return", order_id="BB-1003", email="chen@example.com", reason="changed my mind")
    assert r.is_error and "30 days" in r.content


def test_start_return_ok():
    r = call("start_return", order_id="BB-1001", email="alice@example.com", reason="duplicate gift")
    assert not r.is_error and json.loads(r.content)["return_id"] == "R-BB-1001"


def test_unknown_tool_is_error_result():
    r = call("refund_everything")
    assert r.is_error and "Unknown tool" in r.content


def test_missing_argument_is_error_result():
    r = call("lookup_order", order_id="BB-1001")
    assert r.is_error and "email" in r.content
