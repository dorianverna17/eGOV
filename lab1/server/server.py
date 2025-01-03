from spyne import Application, rpc, ServiceBase, Integer, Float, Unicode, String, Array, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from sqlalchemy import create_engine, insert, text

import logging
import sys
import time

# Create and configure logger
logging.basicConfig(format='%(asctime)s %(message)s')

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

request_dict = {}
request_no = 0

time.sleep(5)

# connect to database and create desired table
engine = create_engine("postgresql+psycopg2://dorian:1234@data-storage:5432/database")
conn = engine.connect()

query_delete = """
DO $$
BEGIN
   IF EXISTS (SELECT relname FROM pg_class WHERE relname='payments') THEN
       DELETE FROM payments;
       DROP TABLE payments;
   END IF;
END $$;
"""

query=text(query_delete)
conn.execute(query)
conn.commit()

query_table = "CREATE TABLE IF NOT EXISTS payments (_no int, payments varchar(10000));"
query=text(query_table)
conn.execute(query)
conn.commit()


class MonthlyPayment(ComplexModel):
    month = Integer
    month_payment = Float
    interest_payment = Float
    principal_payment = Float

    def __init__(self, month, month_payment, interest_payment, principal_payment):
        self.month = month
        self.month_payment = month_payment
        self.interest_payment = interest_payment
        self.principal_payment = principal_payment

    def __str__(self):
        return f"({self.month}, {self.month_payment}, {self.interest_payment}, {self.principal_payment})"


class LoanCalculatorService(ServiceBase):
    @rpc(String, String, Float, Integer, Float, Float, Float, _returns=Array(MonthlyPayment))
    def calculateLoan(ctx, buyerName, carName, carPrice, loanTerm, salary, deposit, annualInterest):
        logger.info("Entered request")
        
        monthly_rate = annualInterest / 12  # Initial monthly interest rate
        remaining_balance = carPrice - deposit  # Start with the car price minus the deposit
        
        # Calculate the monthly payment based on the initial loan amount and term
        monthly_payment = (remaining_balance * monthly_rate) / (1 - (1 + monthly_rate) ** -loanTerm)

        payments = []  # List to store (monthly payment, interest) tuples
        
        for month in range(loanTerm):
            # Calculate interest for the current month on remaining balance
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            
            # Store the payment details for the month
            payments.append(MonthlyPayment(
                month + 1,
                monthly_payment,
                interest_payment,
                principal_payment
            ))
        
            # Reduce the remaining balance by the principal paid
            remaining_balance -= principal_payment
        
        global request_dict
        global request_no

        # Add entry to database
        payments_text = "("
        for payment in payments[0: len(payments) - 1]:
            payments_text += str(payment) + ", "
        payments_text += str(payments[-1]) + ")"

        query_text = "INSERT INTO payments (_no, payments) VALUES (" + \
            str(request_no) + ", " + payments_text + ");"

        query=text(query_text)
        conn.execute(query)
        conn.commit()

        # update dictionary
        request_dict[request_no] = payments
        request_no += 1

        logger.info("Monthly payments with interest generated " + str(payments))

        # return response code and payments
        ctx.transport.resp_code = 200

        return payments


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
