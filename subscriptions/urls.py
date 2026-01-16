from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Checkout page (plan selection confirmation)
    path('checkout/<int:plan_id>/', views.CheckoutView.as_view(), name='checkout'),
    
    # Payment creation (AJAX - called by Snap.js)
    path('payment/create/', views.CreatePaymentView.as_view(), name='create_payment'),
    
    # Payment finish redirect
    path('payment/finish/', views.PaymentFinishView.as_view(), name='payment_finish'),
    
    # Midtrans webhook (called by Midtrans servers)
    path('webhook/midtrans/', views.PaymentWebhookView.as_view(), name='webhook_midtrans'),
    
    # Pricing page
    path('pricing/', views.PricingPageView.as_view(), name='pricing'),
]

