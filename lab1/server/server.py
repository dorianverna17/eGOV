from spyne import Application, rpc, ServiceBase, Integer, Float, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import logging
import sys

# Create and configure logger
logging.basicConfig(format='%(asctime)s %(message)s')

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

request_dict = {}
request_no = 0

class LoanCalculatorService(ServiceBase):
    def calculateLoan(ctx, carPrice, loanTerm):
        """
        Calculate the monthly payment for a loan.
        :param carPrice: The price of the car (float).
        :param loanTerm: The loan term in months (integer).
        :return: The calculated monthly payment (float).
        """
        logger.info("Entered request")
        # Example loan calculation logic (simple interest for demonstration)
        interest_rate = 0.05  # Example fixed annual interest rate of 5%
        monthly_rate = interest_rate / 12  # Monthly interest rate
        
        # Simple loan payment formula for fixed-rate loans
        monthly_payment = (carPrice * monthly_rate) / (1 - (1 + monthly_rate) ** -loanTerm)
        
        request_dict[request_no] = monthly_payment
        request_no += 1

class CORSMiddleware:
    def __init__(self, app):
        self.app = app

    def extract_car_price_from_body(body):
        """
        Extract car price from the request XML body.
        :param body: The XML body as a string.
        :return: The extracted car price as a float.
        """
        root = ET.fromstring(body)
        # Assuming your XML structure has <carPrice> element
        car_price_element = root.find('.//carPrice')  # Adjust the path according to your XML schema
        if car_price_element is not None:
            return float(car_price_element.text)
        raise ValueError("carPrice not found in the request body.")

    def extract_loan_term_from_body(body):
        """
        Extract loan term from the request XML body.
        :param body: The XML body as a string.
        :return: The extracted loan term as an integer.
        """
        root = ET.fromstring(body)
        # Assuming your XML structure has <loanTerm> element
        loan_term_element = root.find('.//loanTerm')  # Adjust the path according to your XML schema
        if loan_term_element is not None:
            return int(loan_term_element.text)
        raise ValueError("loanTerm not found in the request body.")

    def __call__(self, environ, start_response):
        # Define a custom start_response to add CORS headers
        def custom_start_response(status, headers, exc_info=None):
            headers.append(('Access-Control-Allow-Origin', '*'))  # Allow any origin
            headers.append(('Access-Control-Allow-Methods', 'POST, OPTIONS'))
            headers.append(('Access-Control-Allow-Headers', 'Content-Type, Authorization'))
            return start_response(status, headers, exc_info)
        
        # Handle preflight OPTIONS request specifically for POST
        if environ['REQUEST_METHOD'] == 'OPTIONS':

            body_size = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(body_size).decode('utf-8')

            # Define your XML response for OPTIONS requests
            carPrice = extract_car_price_from_body(body)  # Define this function
            loanTerm = extract_loan_term_from_body(body)   # Define this function
                
            # Call the calculateLoan method
            response = LoanCalculatorService.calculateLoan(None, carPrice, loanTerm)

            xml_response = '''<?xml version="1.0" encoding="UTF-8"?>
            <response>
            <monthlyPayment>{request_dict[${request_no} - 1]}</monthlyPayment>
            <message>Preflight check successful</message>
            </response>'''
            headers = [('Content-Type', 'application/xml')]  # Set appropriate content type
            custom_start_response('200 OK', headers)
            return [xml_response.encode('utf-8')]  # Return the XML response as bytes
        
        
        # Otherwise, proceed with the application (for POST requests)
        return self.app(environ, custom_start_response)

# Define the SOAP Application
application = Application(
    [LoanCalculatorService],
    tns='service',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

# Wrap with CORSMiddleware if needed
wsgi_application = CORSMiddleware(WsgiApplication(application))

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    logger.info("Starting server")
    
    # Start the server
    server = make_server('0.0.0.0', 8000, wsgi_application)
    server.serve_forever()
