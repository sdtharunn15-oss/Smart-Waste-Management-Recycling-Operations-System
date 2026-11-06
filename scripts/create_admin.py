import getpass

from app.db.session import SessionLocal
from app.services.admin_setup import create_initial_admin


def main():
    full_name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip()
    password = getpass.getpass("Enter admin password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    db = SessionLocal()

    try:
        admin = create_initial_admin(
            db=db,
            full_name=full_name,
            email=email,
            password=password
        )

        print(f"Super admin created successfully. User ID: {admin.id}")

    except Exception as error:
        db.rollback()
        print(f"Admin creation failed: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    main()