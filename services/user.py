import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

class UserHandler:
    def __init__(self, user_service):
        self.user_service = user_service
        self.sender_email = "arnab.rph.99@gmail.com"  # Use your email
        self.sender_password = "uqjk zrxr qnug whvn"  # Use your email password or app password

    def generate_otp(self):
        return random.randint(111111, 999999)

    def send_otp_email(self, email, otp, purpose):
        # Create message
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = email
        
        if purpose == "authentication":
            message["Subject"] = "[PassVault - Verification Code]"
            body = self._get_verification_template(otp)
        
        elif purpose == "master_key_reset":
            message["Subject"] = "[PassVault - Master Key Reset Code]"
            body = self._get_master_key_reset_template(otp)
        
        elif purpose == "reset_password":
            message["Subject"] = "[PassVault - Password Reset Code] "
            body = self._get_reset_template(otp)
            
        else:
            message["Subject"] = "[PassVault - Verification Code]"
            body = self._get_generic_template(otp)
        
        message.attach(MIMEText(body, "html"))
        
        try:
            # Connect to SMTP server (for Gmail)
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            server.send_message(message)
            server.quit()
            return True
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
    
    
    def _get_verification_template(self, otp):
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PassVault - Your Verification Code</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333333;
                        background-color: #f9f9f9;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #2c3e50, #3498db);
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 150px;
                        height: auto;
                        margin-bottom: 15px;
                    }}
                    .header h1 {{
                        color: white;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    h2 {{
                        color: #2c3e50;
                        margin-top: 0;
                        font-size: 22px;
                        font-weight: 600;
                    }}
                    p {{
                        margin-bottom: 20px;
                        font-size: 16px;
                    }}
                    .code-container {{
                        background-color: #f5f7fa;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: center;
                        border-left: 4px solid #3498db;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2c3e50;
                        letter-spacing: 8px;
                        margin: 0;
                    }}
                    .expiry {{
                        background-color: #fff8e1;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ffc107;
                    }}
                    .expiry-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ffc107;
                        font-weight: bold;
                    }}
                    .warning {{
                        background-color: #fef2f2;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ef4444;
                    }}
                    .warning-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    }}
                    .footer {{
                        background-color: #f5f7fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .footer p {{
                        color: #6b7280;
                        font-size: 13px;
                        margin: 0;
                    }}
                    .social-links {{
                        margin-top: 15px;
                    }}
                    .social-links a {{
                        display: inline-block;
                        margin: 0 8px;
                        color: #6b7280;
                        text-decoration: none;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #3498db;
                        color: white;
                        text-decoration: none;
                        padding: 12px 25px;
                        border-radius: 4px;
                        font-weight: 500;
                        margin-top: 15px;
                        text-align: center;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            width: 100%;
                            margin: 0;
                            border-radius: 0;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        .verification-code {{
                            font-size: 28px;
                            letter-spacing: 6px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://yourdomain.com/logo.png" alt="PassVault Logo" class="logo" />
                        <h1>Account Verification</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Your Verification Code</h2>
                        <p>Hello there,</p>
                        <p>Thank you for signing up with PassVault. To complete your account verification and ensure the security of your passwords, please use the code below:</p>
                        
                        <div class="code-container">
                            <div class="verification-code">{otp}</div>
                        </div>
                        
                        <div class="expiry">
                            <span class="expiry-icon">⏱</span> This code will expire in <strong>5 minutes</strong>. Please enter it promptly to complete your verification.
                        </div>
                        
                        <div class="warning">
                            <span class="warning-icon">⚠️</span> If you didn't request this code, you can safely ignore this email. No action is needed.
                        </div>
                        
                        <p>Once verified, you'll have access to all of PassVault's secure password management features.</p>
                        
                        <a href="https://passvault.yourdomain.com" class="button">Return to PassVault</a>
                    </div>
                    
                    <div class="footer">
                        <p>© {datetime.now().year} PassVault. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                        <div class="social-links">
                            <a href="#">Privacy Policy</a> | 
                            <a href="#">Terms of Service</a> | 
                            <a href="#">Support</a>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
    
    def _get_reset_template(self, otp):
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PassVault - Password Reset Code</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333333;
                        background-color: #f9f9f9;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #2c3e50, #3498db);
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 150px;
                        height: auto;
                        margin-bottom: 15px;
                    }}
                    .header h1 {{
                        color: white;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    h2 {{
                        color: #2c3e50;
                        margin-top: 0;
                        font-size: 22px;
                        font-weight: 600;
                    }}
                    p {{
                        margin-bottom: 20px;
                        font-size: 16px;
                    }}
                    .code-container {{
                        background-color: #f5f7fa;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: center;
                        border-left: 4px solid #3498db;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2c3e50;
                        letter-spacing: 8px;
                        margin: 0;
                    }}
                    .expiry {{
                        background-color: #fff8e1;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ffc107;
                    }}
                    .expiry-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ffc107;
                        font-weight: bold;
                    }}
                    .warning {{
                        background-color: #fef2f2;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ef4444;
                    }}
                    .warning-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    }}
                    .footer {{
                        background-color: #f5f7fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .footer p {{
                        color: #6b7280;
                        font-size: 13px;
                        margin: 0;
                    }}
                    .social-links {{
                        margin-top: 15px;
                    }}
                    .social-links a {{
                        display: inline-block;
                        margin: 0 8px;
                        color: #6b7280;
                        text-decoration: none;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #3498db;
                        color: white;
                        text-decoration: none;
                        padding: 12px 25px;
                        border-radius: 4px;
                        font-weight: 500;
                        margin-top: 15px;
                        text-align: center;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            width: 100%;
                            margin: 0;
                            border-radius: 0;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        .verification-code {{
                            font-size: 28px;
                            letter-spacing: 6px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://yourdomain.com/logo.png" alt="PassVault Logo" class="logo" />
                        <h1>Password Reset</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Password Reset Code</h2>
                        <p>Hello there,</p>
                        <p>We received a request to reset your PassVault password. To proceed with resetting your password, please use the code below:</p>
                        
                        <div class="code-container">
                            <div class="verification-code">{otp}</div>
                        </div>
                        
                        <div class="expiry">
                            <span class="expiry-icon">⏱</span> This code will expire in <strong>5 minutes</strong>. Please enter it promptly to complete your password reset.
                        </div>
                        
                        <div class="warning">
                            <span class="warning-icon">⚠️</span> If you didn't request a password reset, please secure your account immediately or contact our support team as someone may be attempting to access your account.
                        </div>
                        
                        <p>After resetting your password, we recommend updating passwords for any other accounts that may have used similar credentials.</p>
                        
                        <a href="https://passvault.yourdomain.com/reset" class="button">Reset Password</a>
                    </div>
                    
                    <div class="footer">
                        <p>© {datetime.now().year} PassVault. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                        <div class="social-links">
                            <a href="#">Privacy Policy</a> | 
                            <a href="#">Terms of Service</a> | 
                            <a href="#">Support</a>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
    
    def _get_generic_template(self, otp):
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PassVault - Verification Code</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333333;
                        background-color: #f9f9f9;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #2c3e50, #3498db);
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 150px;
                        height: auto;
                        margin-bottom: 15px;
                    }}
                    .header h1 {{
                        color: white;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    h2 {{
                        color: #2c3e50;
                        margin-top: 0;
                        font-size: 22px;
                        font-weight: 600;
                    }}
                    p {{
                        margin-bottom: 20px;
                        font-size: 16px;
                    }}
                    .code-container {{
                        background-color: #f5f7fa;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: center;
                        border-left: 4px solid #3498db;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2c3e50;
                        letter-spacing: 8px;
                        margin: 0;
                    }}
                    .expiry {{
                        background-color: #fff8e1;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ffc107;
                    }}
                    .expiry-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ffc107;
                        font-weight: bold;
                    }}
                    .warning {{
                        background-color: #fef2f2;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ef4444;
                    }}
                    .warning-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    }}
                    .footer {{
                        background-color: #f5f7fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .footer p {{
                        color: #6b7280;
                        font-size: 13px;
                        margin: 0;
                    }}
                    .social-links {{
                        margin-top: 15px;
                    }}
                    .social-links a {{
                        display: inline-block;
                        margin: 0 8px;
                        color: #6b7280;
                        text-decoration: none;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #3498db;
                        color: white;
                        text-decoration: none;
                        padding: 12px 25px;
                        border-radius: 4px;
                        font-weight: 500;
                        margin-top: 15px;
                        text-align: center;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            width: 100%;
                            margin: 0;
                            border-radius: 0;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        .verification-code {{
                            font-size: 28px;
                            letter-spacing: 6px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://yourdomain.com/logo.png" alt="PassVault Logo" class="logo" />
                        <h1>Verification Required</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Your Verification Code</h2>
                        <p>Hello there,</p>
                        <p>Thank you for using PassVault. To ensure the security of your account, please use the verification code below:</p>
                        
                        <div class="code-container">
                            <div class="verification-code">{otp}</div>
                        </div>
                        
                        <div class="expiry">
                            <span class="expiry-icon">⏱</span> This code will expire in <strong>5 minutes</strong>. Please enter it promptly to complete your verification.
                        </div>
                        
                        <div class="warning">
                            <span class="warning-icon">⚠️</span> If you didn't request this code, please ignore this email or contact our support team immediately as your account may have been compromised.
                        </div>
                        
                        <p>Need help? Our support team is available to assist you with any questions or concerns.</p>
                        
                        <a href="https://passvault.yourdomain.com" class="button">Visit PassVault</a>
                    </div>
                    
                    <div class="footer">
                        <p>© {datetime.now().year} PassVault. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                        <div class="social-links">
                            <a href="#">Privacy Policy</a> | 
                            <a href="#">Terms of Service</a> | 
                            <a href="#">Support</a>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

    def _get_master_key_reset_template(self, otp):
        return f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>PassVault - Master Key Reset Request</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333333;
                        background-color: #f9f9f9;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #8e44ad, #3498db);
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 150px;
                        height: auto;
                        margin-bottom: 15px;
                    }}
                    .header h1 {{
                        color: white;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    h2 {{
                        color: #8e44ad;
                        margin-top: 0;
                        font-size: 22px;
                        font-weight: 600;
                    }}
                    p {{
                        margin-bottom: 20px;
                        font-size: 16px;
                    }}
                    .code-container {{
                        background-color: #f5f7fa;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: center;
                        border-left: 4px solid #8e44ad;
                    }}
                    .verification-code {{
                        font-size: 32px;
                        font-weight: bold;
                        color: #2c3e50;
                        letter-spacing: 8px;
                        margin: 0;
                    }}
                    .reset-warning {{
                        background-color: #fef2f2;
                        border-radius: 4px;
                        padding: 10px 15px;
                        margin: 25px 0;
                        font-size: 14px;
                        border-left: 4px solid #ef4444;
                    }}
                    .reset-warning-icon {{
                        display: inline-block;
                        margin-right: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    }}
                    .footer {{
                        background-color: #f5f7fa;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .footer p {{
                        color: #6b7280;
                        font-size: 13px;
                        margin: 0;
                    }}
                    .social-links a {{
                        display: inline-block;
                        margin: 0 8px;
                        color: #6b7280;
                        text-decoration: none;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            width: 100%;
                            margin: 0;
                            border-radius: 0;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://yourdomain.com/logo.png" alt="PassVault Logo" class="logo" />
                        <h1>Master Key Reset</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Your Master Key Reset Code</h2>
                        <p>Hello,</p>
                        <p>We received a request to reset your Master Key for PassVault. Please use the verification code below to proceed:</p>
                        
                        <div class="code-container">
                            <div class="verification-code">{otp}</div>
                        </div>
                        
                        <div class="reset-warning">
                            <span class="reset-warning-icon">⚠️</span> If you did not request this reset, please ignore this email or contact support immediately.
                        </div>
                        
                        <p>For security reasons, this code will expire in <strong>15 minutes</strong>. Please use it promptly.</p>
                    </div>
                    
                    <div class="footer">
                        <p>© {datetime.now().year} PassVault. All rights reserved.</p>
                        <p>This is an automated message, please do not reply to this email.</p>
                        <div class="social-links">
                            <a href="#">Privacy Policy</a> | 
                            <a href="#">Terms of Service</a> | 
                            <a href="#">Support</a>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
