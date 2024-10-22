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
    @rpc(Float, Integer, _returns=Float)
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
        
        global request_dict
        global request_no

        request_dict[request_no] = monthly_payment
        request_no += 1

        ctx.transport.resp_code = 200

        logger.info("Monthly payment is " + str(monthly_payment))

        return monthly_payment

class CORSMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Define a custom start_response to add CORS headers
        def custom_start_response(status, headers, exc_info=None):
            headers.append(('Access-Control-Allow-Origin', '*'))  # Allow any origin
            headers.append(('Access-Control-Allow-Methods', 'POST, OPTIONS'))
            headers.append(('Access-Control-Allow-Headers', 'Content-Type, Authorization'))
            
            logger.info("status: " + str(status))
            status = '200 OK'

            return start_response(status, headers, exc_info)
        
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
