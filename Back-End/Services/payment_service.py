# from alipay import AliPay
# from alipay.utils import AliPayConfig
# import os
# import time
# from config import Config

# class AlipayService:
#     def __init__(self, app=None):
#         self.alipay = None
#         if app:
#             self.init_app(app)
    
#     def init_app(self, app):
#         """Initialize Alipay SDK with app configuration"""
#         self.alipay = AliPay(
#             appid=app.config['ALIPAY_APP_ID'],
#             app_notify_url=app.config['ALIPAY_NOTIFY_URL'],
#             app_private_key_string=open('keys/app_private_key.pem').read(),
#             alipay_public_key_string=open('keys/alipay_public_key.pem').read(),
#             sign_type='RSA2',
#             debug=app.config['ALIPAY_DEBUG'],
#             config=AliPayConfig(timeout=15)
#         )

#     def create_payment(self, user_id, amount, subject):
#         """Create Alipay payment order"""
#         out_trade_no = f"facepay_{user_id}_{int(time.time())}"
#         order_string = self.alipay.api_alipay_trade_page_pay(
#             out_trade_no=out_trade_no,
#             total_amount=str(amount),
#             subject=subject,
#             return_url=Config.ALIPAY_RETURN_URL,
#             notify_url=Config.ALIPAY_NOTIFY_URL
#         )
#         return {
#             'payment_url': Config.ALIPAY_GATEWAY + "?" + order_string,
#             'out_trade_no': out_trade_no
#         }

#     def verify_notification(self, data):
#         """Verify Alipay payment notification"""
#         return self.alipay.verify_notification(data)

from alipay import AliPay
from alipay.utils import AliPayConfig
import os
import time
from datetime import datetime

class AlipayService:
    def __init__(self, app=None):
        self.alipay = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Alipay SDK with app configuration"""
        self.alipay = AliPay(
            appid=app.config['ALIPAY_APP_ID'],
            app_notify_url=app.config['ALIPAY_NOTIFY_URL'],
            app_private_key_string=app.config['APP_PRIVATE_KEY'],
            alipay_public_key_string=app.config['ALIPAY_PUBLIC_KEY'],
            sign_type='RSA2',
            debug=app.config['ALIPAY_DEBUG'],
            config=AliPayConfig(timeout=15)
        )
        self.gateway = app.config['ALIPAY_GATEWAY']
        self.return_url = app.config['ALIPAY_RETURN_URL']

    def create_payment(self, user_id, amount, subject, out_trade_no=None):
        """Create Alipay payment order"""
        if not out_trade_no:
            out_trade_no = f"facepay_{user_id}_{int(datetime.now().timestamp())}"
        
        order_string = self.alipay.api_alipay_trade_page_pay(
            out_trade_no=out_trade_no,
            total_amount=str(amount),
            subject=subject,
            return_url=self.return_url,
            notify_url=self.alipay.app_notify_url
        )
        
        return {
            'payment_url': f"{self.gateway}?{order_string}",
            'out_trade_no': out_trade_no
        }

    def verify_notification(self, data):
        """Verify Alipay payment notification"""
        signature = data.pop("sign", None)
        success = self.alipay.verify(data, signature)
        if not success:
            print("Alipay notification verification failed")
        return success

    def query_payment_status(self, out_trade_no=None, trade_no=None):
        """Query payment status"""
        if not (out_trade_no or trade_no):
            raise ValueError("Either out_trade_no or trade_no is required")
            
        response = self.alipay.api_alipay_trade_query(
            out_trade_no=out_trade_no,
            trade_no=trade_no
        )
        
        if response.get("code") != "10000":
            return None
            
        return {
            'status': response['trade_status'],
            'amount': float(response['total_amount']),
            'trade_no': response['trade_no'],
            'out_trade_no': response['out_trade_no'],
            'pay_time': response.get('send_pay_date')
        }