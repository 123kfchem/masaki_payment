import base64
import json
import os
from datetime import datetime
from io import BytesIO
from urllib import error, parse, request

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import LoginForm, PaymentForm, RegisterForm
from .models import Transaction


def _normalize_phone_number(phone_number):
    phone = phone_number.strip().replace("+", "")

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7"):
        phone = "254" + phone
    elif phone.startswith("254"):
        phone = phone
    else:
        raise ValueError("Invalid phone number")

    return f"+{phone}"


def _build_daraja_password(short_code: str, passkey: str, timestamp: str) -> str:
    payload = f'{short_code}{passkey}{timestamp}'.encode('utf-8')
    return base64.b64encode(payload).decode('utf-8')


def _get_daraja_access_token() -> str | None:
    consumer_key = os.getenv('DARAJA_CONSUMER_KEY', '').strip()
    consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET', '').strip()
    if not consumer_key or not consumer_secret:
        return None

    credentials = base64.b64encode(f'{consumer_key}:{consumer_secret}'.encode('utf-8')).decode('utf-8')
    auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    req = request.Request(auth_url, headers={'Authorization': f'Basic {credentials}'})
    try:
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('access_token')
    except error.URLError:
        return None


def _initiate_daraja_stk_push(transaction: Transaction) -> dict:
    short_code = os.getenv('DARAJA_SHORT_CODE', '').strip()
    passkey = os.getenv('DARAJA_PASSKEY', '').strip()
    callback_url = os.getenv('DARAJA_CALLBACK_URL', '').strip()
    print("Short Code:", repr(short_code))
    print("Passkey:", repr(passkey))
    print("Callback URL:", repr(callback_url))
    if not short_code or not passkey or not callback_url:
        transaction.status = 'PENDING'
        transaction.notes = 'Daraja credentials are not configured. Payment simulation only.'
        transaction.save(update_fields=['status', 'notes'])
        return {'ok': True, 'message': 'Demo mode: payment request accepted and queued for review.'}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = _build_daraja_password(short_code, passkey, timestamp)
    access_token = _get_daraja_access_token()
    if not access_token:
        transaction.status = 'PENDING'
        transaction.notes = 'Unable to obtain Daraja access token. Please verify credentials.'
        transaction.save(update_fields=['status', 'notes'])
        return {'ok': False, 'message': 'Daraja access token could not be created.'}

    payload = {
        
        'BusinessShortCode': 522522,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': str(int(transaction.amount)),
        'PartyA': transaction.phone_number,
        'PartyB': short_code,
        'PhoneNumber': transaction.phone_number,
        'CallBackURL': 'https://perky-unsuited-croak.ngrok-free.dev/payment/callback/',
        'AccountReference': '6234 8700 2154 1397',
        'TransactionDesc': 'Masaki payment',
    }

    endpoint = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            transaction.checkout_request_id = data.get('CheckoutRequestID', '')
            transaction.merchant_request_id = data.get('MerchantRequestID', '')
            transaction.status = 'PENDING'
            transaction.notes = 'STK push initiated successfully.'
            transaction.save(update_fields=['checkout_request_id', 'merchant_request_id', 'status', 'notes'])
            return {'ok': True, 'message': 'Safaricom STK push initiated successfully.'}
    except error.URLError as exc:
        transaction.status = 'PENDING'
        transaction.notes = f'Daraja request failed: {exc}'
        transaction.save(update_fields=['status', 'notes'])
        return {'ok': False, 'message': 'Daraja request failed. Please verify the endpoint and credentials.'}


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Welcome back to Masaki Payment Platform.')
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'payments/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'payments/register.html', {'form': form})


@login_required(login_url='login')
def dashboard_view(request):
    today = timezone.localdate()
    transactions = Transaction.objects.filter(user=request.user, created_at__date=today)
    completed_total = transactions.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
    pending_total = transactions.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0
    daily_totals = [
        {'day': item['created_at__date'], 'total': item['total']}
        for item in Transaction.objects.daily_totals_for_user(request.user, day=today)
    ]

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            transaction = Transaction.objects.create(
                user=request.user,
                phone_number=_normalize_phone_number(form.cleaned_data['phone_number']),
                amount=form.cleaned_data['amount'],
            )
            result = _initiate_daraja_stk_push(transaction)
            messages.success(request, result['message'])
            return redirect('dashboard')
    else:
        form = PaymentForm()

    return render(
        request,
        'payments/dashboard.html',
        {
            'form': form,
            'transactions': transactions,
            'completed_total': completed_total,
            'pending_total': pending_total,
            'transaction_count': transactions.count(),
            'daily_totals': daily_totals,
        },
    )


@login_required(login_url='login')
def download_pdf_report(request):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title='Masaki Transactions Report')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TableHeading', parent=styles['Heading4'], fontSize=10, leading=14, textColor=colors.HexColor('#2563eb')))
    story = []
    story.append(Paragraph('Masaki Payment Platform Transaction Report', styles['Title']))
    story.append(Paragraph(f'Generated on {timezone.now().strftime("%Y-%m-%d %H:%M")}', styles['BodyText']))
    story.append(Spacer(1, 0.2 * inch))

    transactions = Transaction.objects.filter(user=request.user)
    data = [['Phone number', 'Amount', 'Status', 'Created']] + [
        [transaction.phone_number, f'{transaction.amount:.2f}', transaction.status, transaction.created_at.strftime('%Y-%m-%d %H:%M')]
        for transaction in transactions
    ]

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph('Daily totals summary', styles['Heading4']))
    daily_totals = Transaction.objects.daily_totals_for_user(request.user)
    summary = [f"{item['created_at__date']} - {item['total']:.2f}" for item in daily_totals]
    story.extend([Paragraph(item, styles['BodyText']) for item in summary])

    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf_value, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="masaki_transactions_report.pdf"'
    return response


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


def payment_callback(request):
    if request.method != 'POST':
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)

    payload = json.loads(request.body.decode('utf-8'))
    callback = payload.get('Body', {}).get('stkCallback', {})
    checkout_request_id = callback.get('CheckoutRequestID')
    result_code = callback.get('ResultCode')
    transaction = Transaction.objects.filter(checkout_request_id=checkout_request_id).first()
    if transaction:
        transaction.status = 'COMPLETED' if result_code == 0 else 'FAILED'
        transaction.notes = callback.get('ResultDesc', 'Callback processed')
        transaction.save(update_fields=['status', 'notes'])
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'}, status=200)
