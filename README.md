# Masaki Payment Platform

A Django-based single-user payment platform with:

- Secure Django authentication and registration
- Safaricom Daraja STK push initiation with environment-based configuration
- Transaction logging and daily total aggregation
- A dashboard with completed/pending payment status views
- PDF report generation for historical transactions

## Quick start

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Daraja configuration

Set the following environment variables before initiating payments:

```bash
export DARAJA_CONSUMER_KEY="your_consumer_key"
export DARAJA_CONSUMER_SECRET="your_consumer_secret"
export DARAJA_SHORT_CODE="your_short_code"
export DARAJA_PASSKEY="your_passkey"
export DARAJA_CALLBACK_URL="https://your-domain.com/callback/"
```

If these values are absent, the app falls back to a safe demo mode so development can continue without breaking the flow.
