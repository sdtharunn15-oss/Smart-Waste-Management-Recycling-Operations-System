# Smart Waste Management and Recycling Operations System

## Project Overview

The Smart Waste Management and Recycling Operations System is a backend application developed using FastAPI. It helps manage waste collection, vehicle assignments, workforce operations, recycling activities, disposal records, customer complaints, notifications, and environmental impact calculations.

The system provides REST APIs for administrators, operations managers, collection staff, recycling center managers, and customers.

## Technologies Used

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite
- JWT Authentication
- Alembic
- Pytest
- Uvicorn
- Docker

## Main Features

### Authentication and Authorization

- User registration and login
- JWT access and refresh tokens
- Password hashing
- Role-based access control
- User management

### Location and Customer Management

- Create and manage locations
- Support hierarchical locations
- Manage waste categories
- Register and manage customers

### Pickup and Collection Management

- Create and manage pickup requests
- Set pickup priorities
- Assign vehicles and drivers
- Track collection activities
- Validate vehicle availability and capacity
- Manage collection records

### Workforce and Vehicle Management

- Manage drivers and field workers
- Manage vehicle details and availability
- Assign collection staff
- Track vehicle maintenance
- Prevent assignments to unavailable vehicles

### Recycling Operations

- Manage recycling centers
- Transfer waste to recycling centers
- Record waste segregation
- Manage recycling processing batches
- Track waste disposal activities

### Customer Complaints and Notifications

- Register customer complaints
- Assign complaints to management staff
- Update complaint status
- Create and manage notifications
- Mark notifications as read or archived

### Analytics and Environmental Impact

- Collection performance reports
- Driver performance tracking
- Vehicle performance tracking
- Environmental impact calculations
- CO2 savings estimation
- Water and energy savings estimation
- Landfill waste reduction tracking

### Security and Validation

- Role-based permissions
- Request validation
- Error handling
- Rate limiting
- Security response headers
- Business rule validation

## Project Structure

```text
smart-waste-management-system/
│
├── alembic/
│   └── versions/
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │
│   ├── core/
│   ├── db/
│   ├── middleware/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── utils/
│
├── tests/
│   ├── integration/
│   └── unit/
│
├── docs/
├── postman/
├── scripts/
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
├── README.md
└── smart_waste.db
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <your-github-repository-url>
```

### 2. Navigate to the Project Folder

```bash
cd smart-waste-management-system
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file in the project root directory.

Example configuration:

```env
APP_NAME=Smart Waste Management System
APP_ENV=development
DATABASE_URL=sqlite:///./smart_waste.db
SECRET_KEY=change_this_to_a_long_random_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Use a secure secret key in production.

### 7. Run Database Migrations

```bash
alembic upgrade head
```

If the database has already been initialized and its existing schema has been stamped with the current Alembic revision, verify the migration status before running additional migrations.

### 8. Start the Application

```bash
uvicorn app.main:app --reload
```

The application will run at:

```text
http://127.0.0.1:8000
```

## API Documentation

FastAPI provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

Use Swagger UI to test available API endpoints.

## Running Tests

Run the complete test suite:

```bash
pytest -v
```

Run integration tests:

```bash
pytest tests/integration -v
```

Run unit tests:

```bash
pytest tests/unit -v
```

Run a specific test file:

```bash
pytest tests/integration/test_auth.py -v
```

## Database

The project uses SQLite as its database.

Database file:

```text
smart_waste.db
```

SQLAlchemy is used for database operations and Alembic is used to manage database schema migrations.

## User Roles

The application supports the following user roles:

- Super Admin
- Operations Manager
- Collection Supervisor
- Driver
- Recycling Center Manager
- Field Worker
- Customer

Each role has access to permitted operations based on the authorization rules.

## Application Workflow

1. Admin logs into the system.
2. Create collection locations and waste categories.
3. Register customers.
4. Create pickup requests.
5. Assign vehicles and drivers.
6. Track waste collection.
7. Transfer collected waste to recycling centers.
8. Record received waste.
9. Segregate waste by category.
10. Process recyclable waste.
11. Record waste disposal.
12. Calculate environmental impact.
13. Manage customer complaints.
14. Send notifications.
15. View collection performance and reports.
16. Review audit logs.

## Future Improvements

- Email and SMS notification integration
- Real-time vehicle tracking
- GPS-based route optimization
- Advanced analytics dashboard
- Automated pickup scheduling
- Production deployment and monitoring

## Author

Developed as a Smart Waste Management and Recycling Operations System project.

## License

This project is developed for educational and demonstration purposes.
