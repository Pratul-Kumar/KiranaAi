# 📲 How to Enable WhatsApp Integration

To connect your Digital Store Manager to a real WhatsApp number, you need to set up the **WhatsApp Business Platform** via the Meta Developer Portal.

---

## 1. Create a Meta Developer App
1. Go to the [Meta for Developers](https://developers.facebook.com/) portal.
2. Click **My Apps** > **Create App**.
3. Select **Other** > **Business** as the app type.
4. Add **WhatsApp** to your app from the dashboard.

## 2. Get Your Credentials
1. In the left sidebar, navigate to **WhatsApp** > **API Setup**.
2. **Temporary Access Token**: Copy this token (valid for 24 hours). You'll need this for `WHATSAPP_ACCESS_TOKEN` in your `.env`.
3. **Phone Number ID**: Note this down; it's used when sending messages from the API.

## 3. Set Up the Webhook
Since Meta needs to send messages *to* your backend, your server must be reachable over the internet with **HTTPS**.

### A. Local Testing (using ngrok)
1. Run `ngrok http 8000`.
2. Copy the `https://...` URL.
3. Your Webhook URL will be: `https://<your-ngrok-url>/api/v1/whatsapp/webhook`.

### B. Meta Configuration
1. Go to **WhatsApp** > **Configuration**.
2. Click **Edit** under Webhook.
3. **Callback URL**: Paste your Webhook URL from the step above.
4. **Verify Token**: Enter the value you set for `WHATSAPP_VERIFY_TOKEN` in your `.env` (default is `digital_store_manager_verify`).
5. Click **Verify and Save**. Meta will send a GET request to your backend, which our code is already configured to handle.

## 4. Subscribe to Message Events
1. In the same **Configuration** section, look for **Webhook fields**.
2. Click **Manage**.
3. Subscribe to the `messages` field. This ensures your backend receives a notification every time someone sends a message to your WhatsApp business number.

## 5. Update Your `.env`
Ensure these values match your Meta App settings:
```bash
WHATSAPP_VERIFY_TOKEN="your_custom_verify_token"
WHATSAPP_ACCESS_TOKEN="your_meta_access_token"
```

---

## 🧪 Testing the Connection
1. Send a text or audio message (e.g., *"5 packet milk update karo"*) to the test phone number provided in the **API Setup** page.
2. Check your backend logs to see the SLM extracting the intent and updating the Supabase database in real-time!

> [!TIP]
> Always use a Permanent Access Token for production. You can generate one by creating a **System User** in your Meta Business Suite.
