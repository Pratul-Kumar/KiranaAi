import httpx
import asyncio
import json

async def simulate_webhook():
    url = "http://localhost:8005/api/v1/whatsapp/webhook"
    
    # Example 1: Stock Update
    stock_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "15551551425",
                        "type": "text",
                        "text": {"body": "5 packet milk update karo"}
                    }]
                }
            }]
        }]
    }
    
    print("Testing Stock Update from +1 555 155 1425...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=stock_payload)
            print(f"Status: {response.status_code}")
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Raw Response: {response.text}")
        except Exception as e:
            print(f"Detailed Error: {type(e).__name__}: {e}")

    print("\n" + "-"*30 + "\n")

    # Example 2: Lost Sale
    lost_sale_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "15551551425",
                        "type": "text",
                        "text": {"body": "Customer asked for 2kg Basmati Rice, but none in stock"}
                    }]
                }
            }]
        }]
    }
    
    print("Testing Lost Sale from +1 555 155 1425...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=lost_sale_payload, headers={"X-Hub-Signature": "sha256=test_sig"})
            print(f"Status: {response.status_code}")
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Raw Response: {response.text}")
        except Exception as e:
            print(f"Detailed Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_webhook())
