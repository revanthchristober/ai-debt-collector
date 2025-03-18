import stripe
import requests
import pytz
from datetime import datetime
from celery import shared_task
from django.conf import settings

# Set Stripe API key from Django settings
stripe.api_key = settings.STRIPE_API_KEY

# Build Airtable API URL and headers
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_CONTACTS_TABLE_ID}"
HEADERS = {
    'Authorization': f"Bearer {settings.AIRTABLE_API_KEY}",
    'Content-Type': 'application/json'
}

def get_brisbane_time():
    tz = pytz.timezone("Australia/Brisbane")
    return datetime.now(tz)

def is_business_hours():
    now = get_brisbane_time()
    # Business hours: Monday-Friday, 7:00 to 19:00 Brisbane time
    return now.weekday() < 5 and 7 <= now.hour < 19

def fetch_new_contacts():
    try:
        response = requests.get(AIRTABLE_API_URL, headers=HEADERS)
        response.raise_for_status()
        records = response.json().get('records', [])
        # Filter records with PROCESS == 'new' and no paylink
        new_contacts = [
            record for record in records
            if record.get("fields", {}).get("PROCESS") == "new" and not record.get("fields", {}).get("paylink")
        ]
        print(f"Fetched {len(new_contacts)} new contacts.")
        return new_contacts
    except Exception as e:
        print("Error fetching contacts from Airtable:", e)
        return []

def create_stripe_customer(contact):
    fields = contact.get("fields", {})
    try:
        customer = stripe.Customer.create(
            name=fields.get("Name"),
            email=fields.get("Email"),
            metadata={
                "debitor": fields.get("Debitor name"),
                "ref_id": fields.get("Client REF ID")
            }
        )
        print(f"Stripe customer created: {customer.id} for {fields.get('Name')}")
        return customer.id
    except Exception as e:
        print("Error creating Stripe customer:", e)
        return None

def create_stripe_price(contact):
    fields = contact.get("fields", {})
    overdue_amount = fields.get("Overdue amount")
    if overdue_amount is None:
        print(f"Missing 'Overdue amount' for {fields.get('Name')}")
        return None

    amount = int(float(overdue_amount) * 100)  # Convert to cents
    try:
        price = stripe.Price.create(
            unit_amount=amount,
            currency="aud",
            product="prod_QbFLLPk2A67lJi"  # Update with your actual product ID
        )
        print(f"Stripe price created: {price.id} for {fields.get('Name')}")
        return price.id
    except Exception as e:
        print("Error creating Stripe price:", e)
        return None

def create_or_update_payment_link(contact, price_id):
    fields = contact.get("fields", {})
    try:
        if fields.get("paylink"):
            payment_link = stripe.PaymentLink.modify(
                fields.get("paylink"),
                line_items=[{"price": price_id, "quantity": 1}],
                metadata={
                    "customer_email": fields.get("Email"),
                    "customer_id": fields.get("Client REF ID"),
                    "customer_name": fields.get("Name")
                },
                payment_method_types=["card", "afterpay_clearpay", "link", "zip"],
                allow_promotion_codes=True,
                invoice_creation={
                    "enabled": True,
                    "invoice_data": {
                        "description": f"Invoice for {fields.get('Name')}",
                        "metadata": {
                            "Customer Email": fields.get("Email"),
                            "Customer ID": fields.get("Client REF ID")
                        }
                    }
                },
                shipping_address_collection={"allowed_countries": ["AU", "US", "CA", "GB", "NZ"]},
                billing_address_collection="required",
                phone_number_collection={"enabled": True},
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": "https://example.com/success"}
                }
            )
        else:
            payment_link = stripe.PaymentLink.create(
                line_items=[{"price": price_id, "quantity": 1}],
                metadata={
                    "customer_email": fields.get("Email"),
                    "customer_id": fields.get("Client REF ID"),
                    "customer_name": fields.get("Name")
                },
                payment_method_types=["card", "afterpay_clearpay", "link", "zip"],
                allow_promotion_codes=True,
                invoice_creation={
                    "enabled": True,
                    "invoice_data": {
                        "description": f"Invoice for {fields.get('Name')}",
                        "metadata": {
                            "Customer Email": fields.get("Email"),
                            "Customer ID": fields.get("Client REF ID")
                        }
                    }
                },
                shipping_address_collection={"allowed_countries": ["AU", "US", "CA", "GB", "NZ"]},
                billing_address_collection="required",
                phone_number_collection={"enabled": True},
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": "https://example.com/success"}
                }
            )
        print(f"Payment link for {fields.get('Name')}: {payment_link.url}")
        return payment_link.url
    except Exception as e:
        print("Error creating/updating payment link:", e)
        return None

def update_airtable(contact_id, update_fields):
    try:
        url = f"{AIRTABLE_API_URL}/{contact_id}"
        data = {"fields": update_fields}
        response = requests.patch(url, json=data, headers=HEADERS)
        response.raise_for_status()
        print(f"Airtable record {contact_id} updated.")
    except Exception as e:
        print(f"Error updating Airtable record {contact_id}:", e)

@shared_task
def process_contacts_task():
    if not is_business_hours():
        print("Outside business hours. Task skipped.")
        return

    contacts = fetch_new_contacts()
    if not contacts:
        print("No new contacts found.")
        return

    for contact in contacts:
        contact_id = contact.get("id")
        print(f"Processing contact {contact_id} - {contact.get('fields', {}).get('Name')}")
        customer_id = create_stripe_customer(contact)
        if not customer_id:
            print(f"Skipping contact {contact_id} due to Stripe customer creation failure.")
            continue

        price_id = create_stripe_price(contact)
        if not price_id:
            print(f"Skipping contact {contact_id} due to Stripe price creation failure.")
            continue

        payment_link = create_or_update_payment_link(contact, price_id)
        if payment_link:
            update_fields = {
                "paylink": payment_link,
                "PROCESS": "START",
                "Stripe Log in": "https://billing.stripe.com/p/login/fZe5o106saRx6ZO3cc",
                "Stripe REF ID": customer_id
            }
            update_airtable(contact_id, update_fields)
        else:
            print(f"Failed to create payment link for contact {contact_id}.")
