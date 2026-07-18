# facturacion/integrations/stripe_service.py
# Integración con Stripe.

import stripe
from django.conf import settings
from decimal import Decimal

stripe.api_key = settings.STRIPE_SECRET_KEY


def crear_customer_stripe(email, nombre):
    """Crea un customer en Stripe."""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=nombre,
        )
        return customer
    except stripe.error.StripeError as e:
        print(f"Error creando customer: {e}")
        return None


def crear_payment_intent(monto, moneda="PEN", customer_id=None):
    """Crea un PaymentIntent para un cobro único."""
    try:
        monto_centavos = int(Decimal(str(monto)) * 100)
        intent_data = {
            "amount": monto_centavos,
            "currency": moneda,
            "payment_method_types": ["card"],
        }
        if customer_id:
            intent_data["customer"] = customer_id
        intent = stripe.PaymentIntent.create(**intent_data)
        return intent
    except stripe.error.StripeError as e:
        print(f"Error creando PaymentIntent: {e}")
        return None


def crear_suscripcion_stripe(customer_id, price_id):
    """Crea una suscripción recurrente en Stripe."""
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        return subscription
    except stripe.error.StripeError as e:
        print(f"Error creando suscripción: {e}")
        return None


def confirmar_pago_stripe(payment_intent_id):
    """Confirma un pago en Stripe."""
    try:
        intent = stripe.PaymentIntent.confirm(payment_intent_id)
        return intent
    except stripe.error.StripeError as e:
        print(f"Error confirmando pago: {e}")
        return None


def verificar_webhook(payload, sig_header):
    """Verifica la firma de un webhook de Stripe."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        print(f"Error verificando webhook: {e}")
        return None


def reembolsar_pago(payment_intent_id, monto=None):
    """Procesa un reembolso a través de Stripe."""
    try:
        refund_data = {"payment_intent": payment_intent_id}
        if monto:
            refund_data["amount"] = int(Decimal(str(monto)) * 100)
        refund = stripe.Refund.create(**refund_data)
        return refund
    except stripe.error.StripeError as e:
        print(f"Error procesando reembolso: {e}")
        return None
