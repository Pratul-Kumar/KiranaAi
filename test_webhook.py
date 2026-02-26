import httpx
import asyncio
import json

async def simulate_webhook():
    url = "http://localhost:8004/api/v1/whatsapp/webhook"
    
    # Example 1: Stock Update
    stock_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919876543210",
                        "type": "text",
                        "text": {"body": "5 packet milk update karo"}
                    }]
                }
            }]
        }]
    }
    
    print("Testing Stock Update...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=stock_payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "-"*30 + "\n")

    # Example 2: Lost Sale
    lost_sale_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919876543210",
                        "type": "text",
                        "text": {"body": "Customer asked for 2kg Basmati Rice, but none in stock"}
                    }]
                }
            }]
        }]
    }
    
    print("Testing Lost Sale...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=lost_sale_payload, headers={"X-Hub-Signature": "sha256=test_sig"})
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_webhook())
