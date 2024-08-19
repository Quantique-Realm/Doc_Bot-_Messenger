from flask import Flask, request, send_file, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from fpdf import FPDF
from twilio.rest import Client
import os
import tempfile

app = Flask(__name__)

# Your Twilio Account SID and Auth Token
account_sid = ''
auth_token = ''

# In-memory storage to track user sessions and last contract
user_sessions = {}
last_contracts = {}

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    from_number = request.values.get('From')
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if from_number not in user_sessions:
        user_sessions[from_number] = {'step': 'start'}

    user_session = user_sessions[from_number]

    if user_session['step'] == 'start':
        if incoming_msg == 'hi':
            msg.body("Hi! Do you want to create a new contract or view the last one? Type 'new' or 'view'.")
        elif incoming_msg == 'view':
            if from_number in last_contracts:
                contract_path = last_contracts[from_number]
                msg.body("Here's your last contract.")
                send_pdf(from_number, contract_path)
            else:
                msg.body("No contract found. Please create a new one first.")
        elif incoming_msg == 'new':
            msg.body("Great! Let's start with the contract details. What is the name of Party 1?")
            user_session['step'] = 'party1_name'
        else:
            msg.body("Sorry, I didn't understand that. Type 'Hi' to start over.")
    
    elif user_session['step'] == 'party1_name':
        user_session['party1_name'] = incoming_msg
        msg.body("Thank you! What is the name of Party 2?")
        user_session['step'] = 'party2_name'

    elif user_session['step'] == 'party2_name':
        user_session['party2_name'] = incoming_msg
        msg.body("What is the contract start date? (e.g., 2024-01-01)")
        user_session['step'] = 'start_date'

    elif user_session['step'] == 'start_date':
        user_session['start_date'] = incoming_msg
        msg.body("What is the contract end date? (e.g., 2024-12-31)")
        user_session['step'] = 'end_date'

    elif user_session['step'] == 'end_date':
        user_session['end_date'] = incoming_msg
        msg.body("Please provide the contract terms.")
        user_session['step'] = 'terms'

    elif user_session['step'] == 'terms':
        user_session['terms'] = incoming_msg
        msg.body("Who is signing as Party 1?")
        user_session['step'] = 'signature1_name'

    elif user_session['step'] == 'signature1_name':
        user_session['signature1_name'] = incoming_msg
        msg.body("And who is signing as Party 2?")
        user_session['step'] = 'signature2_name'

    elif user_session['step'] == 'signature2_name':
        user_session['signature2_name'] = incoming_msg
        # Generate PDF
        pdf_path = generate_contract_pdf(
            user_session['party1_name'], user_session['party2_name'],
            user_session['start_date'], user_session['end_date'],
            user_session['terms'], user_session['signature1_name'],
            user_session['signature2_name']
        )
        
        # Store the path of the last contract
        last_contracts[from_number] = pdf_path

        send_pdf(from_number, pdf_path)
        msg.body("Your contract has been generated and sent to you via WhatsApp.")
        # Reset the user session
        user_sessions[from_number] = {'step': 'start'}

    return str(resp)

def generate_contract_pdf(party1, party2, start_date, end_date, terms, signature1, signature2):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Service Agreement", ln=True, align='C')

    # Space
    pdf.ln(10)

    # Party Details
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"This Agreement is made between {party1} and {party2}.", ln=True, align='L')

    # Contract Dates
    pdf.cell(200, 10, txt=f"Contract Start Date: {start_date}", ln=True, align='L')
    if end_date:
        pdf.cell(200, 10, txt=f"Contract End Date: {end_date}", ln=True, align='L')

    # Space
    pdf.ln(10)

    # Contract Terms
    pdf.multi_cell(0, 10, txt=f"Contract Terms: {terms}", align='L')

    # Space
    pdf.ln(10)

    # Signature Lines
    pdf.cell(200, 10, txt="Signatures:", ln=True, align='L')
    pdf.cell(200, 10, txt=f"{party1} (Party 1): _______________________", ln=True, align='L')
    pdf.cell(200, 10, txt=f"{party2} (Party 2): _______________________", ln=True, align='L')

    # Signature Names
    pdf.cell(200, 10, txt=f"Signed by {signature1} for Party 1", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Signed by {signature2} for Party 2", ln=True, align='L')

    # Save the PDF to a temporary file
    pdf_output_path = os.path.join(tempfile.gettempdir(), "contract.pdf")
    pdf.output(pdf_output_path)

    return pdf_output_path

def send_pdf(to_whatsapp_number, pdf_path):
    """Send a PDF file via WhatsApp."""
    client = Client(account_sid, auth_token)

    # Replace with your actual ngrok URL
    ngrok_url = 'https://3af7-103-159-214-186.ngrok-free.app'  # Replace this with your actual ngrok URL
    media_url = f"{ngrok_url}/download/contract.pdf"

    try:
        message = client.messages.create(
            body="Here is your contract PDF.",
            from_='whatsapp:+14155238886',  # Your Twilio sandbox number
            to=to_whatsapp_number,
            media_url=[media_url],
            status_callback=f"{ngrok_url}/status"  # Optional: Add a status callback URL
        )
        print(f"Message sent: SID {message.sid}")
    except Exception as e:
        print(f"Failed to send message: {e}")

@app.route('/download/contract.pdf')
def download_pdf():
    pdf_path = os.path.join(tempfile.gettempdir(), 'contract.pdf')
    return send_file(pdf_path, as_attachment=True)

@app.route('/status', methods=['POST'])
def status_callback():
    message_sid = request.values.get('MessageSid')
    message_status = request.values.get('MessageStatus')
    
    # Log or handle the message status update
    print(f"Message SID: {message_sid}, Status: {message_status}")
    
    return '', 200

if __name__ == "__main__":
    app.run(debug=True)
