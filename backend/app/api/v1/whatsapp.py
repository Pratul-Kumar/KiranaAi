from fastapi import APIRouter, Request, Header, HTTPException, Depends, Query
from fastapi.responses import Response
from app.core.config import get_settings
from app.services.ai.ai_service import AIServiceLayer
from app.services.inventory_service import InventoryOrchestrator
from app.services.khata_service import KhataService
from app.services.whatsapp_service import WhatsAppService
from app.db.supabase import get_supabase_client
from app.schemas.ai_schemas import IntentEnum
import logging
import json
import os

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

DEBUG_LOG = "whatsapp_webhook_debug.log"

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge)
    return Response(status_code=403)

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    ai_service: AIServiceLayer = Depends(AIServiceLayer),
    inventory_service: InventoryOrchestrator = Depends(InventoryOrchestrator),
    khata_service: KhataService = Depends(KhataService),
    whatsapp_service: WhatsAppService = Depends(WhatsAppService)
):
    body = await request.json()
    
    # LOG EVERYTHING TO FILE
    with open(DEBUG_LOG, "a") as f:
        f.write(f"\n--- WEBHOOK RECEIVED {json.dumps(body)} ---\n")

    try:
        entry = body.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        value = change.get("value", {})
        
        if "messages" not in value:
            return {"status": "event_received"}

        message = value["messages"][0]
        from_phone = message["from"]
        msg_body = ""
        
        if message["type"] == "text":
            msg_body = message["text"]["body"]
        elif message["type"] == "interactive":
            # Handle Button Reply
            msg_body = message["interactive"]["button_reply"]["title"]
            button_id = message["interactive"]["button_reply"]["id"]
            with open(DEBUG_LOG, "a") as f:
                f.write(f"BUTTON CLICK: {button_id} ({msg_body})\n")
        
        with open(DEBUG_LOG, "a") as f:
            f.write(f"SENDER: {from_phone} | BODY: {msg_body}\n")

        # 1. Role Detection
        db = get_supabase_client()
        role = "unknown"
        store_id = None
        store_data = {}
        
        # OWNER CHECK
        store_res = db.table("stores").select("*").eq("contact_phone", from_phone).execute()
        if store_res.data:
            role = "owner"
            store_data = store_res.data[0]
            store_id = store_data["id"]
        else:
            # SUPPLIER CHECK
            supplier_res = db.table("suppliers").select("*").eq("phone", from_phone).execute()
            if supplier_res.data:
                role = "supplier"
                supplier_data = supplier_res.data[0]
                store_id = supplier_data["store_id"]
                # Fetch store info
                store_res = db.table("stores").select("*").eq("id", store_id).execute()
                if store_res.data:
                    store_data = store_res.data[0]

        with open(DEBUG_LOG, "a") as f:
            f.write(f"DETECTED ROLE: {role} | STORE_ID: {store_id}\n")

        if not store_id:
            with open(DEBUG_LOG, "a") as f:
                f.write(f"ERROR: Unauthorized sender {from_phone}\n")
            return {"status": "unauthorized"}

        # 2. Process AI (Only if text message, not button click)
        if message["type"] == "text":
            ai_result = await ai_service.process_text_message(msg_body)
        else:
            # For button clicks, we don't need the SLM to process intent
            from app.schemas.ai_schemas import AIIntentResponse
            ai_result = AIIntentResponse(intent=IntentEnum.UNKNOWN, confidence=1.0, original_text=msg_body, sku="", quantity=0)

        with open(DEBUG_LOG, "a") as f:
            f.write(f"AI INTENT: {ai_result.intent} | SKU: {ai_result.sku}\n")

        # 3. Routing
        response = {}
        if role == "owner":
            if ai_result.intent == IntentEnum.REORDER:
                # Find Supplier by SKU category
                sku_res = db.table("skus").select("*").ilike("name", f"%{ai_result.sku}%").eq("store_id", store_id).execute()
                sku_data = sku_res.data[0] if sku_res.data else None
                cat = sku_data["category_path"] if sku_data else None
                
                if cat:
                    supp_res = db.table("suppliers").select("*").eq("store_id", store_id).eq("category", cat).execute()
                    if supp_res.data:
                        supplier = supp_res.data[0]
                        
                        # FETCH LAST AGREED PRICE
                        last_price_res = db.table("reorder_requests").select("unit_price").eq("supplier_id", supplier["id"]).eq("sku_name", ai_result.sku).not_.is_("unit_price", "null").order("created_at", desc=True).limit(1).execute()
                        last_price = last_price_res.data[0]["unit_price"] if last_price_res.data else None
                        
                        # PERSIST THE ORDER REQUEST
                        total = (float(last_price) * float(ai_result.quantity or 1)) if last_price else None
                        order_req = db.table("reorder_requests").insert({
                            "store_id": store_id,
                            "supplier_id": supplier["id"],
                            "sku_name": ai_result.sku,
                            "quantity": ai_result.quantity or 1,
                            "unit_price": last_price,
                            "total_amount": total,
                            "status": "pending"
                        }).execute()
                        
                        order_id = order_req.data[0]["id"]
                        
                        price_display = f"Price: ₹{last_price} (Last agreed)" if last_price else "Price: Not set"
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
                        # SENT WITH UNIQUE BUTTON IDs
                        buttons = [
                            {"id": f"approve_{order_id}", "title": "Approve"},
                            {"id": f"update_{order_id}", "title": "Update Price"},
                            {"id": f"decline_{order_id}", "title": "Decline"}
                        ]
                        await whatsapp_service.send_button_message(supplier["phone"], reorder_msg, buttons)
                        
                        response = {"status": "distributor_notified", "supplier": supplier["name"]}
                        with open(DEBUG_LOG, "a") as f:
                            f.write(f"ORDER TRACKED: {order_id} | Notified {supplier['name']}\n")
            
            elif ai_result.intent == IntentEnum.STOCK_UPDATE:
                response = await inventory_service.update_stock(ai_result, store_id)

        elif role == "supplier":
            # Handle Text Messages (potential price updates)
            if message["type"] == "text":
                # Check if this supplier has a 'pending_price' order
                pending_res = db.table("reorder_requests").select("*").eq("supplier_id", supplier_data["id"]).eq("status", "pending_price").order("updated_at", desc=True).limit(1).execute()
                
                if pending_res.data:
                    order = pending_res.data[0]
                    try:
                        new_price = float(msg_body.strip())
                        total = new_price * float(order["quantity"])
                        
                        db.table("reorder_requests").update({
                            "unit_price": new_price,
                            "total_amount": total,
                            "status": "pending" # Reset to pending for approval
                        }).eq("id", order["id"]).execute()
                        
                        confirm_msg = f"✅ Price updated to ₹{new_price}.\nTotal: ₹{total}.\n\nPlease Approve or Decline now."
                        buttons = [
                            {"id": f"approve_{order['id']}", "title": "Approve"},
                            {"id": f"decline_{order['id']}", "title": "Decline"}
                        ]
                        await whatsapp_service.send_button_message(from_phone, confirm_msg, buttons)
                        return {"status": "price_updated"}
                    except ValueError:
                        await whatsapp_service.send_text_message(from_phone, "❌ Invalid price. Please send a number (e.g., 50).")
                        return {"status": "invalid_input"}

            # Handle Button Responses
            if message["type"] == "interactive":
                button_id = message["interactive"]["button_reply"]["id"]
                
                # Format: action_orderid
                parts = button_id.split("_")
                action = parts[0]
                order_id = parts[1] if len(parts) > 1 else None

                if not order_id:
                    return {"status": "invalid_button"}

                # Fetch Order State
                order_res = db.table("reorder_requests").select("*").eq("id", order_id).execute()
                if not order_res.data:
                    return {"status": "order_not_found"}
                
                order = order_res.data[0]
                
                if action == "approve":
                    if order["status"] not in ["pending", "pending_price"]:
                        await whatsapp_service.send_text_message(from_phone, f"⚠️ This order was already {order['status']}.")
                        return {"status": "already_processed"}
                    
                    # Update State
                    db.table("reorder_requests").update({"status": "approved"}).eq("id", order_id).execute()
                    
                    # Notify Owner
                    price_info = f" at ₹{order['unit_price']}" if order.get('unit_price') else ""
                    await whatsapp_service.send_text_message(store_data["contact_phone"], f"🔔 *APPROVED*: {store_data['name']} distributor accepted order for {order['sku_name']}{price_info}.")
                    
                    # Notify Distributor & Provide Billing Option
                    bill_msg = f"✅ Order {str(order_id)[:8]} Approved.\n\nYou can now generate the bill."
                    bill_buttons = [{"id": f"genbill_{order_id}", "title": "Generate Bill"}]
                    await whatsapp_service.send_button_message(from_phone, bill_msg, bill_buttons)
                    response = {"status": "processed"}

                elif action == "update":
                    # Put order in pending_price state
                    db.table("reorder_requests").update({"status": "pending_price"}).eq("id", order_id).execute()
                    await whatsapp_service.send_text_message(from_phone, f"Please send the new unit price for {order['sku_name']}:")
                    return {"status": "awaiting_price"}

                elif action == "decline":
                    if order["status"] not in ["pending", "pending_price"]:
                        await whatsapp_service.send_text_message(from_phone, f"⚠️ This order was already {order['status']}.")
                        return {"status": "already_processed"}
                        
                    db.table("reorder_requests").update({"status": "declined"}).eq("id", order_id).execute()
                    await whatsapp_service.send_text_message(store_data["contact_phone"], f"❌ *DECLINED*: Distributor rejected order for {order['sku_name']}.")
                    await whatsapp_service.send_text_message(from_phone, "Order declined.")
                    response = {"status": "processed"}

                elif action == "genbill":
                    # Billing Logic
                    total = order.get('total_amount') or 0
                    price = order.get('unit_price') or "N/A"
                    qty = int(order['quantity']) if float(order['quantity']).is_integer() else order['quantity']
                    
                    bill_text = (
                        f"📜 *TAX INVOICE*\n"
                        f"Inv: BILL-{str(order_id)[:6]}\n"
                        f"--------------------------\n"
                        f"To: {store_data['name']}\n"
                        f"Item: {order['sku_name']}\n"
                        f"Qty: {qty}\n"
                        f"Price: ₹{price}\n"
                        f"Total: ₹{total}\n"
                        f"Status: PAID/PENDING\n"
                        f"--------------------------\n"
                        f"Thank you for your business!"
                    )
                    # 1. Send to Distributor
                    await whatsapp_service.send_text_message(from_phone, bill_text)
                    
                    # 2. Automatically Share with Owner
                    owner_bill_text = f"📄 *INVOICE RECEIVED* from {supplier_data['name']}\n\n" + bill_text
                    await whatsapp_service.send_text_message(store_data["contact_phone"], owner_bill_text)
                    
                    response = {"status": "bill_generated"}

        # 4. Feedback to the Sender
        if message["type"] == "text" and role == "owner":
            reply = "Received."
            if response.get("status") == "distributor_notified":
                reply = f"✅ Order sent to {response['supplier']} with interactive options."
            await whatsapp_service.send_text_message(from_phone, reply)
        
        return {"status": "success"}
        
        return {"status": "success"}

    except Exception as e:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"CRITICAL ERROR: {str(e)}\n")
        return {"status": "error", "detail": str(e)}
