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

# Updated table creation query with payments as a large VARCHAR
query_table = """
CREATE TABLE IF NOT EXISTS payments (
    id INT PRIMARY KEY, 
    buyerName VARCHAR(255) NOT NULL, 
    carName VARCHAR(255) NOT NULL, 
    carPrice DECIMAL(10, 2) NOT NULL, 
    loanTerm INT NOT NULL, 
    deposit DECIMAL(10, 2) NOT NULL, 
    salary DECIMAL(10, 2) NOT NULL, 
    annualInterest DECIMAL(5, 2) NOT NULL, 
    payments TEXT NOT NULL, 
    basic_statistics TEXT NOT NULL
);
"""
query = text(query_table)
conn.execute(query)
conn.commit()


# constructQuery returns a string that represents the query sent to the
# database in order to introduce a row in the table
def constructQuery(id, buyerName, carName, carPrice, loanTerm, deposit, salary, annualInterest, payments, basic_statistics):
    query_text = (
        f"INSERT INTO payments (id, buyerName, carName, carPrice, loanTerm, deposit, salary, annualInterest, payments, basic_statistics) "
        f"VALUES ({id}, '{buyerName}', '{carName}', {carPrice}, {loanTerm}, {deposit}, {salary}, {annualInterest}, '{payments}', '{basic_statistics}');"
    )
    return query_text


# addTestData adds test data to database in order to be able to test report generation afterward
def addTestData():
    logger.info("Adding test data to the database")
    
    global request_no, request_dict

    carNames = [
        "Tesla Model 3", "Audi A4", "Volkswagen Golf", "Dacia Duster", 
        "Skoda Octavia", "Nissan Qashqai", "Toyota Corolla", "BMW X5", 
        "Ford Mustang", "Hyundai Tucson"
    ]
    buyerNames = ["Dorian Verna", "Andrei Popescu", "Mihai Ionescu", "Radu Alexandrescu", "Mihai Florescu", 
                "Ioana Georgescu", "Cristina Marinescu", "Victor Matei", "Elena Nastase", "Maria Tudor"]
        
    carPrices = [40000, 35000, 30000, 15000, 20000, 25000, 27000, 45000, 55000, 28000]
    loanTerms = [36, 48, 60, 72, 84, 36, 48, 60, 72, 84]
    deposits = [5000, 7000, 6000, 4000, 3000, 5000, 8000, 10000, 8000, 7000]
    salaries = [50000, 55000, 60000, 40000, 45000, 52000, 58000, 62000, 65000, 50000]
    annualInterests = [3.5, 4.0, 3.8, 4.5, 3.9, 4.1, 3.6, 4.2, 3.7, 4.0]
    
        
    # Generate 10 entries
    for i in range(10):
        # Calculate monthly payments
        payments = MonthlyPayment.calculatePayments(
            carPrice=carPrices[i],
            annualInterest=annualInterests[i] / 100,  # Convert annual interest to decimal
            loanTerm=loanTerms[i],
            deposit=deposits[i]
        )
        
        # Calculate basic statistics
        basic_statistics = MonthlyPayment.calculateBasicStatistics(payments)

        query = constructQuery(
            id=i + 1,
            buyerName=buyerNames[i],
            carName=carNames[i],
            carPrice=carPrices[i],
            loanTerm=loanTerms[i],
            deposit=deposits[i],
            salary=salaries[i],
            annualInterest=annualInterests[i],
            payments=str(payments),
            basic_statistics=str(basic_statistics)
        )

        logger.info(f"Executing query: {query}")
        query=text(query)
        conn.execute(query)
        conn.commit()

        # update dictionary
        request_dict[request_no] = payments
        request_no += 1


class BasicStatistics(ComplexModel):
    totalPaid = Float
    totalInterestPaid = Float
    totalPrincipalPaid = Float
    averageMonthlyPayment = Float
    averageInterestPayment = Float
    averagePrincipalPayment = Float

    def __init__(self, totalPaid, totalInterestPaid, totalPrincipalPaid, averageMonthlyPayment,
        averageInterestPayment, averagePrincipalPayment):
        self.totalPaid = totalPaid
        self.totalInterestPaid = totalInterestPaid
        self.totalPrincipalPaid = totalPrincipalPaid
        self.averageMonthlyPayment = averageMonthlyPayment
        self.averageInterestPayment = averageInterestPayment
        self.averagePrincipalPayment = averagePrincipalPayment

    def __str__(self):
        return f"({self.totalPaid}, {self.totalInterestPaid}, {self.totalPrincipalPaid}, \
            {self.averageMonthlyPayment}, {self.averageInterestPayment}, {self.averagePrincipalPayment})"


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

    
    def calculatePayments(carPrice, annualInterest, loanTerm, deposit):
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

        return payments

    
    # calculateBasicStatistics is a function that returns some general information
    # based on the plan made for the loan of the car
    def calculateBasicStatistics(payments):
        # Total calculations
        total_paid = sum(payment.month_payment for payment in payments)
        total_interest_paid = sum(payment.interest_payment for payment in payments)
        total_principal_paid = sum(payment.principal_payment for payment in payments)
        
        # Averages
        average_monthly_payment = total_paid / len(payments)
        average_interest_payment = total_interest_paid / len(payments)
        average_principal_payment = total_principal_paid / len(payments)
        
        # Return the statistics in a dictionary
        return BasicStatistics(total_paid, total_interest_paid, total_principal_paid,
            average_monthly_payment, average_interest_payment, average_principal_payment)


    def __str__(self):
        return f"({self.month}, {self.month_payment}, {self.interest_payment}, {self.principal_payment})"


class LoanCalculatorService(ServiceBase):
    # calculateLoan represents the endpoint fulfilling a request to calculate
    # all loan details and which inserts results in the database
    @rpc(String, String, Float, Integer, Float, Float, Float, _returns=Array(MonthlyPayment))
    def calculateLoan(ctx, buyerName, carName, carPrice, loanTerm, salary, deposit, annualInterest):
        logger.info("Entered request")

        payments = calculatePayments()

        basic_statistics = calculateBasicStatistics(payments)
        
        global request_dict, request_no

        # Add entry to database
        payments_text = "("
        for payment in payments[0: len(payments) - 1]:
            payments_text += str(payment) + ", "
        payments_text += str(payments[-1]) + ")"

        query_text = constructQuery(request_no, buyerName, carName, carPrice, loanTerm,
            deposit, salary, annualInterest, payments, basic_statistics)

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
    
    # Add test data
    addTestData()

    # Start the server
    server = make_server('0.0.0.0', 8000, wsgi_application)
    server.serve_forever()
