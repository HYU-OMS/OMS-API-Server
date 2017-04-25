import os

# Statement for enabling the development environment
DEBUG = False

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the database
# Follow this form -> "mysql+pymysql://[username]:[password]@[host]/[db]"
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://[ID]:[PASSWORD]@[HOST]/[DB]"
SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_CONNECT_OPTIONS = {
    "charset": "utf8mb4",
    "ssl": {
        "ssl_ca": BASE_DIR + "/cert/your_cert.pem"
    }
}

JWT_SECRET_KEY = "USE_YOUR_OWN_SECRET_KEY"
