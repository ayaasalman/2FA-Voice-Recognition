import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'  # Replace with your SMTP server
SMTP_PORT = 587
EMAIL_ADDRESS = 'ayasalman.j@gmail.com'  # Replace with your email
EMAIL_PASSWORD = 'jega lenx qkto vpzr'  # Replace with your email password

def send_email(to_email, subject, body):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))  # For plain text
        # For HTML email: MIMEText(body, 'html')

        # Connect to the SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Send the email
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

# Usage example
# to_email = 'ayasalman.j@gmail.com'
# subject = 'Congratulations'
# body = 'You have been hacked!'
# send_email(to_email, subject, body)
