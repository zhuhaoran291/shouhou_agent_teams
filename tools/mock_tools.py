"""电商售后 mock 工具实现。

数据来自 scenarios/{scenario_id}.json；每个场景独立维护内存状态
（案件、审批、退款、补发单、库存预留），写操作支持幂等键。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "scenarios"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_scenarios() -> List[str]:
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def load_scenario(scenario_id: str) -> Dict[str, Any]:
    path = SCENARIO_DIR / f"{scenario_id}.json"
    if not path.exists():
        available = ", ".join(list_scenarios())
        raise ValueError(f"Unknown scenario '{scenario_id}'. Available: {available}")
    return load_json(path)


def compact(value: Any, max_len: int = 180) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


class BaseMockTools:
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        self.actions: List[Dict[str, Any]] = []
        self.trace: List[Dict[str, Any]] = []

    def _record(self, tool: str, args: Dict[str, Any], result: Any) -> Any:
        self.trace.append(
            {
                "time": _now(),
                "tool": tool,
                "args": args,
                "result_preview": compact(result),
            }
        )
        return result

    def reset(self) -> None:
        self.actions.clear()
        self.trace.clear()


class LocalMockTools(BaseMockTools):
    """售后场景工具：方法名规则 {tool_domain}_{function}，与 tool_catalog.json 一致。"""

    def __init__(self, scenario_id: str) -> None:
        super().__init__(scenario_id)
        self.scenario = load_scenario(scenario_id)
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.approvals: Dict[str, Dict[str, Any]] = {}
        self.refunds: Dict[str, Dict[str, Any]] = {}
        self.reships: Dict[str, Dict[str, Any]] = {}
        self.reserves: Dict[str, Dict[str, Any]] = {}
        self.idempotent: Dict[str, Any] = {}
        self.messages: List[Dict[str, Any]] = []

    # ---------- 内部辅助 ----------

    def _seq(self, prefix: str) -> str:
        counter = len(self.actions) + 1
        return f"{prefix}-{counter:04d}"

    def _find_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return next((o for o in self.scenario.get("orders", []) if o["order_id"] == order_id), None)

    def _find_payment(self, order_id: str) -> Optional[Dict[str, Any]]:
        return next((p for p in self.scenario.get("payments", []) if p["order_id"] == order_id), None)

    def _find_track(self, order_id: str) -> Optional[Dict[str, Any]]:
        return next((t for t in self.scenario.get("logistics", []) if t["order_id"] == order_id), None)

    def _find_inventory(self, product_id: str) -> Optional[Dict[str, Any]]:
        return next((i for i in self.scenario.get("inventory", []) if i["product_id"] == product_id), None)

    def _idempotent_guard(self, key: str) -> Optional[Any]:
        if key and key in self.idempotent:
            return self.idempotent[key]
        return None

    def _idempotent_commit(self, key: str, result: Any) -> Any:
        if key:
            self.idempotent[key] = result
        return result

    # ---------- aftersales ----------

    def aftersales_get_complaint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        complaint = self.scenario["complaint"]
        return self._record(
            "aftersales.get_complaint",
            payload,
            {
                "case_id": payload.get("case_id") or self.scenario["case_id"],
                "merchant_id": self.scenario["merchant_id"],
                "contact": complaint.get("contact"),
                "submitted_at": complaint.get("submitted_at"),
                "text": complaint["text"],
            },
        )

    def aftersales_query_processing_rules(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rules = self.scenario.get("processing_rules", {})
        return self._record(
            "aftersales.query_processing_rules",
            payload,
            {"scenario": payload.get("scenario") or self.scenario_id, "rules": rules},
        )

    # ---------- customer ----------

    def customer_get_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer = self.scenario["customer"]
        return self._record("customer.get_profile", payload, customer)

    # ---------- order ----------

    def order_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        keyword = (payload.get("keyword") or "").lower()
        orders = []
        for order in self.scenario.get("orders", []):
            if customer_id and order.get("customer_id") != customer_id:
                continue
            if keyword and keyword not in order["order_id"].lower():
                names = " ".join(item["name"] for item in order["items"])
                if keyword not in names.lower():
                    continue
            orders.append(
                {
                    "order_id": order["order_id"],
                    "status": order["status"],
                    "created_at": order["created_at"],
                    "items": order["items"],
                    "fulfillment": order.get("fulfillment", "全部发货"),
                }
            )
        return self._record("order.search", payload, {"orders": orders})

    def order_get_detail(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order = self._find_order(payload.get("order_id", ""))
        if order is None:
            return self._record("order.get_detail", payload, {"found": False, "order_id": payload.get("order_id")})
        return self._record("order.get_detail", payload, {"found": True, **order})

    def order_check_reship_eligible(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = payload.get("product_id", "")
        stock = self._find_inventory(product_id)
        eligible = bool(stock and stock.get("available", 0) > 0)
        return self._record(
            "order.check_reship_eligible",
            payload,
            {
                "order_id": payload.get("order_id"),
                "product_id": product_id,
                "eligible": eligible,
                "available": stock.get("available", 0) if stock else 0,
                "reason": "库存充足，可补发" if eligible else "库存不足，无法补发",
            },
        )

    def order_create_reship(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = payload.get("idempotency_key")
        dup = self._idempotent_guard(key)
        if dup is not None:
            return self._record("order.create_reship", payload, {**dup, "duplicated": True})
        reship_id = self._seq("RS")
        result = {
            "reship_id": reship_id,
            "order_id": payload.get("order_id"),
            "product_id": payload.get("product_id"),
            "status": "已创建",
            "tracking_no": f"SF-R{reship_id}",
            "message": "补发单已创建，等待出库发货。",
        }
        self.reships[reship_id] = result
        self.actions.append({"action": "create_reship", **result})
        return self._record("order.create_reship", payload, self._idempotent_commit(key, result))

    # ---------- payment ----------

    def payment_get_detail(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payment = self._find_payment(payload.get("order_id", ""))
        if payment is None:
            return self._record("payment.get_detail", payload, {"found": False, "order_id": payload.get("order_id")})
        return self._record("payment.get_detail", payload, {"found": True, **payment})

    # ---------- logistics ----------

    def logistics_get_track(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        track = self._find_track(payload.get("order_id", ""))
        if track is None:
            return self._record("logistics.get_track", payload, {"found": False, "order_id": payload.get("order_id")})
        return self._record("logistics.get_track", payload, {"found": True, **track})

    def logistics_query_reship(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        reship_id = payload.get("reship_id", "")
        reship = self.reships.get(reship_id)
        if reship is None:
            return self._record("logistics.query_reship", payload, {"reship_id": reship_id, "found": False})
        return self._record(
            "logistics.query_reship",
            payload,
            {
                "reship_id": reship_id,
                "order_id": reship["order_id"],
                "status": "已发货",
                "tracking_no": reship["tracking_no"],
                "nodes": [
                    {"time": _now(), "event": "已揽收"},
                    {"time": _now(), "event": "运输中，预计 2-3 天送达"},
                ],
            },
        )

    # ---------- inventory ----------

    def inventory_query_available(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        stock = self._find_inventory(payload.get("product_id", ""))
        if stock is None:
            return self._record("inventory.query_available", payload, {"found": False, "product_id": payload.get("product_id")})
        return self._record("inventory.query_available", payload, {"found": True, **stock})

    def inventory_reserve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = payload.get("idempotency_key")
        dup = self._idempotent_guard(key)
        if dup is not None:
            return self._record("inventory.reserve", payload, {**dup, "duplicated": True})
        reserve_id = self._seq("RV")
        result = {
            "reserve_id": reserve_id,
            "order_id": payload.get("order_id"),
            "product_id": payload.get("product_id"),
            "quantity": payload.get("quantity", 1),
            "status": "已预留",
            "message": "库存预留成功，等待补发出库。",
        }
        self.reserves[reserve_id] = result
        self.actions.append({"action": "reserve", **result})
        return self._record("inventory.reserve", payload, self._idempotent_commit(key, result))

    # ---------- evidence ----------

    def evidence_list_submissions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._record(
            "evidence.list_submissions",
            payload,
            {"case_id": payload.get("case_id") or self.scenario["case_id"], "evidence": self.scenario.get("evidence", [])},
        )

    def evidence_verify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        refs = payload.get("evidence_refs") or []
        all_evidence = self.scenario.get("evidence", [])
        verified = []
        for item in all_evidence:
            if not refs or item["evidence_id"] in refs or item["ref"] in refs:
                verified.append(
                    {
                        "evidence_id": item["evidence_id"],
                        "type": item["type"],
                        "result": "与投诉描述一致",
                        "detail": f"{item['desc']} 已核实，可作为证据",
                    }
                )
        conclusion = "证据足以支持诉求" if verified else "缺少证据，需要补充"
        return self._record("evidence.verify", payload, {"verified": verified, "conclusion": conclusion})

    # ---------- policy ----------

    def policy_query_after_sales(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        policy = self.scenario.get("policy", {})
        rules = policy.get("rules", [])
        scenario = payload.get("scenario") or self.scenario_id
        applicable = [r for r in rules if scenario in r.get("applicable_scenarios", [])] or rules
        return self._record(
            "policy.query_after_sales",
            payload,
            {"category": policy.get("category"), "scenario": scenario, "applicable": True, "rules": applicable},
        )

    # ---------- refund ----------

    def refund_query_history(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        history = self.scenario.get("refund_history", [])
        total = sum(float(r.get("amount", 0)) for r in history)
        return self._record(
            "refund.query_history",
            payload,
            {
                "order_id": payload.get("order_id"),
                "customer_id": payload.get("customer_id"),
                "refunds": history,
                "total_refunded": round(total, 2),
                "after_sales_count": self.scenario.get("customer", {}).get("after_sales_count", len(history)),
            },
        )

    def refund_calc_max_amount(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order = self._find_order(payload.get("order_id", ""))
        if order is None:
            return self._record("refund.calc_max_amount", payload, {"found": False, "order_id": payload.get("order_id")})
        shipped = set(order.get("shipped_items", []))
        payment = self._find_payment(order["order_id"])
        total = sum(item["unit_price"] * item["quantity"] for item in order["items"])
        paid = payment.get("paid_amount", total) if payment else total
        # 只有显式声明了 shipped_items 且数量少于下单商品时，才按少件差价计算
        if "shipped_items" in order and len(shipped) < len(order["items"]):
            missing = sum(
                item["unit_price"] * item["quantity"]
                for item in order["items"]
                if item["product_id"] not in shipped
            )
            max_amount, basis = missing, f"少件商品差价 {missing:.2f} 元"
        else:
            max_amount, basis = paid, f"订单实付 {paid:.2f} 元"
        return self._record(
            "refund.calc_max_amount",
            payload,
            {"order_id": order["order_id"], "max_amount": round(max_amount, 2), "basis": basis},
        )

    def refund_submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        key = payload.get("idempotency_key")
        dup = self._idempotent_guard(key)
        if dup is not None:
            return self._record("refund.submit", payload, {**dup, "duplicated": True})
        refund_id = self._seq("RF")
        result = {
            "refund_id": refund_id,
            "case_id": payload.get("case_id"),
            "order_id": payload.get("order_id"),
            "amount": payload.get("amount", 0),
            "status": "已提交",
            "submitted_at": _now(),
            "message": "退款已提交，等待资金到账。",
        }
        self.refunds[refund_id] = result
        self.actions.append({"action": "refund_submit", **result})
        return self._record("refund.submit", payload, self._idempotent_commit(key, result))

    def refund_query_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        refund_id = payload.get("refund_id", "")
        refund = self.refunds.get(refund_id)
        if refund is None:
            return self._record("refund.query_status", payload, {"refund_id": refund_id, "found": False})
        return self._record(
            "refund.query_status",
            payload,
            {
                "refund_id": refund_id,
                "case_id": refund["case_id"],
                "amount": refund["amount"],
                "status": "已到账",
                "refunded_at": _now(),
            },
        )

    # ---------- approval ----------

    def approval_create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task_id = self._seq("AP")
        result = {
            "task_id": task_id,
            "case_id": payload.get("case_id"),
            "title": payload.get("title", ""),
            "details": payload.get("details", {}),
            "status": "pending",
            "created_at": _now(),
        }
        self.approvals[task_id] = result
        self.actions.append({"action": "create_approval_task", **result})
        return self._record("approval.create_task", payload, result)

    def approval_query_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task_id = payload.get("task_id")
        task = self.approvals.get(task_id) if task_id else None
        if task is None:
            case_id = payload.get("case_id")
            for candidate in self.approvals.values():
                if candidate["case_id"] == case_id:
                    task = candidate
                    task_id = candidate["task_id"]
                    break
        if task is None:
            return self._record(
                "approval.query_status", payload, {"task_id": task_id, "found": False, "status": "not_found"}
            )
        # demo 模拟：商家审批自动通过，使 L2 动作可以闭环执行
        return self._record(
            "approval.query_status",
            payload,
            {
                "task_id": task_id,
                "case_id": task["case_id"],
                "title": task["title"],
                "found": True,
                "status": "approved",
                "approved_by": "商家管理员",
                "note": "审批通过（demo 模拟）",
            },
        )

    # ---------- case ----------

    def case_create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_id = payload.get("case_id", "")
        if case_id in self.cases:
            return self._record("case.create", payload, {"case_id": case_id, "status": "already_exists"})
        self.cases[case_id] = {**payload, "created_at": _now()}
        return self._record(
            "case.create", payload, {"case_id": case_id, "status": "created", "created_at": _now()}
        )

    def case_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_id = payload.get("case_id", "")
        fields = payload.get("fields", {})
        if case_id in self.cases:
            self.cases[case_id].update(fields)
        return self._record(
            "case.update",
            payload,
            {"case_id": case_id, "status": "updated", "updated_fields": list(fields.keys())},
        )

    def case_update_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_id = payload.get("case_id", "")
        status = payload.get("status", "")
        if case_id in self.cases:
            self.cases[case_id]["status"] = status
        return self._record("case.update_status", payload, {"case_id": case_id, "status": status})

    def case_close(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_id = payload.get("case_id", "")
        if case_id in self.cases:
            self.cases[case_id]["status"] = "closed"
        return self._record(
            "case.close",
            payload,
            {"case_id": case_id, "status": "closed", "note": payload.get("note", ""), "closed_at": _now()},
        )

    # ---------- message ----------

    def message_notify_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        message_id = self._seq("MSG")
        result = {
            "message_id": message_id,
            "case_id": payload.get("case_id"),
            "channel": payload.get("channel", "app"),
            "content": payload.get("content", ""),
            "sent": True,
        }
        self.messages.append(result)
        return self._record("message.notify_customer", payload, result)
