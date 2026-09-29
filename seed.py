from db import db
from passlib.context import CryptContext
from datetime import datetime

collection = db["user"]
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def check_email_exist(email: str):
    user = collection.find_one({"email": email})
    return user


def check_test_exist(test_name: str):
    return db["tests"].find_one({"test_name": test_name})


def seed_superadmin():
    username = "superadmin"
    email = "superadmin@gmail.com"
    password = "admin@123"

    try:
        if check_email_exist(email) is None:
            password = pwd_context.hash(password)

            superadmin = {
                "name": username,
                "email": email,
                "password": password,
                "profile_image": None,
                "user_role": 1,
                "payment_status": 1,
                "verification_status": 1,
                "status": 1,
                "deleted_at": None,
                "created_at": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "created_date": str(datetime.now().strftime("%Y-%m-%d")),
                "created_time": str(datetime.now().strftime("%H:%M:%S")),
                "created_by": None,
                "updated_at": None,
                "updated_by": None,
            }

            result = collection.insert_one(superadmin)
            if result.inserted_id:
                print(f"✅ Superadmin '{username}' created successfully.")
            else:
                print(f"❌ Error in SuperAdmin Creation")
        else:
            print(f"❌ Superadmin '{username}' already exists.")
            return
    except Exception as e:
        print(f"❌ Error in SuperAdmin Creation: {str(e)}")

if __name__ == "__main__":
    seed_superadmin()


# RUN = > python seed.py
