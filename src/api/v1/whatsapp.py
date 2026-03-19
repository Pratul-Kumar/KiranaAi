import logging

from fastapi import APIRouter, Query, Request, Response

from configs.config import get_settings
from src.db.supabase import get_supabase_client
from src.models.schemas import AIIntentResponse, IntentEnum
from src.inference.ai_service import AIServiceLayer
from src.services.inventory_service import InventoryOrchestrator
from src.services.khata_service import KhataService
from src.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger(__name__)
settings = get_settings()

_ai_service = AIServiceLayer()
_inventory_service = InventoryOrchestrator()
_khata_service = KhataService()
_whatsapp_service = WhatsAppService()


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge)
    return Response(status_code=403)


@router.post("/webhook")
async def whatsapp_webhook(request: Request) -> dict:
    body = await request.json()
    logger.debug(f"Webhook received: {body}")

    try:
        entry = body.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        value = change.get("value", {})

        if "messages" not in value:
            return {"status": "event_received"}

        message = value["messages"][0]
        from_phone = message["from"]
        msg_type = message["type"]
        msg_body = ""
        button_id = None

        if msg_type == "text":
            msg_body = message["text"]["body"]
        elif msg_type == "interactive":
            msg_body = message["interactive"]["button_reply"]["title"]
            button_id = message["interactive"]["button_reply"]["id"]
            logger.info(f"Button click: id={button_id} title={msg_body}")

        logger.info(f"Incoming message: from={from_phone} type={msg_type} body={msg_body!r}")

        # --- Role detection ---
        db = get_supabase_client()
        role = "unknown"
        store_id = None
        store_data = {}
        supplier_data = {}

        store_res = db.table("stores").select("*").eq("contact_phone", from_phone).execute()
        if store_res.data:
            role = "owner"
            store_data = store_res.data[0]
            store_id = store_data["id"]
        else:
            supplier_res = db.table("vendors").select("*").eq("phone", from_phone).execute()
            if supplier_res.data:
                role = "supplier"
                supplier_data = supplier_res.data[0]
                store_id = supplier_data.get("store_id")
                if store_id:
                    sr = db.table("stores").select("*").eq("id", store_id).execute()
                    store_data = sr.data[0] if sr.data else {}

        logger.info(f"Detected role={role} store_id={store_id}")

        if not store_id:
            logger.warning(f"Unauthorized sender: {from_phone}")
            return {"status": "unauthorized"}

        # --- AI intent (text only; buttons skip the SLM) ---
        if msg_type == "text":
            ai_result = await _ai_service.process_text_message(msg_body)
        else:
            ai_result = AIIntentResponse(
                intent=IntentEnum.UNKNOWN,
                confidence=1.0,
                original_text=msg_body,
            )

        logger.info(f"AI intent={ai_result.intent} sku={ai_result.sku} conf={ai_result.confidence:.2f}")

        # --- Routing ---
        response: dict = {}

        if role == "owner":
            if ai_result.intent == IntentEnum.REORDER:
                sku_res = db.table("skus").select("*").ilike("name", f"%{ai_result.sku}%").eq("store_id", store_id).execute()
                sku_data = sku_res.data[0] if sku_res.data else None
                cat = sku_data["category_path"] if sku_data else None

                if cat:
                    supp_res = db.table("vendors").select("*").eq("store_id", store_id).eq("category", cat).execute()
                    if supp_res.data:
                        supplier = supp_res.data[0]

                        last_price_res = (
                            db.table("reorder_requests")
                            .select("unit_price")
                            .eq("supplier_id", supplier["id"])
                            .eq("sku_name", ai_result.sku)
                            .not_.is_("unit_price", "null")
                            .order("created_at", desc=True)
                            .limit(1)
                            .execute()
                        )
                        last_price = last_price_res.data[0]["unit_price"] if last_price_res.data else None
                        total = (float(last_price) * float(ai_result.quantity or 1)) if last_price else None

                        order_req = db.table("reorder_requests").insert({
                            "store_id": store_id,
                            "supplier_id": supplier["id"],
                            "sku_name": ai_result.sku,
                            "quantity": ai_result.quantity or 1,
                            "unit_price": last_price,
                            "total_amount": total,
                            "status": "pending",
                        }).execute()

                        order_id = order_req.data[0]["id"]
                        price_display = f"Price: ₹{last_price} (last agreed)" if last_price else "Price: Not set"

                        reorder_msg = (
                            f"📦 *REORDER REQUEST*\n"
                            f"Order ID: {str(order_id)[:8]}\n"
                            f"Store: {store_data['name']}\n"
                            f"Location: {store_data.get('address', 'N/A')}\n\n"
                            f"Item: {ai_result.sku}\n"
                            f"Qty: {ai_result.quantity or 1}\n"
                            f"{price_display}\n\n"
                            f"Please approve or decline."
                        )
                        buttons = [
                            {"id": f"approve_{order_id}", "title": "Approve"},
                            {"id": f"update_{order_id}", "title": "Update Price"},
                            {"id": f"decline_{order_id}", "title": "Decline"},
                        ]
                        await _whatsapp_service.send_button_message(supplier["phone"], reorder_msg, buttons)
                        logger.info(f"Reorder {order_id} sent to supplier {supplier['name']}")
                        response = {"status": "distributor_notified", "supplier": supplier["name"]}

            elif ai_result.intent == IntentEnum.STOCK_UPDATE:
                response = await _inventory_service.update_stock(ai_result, store_id)

        elif role == "supplier":
            if msg_type == "text":
                pending_res = (
                    db.table("reorder_requests")
                    .select("*")
                    .eq("supplier_id", supplier_data["id"])
                    .eq("status", "pending_price")
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if pending_res.data:
                    order = pending_res.data[0]
                    try:
                        new_price = float(msg_body.strip())
                        total = new_price * float(order["quantity"])
                        db.table("reorder_requests").update({
                            "unit_price": new_price,
                            "total_amount": total,
                            "status": "pending",
                        }).eq("id", order["id"]).execute()

                        confirm_msg = f"✅ Price updated to ₹{new_price}.\nTotal: ₹{total}.\n\nPlease Approve or Decline now."
                        buttons = [
                            {"id": f"approve_{order['id']}", "title": "Approve"},
                            {"id": f"decline_{order['id']}", "title": "Decline"},
                        ]
                        await _whatsapp_service.send_button_message(from_phone, confirm_msg, buttons)
                        return {"status": "price_updated"}
                    except ValueError:
                        await _whatsapp_service.send_text_message(from_phone, "❌ Invalid price. Please send a number (e.g., 50).")
                        return {"status": "invalid_input"}

            if msg_type == "interactive" and button_id:
                parts = button_id.split("_", 1)
                if len(parts) != 2:
                    return {"status": "invalid_button"}

                action, order_id = parts[0], parts[1]

                order_res = db.table("reorder_requests").select("*").eq("id", order_id).execute()
                if not order_res.data:
                    return {"status": "order_not_found"}

                order = order_res.data[0]

                if action == "approve":
                    if order["status"] not in ("pending", "pending_price"):
                        await _whatsapp_service.send_text_message(from_phone, f"⚠️ Order already {order['status']}.")
                        return {"status": "already_processed"}

                    db.table("reorder_requests").update({"status": "approved"}).eq("id", order_id).execute()
                    price_info = f" at ₹{order['unit_price']}" if order.get("unit_price") else ""
                    await _whatsapp_service.send_text_message(
                        store_data["contact_phone"],
                        f"🔔 *APPROVED*: Distributor accepted order for {order['sku_name']}{price_info}.",
                    )
                    bill_msg = f"✅ Order {str(order_id)[:8]} Approved.\n\nYou can now generate the bill."
                    await _whatsapp_service.send_button_message(
                        from_phone, bill_msg, [{"id": f"genbill_{order_id}", "title": "Generate Bill"}]
                    )
                    response = {"status": "approved"}

                elif action == "update":
                    db.table("reorder_requests").update({"status": "pending_price"}).eq("id", order_id).execute()
                    await _whatsapp_service.send_text_message(from_phone, f"Please send the new unit price for {order['sku_name']}:")
                    return {"status": "awaiting_price"}

                elif action == "decline":
                    if order["status"] not in ("pending", "pending_price"):
                        await _whatsapp_service.send_text_message(from_phone, f"⚠️ Order already {order['status']}.")
                        return {"status": "already_processed"}

                    db.table("reorder_requests").update({"status": "declined"}).eq("id", order_id).execute()
                    await _whatsapp_service.send_text_message(
                        store_data["contact_phone"],
                        f"❌ *DECLINED*: Distributor rejected order for {order['sku_name']}.",
                    )
                    await _whatsapp_service.send_text_message(from_phone, "Order declined.")
                    response = {"status": "declined"}

                elif action == "genbill":
                    total = order.get("total_amount") or 0
                    price = order.get("unit_price") or "N/A"
                    qty_raw = order["quantity"]
                    qty = int(qty_raw) if float(qty_raw).is_integer() else qty_raw

                    bill_text = (
                        f"📜 *TAX INVOICE*\n"
                        f"Inv: BILL-{str(order_id)[:6]}\n"
                        f"--------------------------\n"
                        f"To: {store_data['name']}\n"
                        f"Item: {order['sku_name']}\n"
                        f"Qty: {qty}\n"
                        f"Price: ₹{price}\n"
                        f"Total: ₹{total}\n"
                        f"--------------------------\n"
                        f"Thank you for your business!"
                    )
                    await _whatsapp_service.send_text_message(from_phone, bill_text)
                    await _whatsapp_service.send_text_message(
                        store_data["contact_phone"],
                        f"📄 *INVOICE RECEIVED* from {supplier_data.get('name', 'Supplier')}\n\n{bill_text}",
                    )
                    response = {"status": "bill_generated"}

        # --- Acknowledge text messages to owner ---
        if msg_type == "text" and role == "owner":
            reply = "Received."
            if response.get("status") == "distributor_notified":
                reply = f"✅ Order sent to {response['supplier']} for approval."
            await _whatsapp_service.send_text_message(from_phone, reply)

        return {"status": "success"}

    except Exception as exc:
        logger.exception(f"Webhook processing error: {exc}")
        return {"status": "error", "detail": str(exc)}
