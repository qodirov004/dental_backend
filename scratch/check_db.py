import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clinic.models import MedicalRecord
from django.db import connection

def check_column():
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(clinic_medicalrecord)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Columns in clinic_medicalrecord: {columns}")
        if 'additional_conditions' in columns:
            print("SUCCESS: additional_conditions column exists.")
        else:
            print("ERROR: additional_conditions column is MISSING!")

if __name__ == "__main__":
    check_column()
