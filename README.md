# AttendTrack – Employee Attendance Management System

## Project Overview

**AttendTrack** is a Django-based employee attendance management system designed to simplify attendance tracking, CSV attendance imports, anomaly detection, attendance corrections, leave management, and employee attendance analysis.

The system provides role-based access for HR Admins, Managers, and Employees. It uses Django for backend development, Django REST Framework for API development, PostgreSQL for data storage, and PyJWT for token-based authentication.

The project also aims to incorporate asynchronous processing and machine learning techniques to identify attendance patterns and predict employee attendance risks.

## Key Features

- **Employee Management:** Maintain employee records, departments, and reporting relationships.
- **Attendance Import:** Import attendance records from CSV files.
- **Attendance Tracking:** Store and view employee punch-in and punch-out records.
- **Anomaly Detection:** Identify duplicate punches, late arrivals, and attendance irregularities.
- **Attendance Correction:** Allow employees to request corrections, Managers to review requests, and HR to finalize approved corrections.
- **Leave Management:** Support employee leave requests and review workflows.
- **Role-Based Access Control:** Separate permissions for HR Admins, Managers, and Employees.
- **JWT Authentication:** Secure API endpoints using PyJWT-based authentication.
- **REST APIs:** Provide endpoints for employee listings and attendance import-batch status.
- **Attendance Risk Analysis:** Planned integration of machine learning for attendance-risk scoring.
- **Feedback Analysis:** Planned text-processing and sentiment-analysis functionality.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3 | Backend programming |
| Django 5 | Web framework |
| Django REST Framework | REST API development |
| PostgreSQL | Relational database |
| Django ORM | Database operations |
| PyJWT | JWT authentication |
| HTML, CSS, JavaScript | Template-based user interface |
| Pandas | CSV processing and data analysis |
| NumPy | Numerical operations |
| Matplotlib | Data visualization |
| Scikit-learn | Machine learning |
| NLTK | Natural language processing |
| TensorFlow/Keras | Planned neural-network implementation |
| Celery and Redis | Planned asynchronous task processing |

## User Roles

### HR Admin
- Manage employee attendance records.
- Review attendance import history.
- Finalize manager-approved attendance corrections.
- Access HR-authorized management features.

### Manager
- View relevant employee attendance information.
- Review assigned employees' correction requests.
- Approve or reject correction requests.
- Access manager-authorized features.

### Employee
- View personal attendance information.
- Submit attendance correction requests.
- Submit leave requests.
- Access permitted employee features.

Access to each operation is controlled by server-side authentication and permission checks.

## Main Modules

### 1. Employee and Department Management
Stores employee details, department information, employee codes, and manager relationships.

### 2. Attendance Import and Processing
Processes attendance CSV files, validates input records, identifies invalid or duplicate records, and generates processing reports.

Expected CSV columns include:

- `employee_code`
- `employee_name`
- `department`
- `punch_date`
- `punch_time`
- `device_location`
- `punch_type`
- `shift_start`
- `shift_end`
- `leave_type`
- `manager_code`
- `remarks`

### 3. Attendance Management
Stores attendance logs and supports filtering by employee, date, and attendance status.

### 4. Attendance Correction Workflow
Supports a controlled correction process:

1. Employee submits a correction request.
2. Manager reviews the request.
3. Manager approves or rejects it.
4. HR finalizes manager-approved requests.

### 5. Leave Management
Supports leave requests with approval status and reviewer information.

### 6. REST API Module
The API module is implemented inside the existing `attendance` Django app.

Current API endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/attendance/employees/` | List employees |
| GET | `/api/attendance/import-batches/` | List attendance import batches |

Optional filters:

- `/api/attendance/employees/?search=EMP001`
- `/api/attendance/employees/?active=true`
- `/api/attendance/import-batches/?status=COMPLETED`

These endpoints require authentication and appropriate role permissions.

## Database Models

The project includes the following primary models:

- `Department`
- `Employee`
- `ShiftRule`
- `AttendanceImportBatch`
- `AttendanceLog`
- `AttendanceCorrection`
- `LeaveRequest`
- `RiskScore`
- `EmployeeRemark`

These models represent employee information, attendance logs, import history, correction requests, leave requests, risk assessments, and employee remarks.

## Project Structure

```text
AttendTrack/
├── manage.py
├── requirements.txt
├── your_project/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── attendance/
│   ├── models.py
│   ├── admin.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   ├── api_views.py
│   ├── api_urls.py
│   ├── api_authentication.py
│   ├── templates/
│   └── ...
├── scripts/
│   └── attendance_processor.py
├── sample_data/
│   └── attendance_input.csv
├── reports/
└── README.md
```

*Note: Replace `your_project` with the actual Django project package name. The structure may change as additional modules are implemented.*

## Installation and Setup

### Prerequisites

- Python 3
- PostgreSQL
- Git
- pip

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd AttendTrack
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Ensure your dependencies include the packages required by the features implemented in your project, such as Django, Django REST Framework, PyJWT, psycopg, Pandas, and NumPy.

### 4. Configure Environment Variables

Configure your Django secret key, database credentials, and other settings through environment variables.

Example:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=attendtrack_db
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

JWT_SECRET_KEY=your-jwt-secret
```

Use the variable names expected by your `settings.py`. Do not commit real credentials or secret keys to GitHub.

### 5. Create the Database

Create a PostgreSQL database named `attendtrack_db`, or use another database name configured in your environment.

Ensure PostgreSQL is running before starting the application.

### 6. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create a Superuser

```bash
python manage.py createsuperuser
```

### 8. Start the Development Server

```bash
python manage.py runserver
```

Open the application at:

`http://127.0.0.1:8000/`

The Django admin interface is available at:

`http://127.0.0.1:8000/admin/`

## API Authentication

The API uses a custom PyJWT authentication class.

For protected endpoints, obtain an access token through the project's existing login API and include it in the request header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Example request:

```http
GET /api/attendance/employees/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

The server validates the token and checks the user's permissions before returning protected data.

## Testing

Run Django's automated tests with:

```bash
python manage.py test
```

Test API endpoints using Postman or another HTTP client.

Recommended test cases include:

- Valid and invalid authentication tokens.
- Access attempts by users with different roles.
- Employee search and active-status filters.
- Import-batch status filters.
- Invalid CSV files and missing required columns.
- Duplicate attendance records.
- Invalid employee codes, dates, and punch times.
- Attendance correction approval and rejection.
- Leave-request validation and authorization.

## Security Considerations

- Keep secret keys and database passwords in environment variables.
- Never commit `.env` files or real credentials.
- Validate uploaded files and request data on the server.
- Enforce role permissions on the backend rather than relying on the UI.
- Restrict employees to their own records where required.
- Protect form submissions with Django CSRF protection.
- Use HTTPS and production-appropriate settings when deploying.

## Development Status

AttendTrack is being developed incrementally.

The current implementation includes the Django attendance models, CSV processing, attendance views, correction workflows, and the initial employee-list and import-batch API endpoints.

Additional features, including complete leave management, asynchronous task processing, attendance-risk prediction, and feedback sentiment analysis, are planned or under development. Update this section as each feature is completed and tested.

## Future Enhancements

- Celery-based asynchronous attendance processing.
- Redis caching and task-status tracking.
- Machine learning-based attendance-risk prediction.
- NLP-based employee feedback and concern analysis.
- TensorFlow/Keras-based prediction experiments.
- Expanded API coverage and automated tests.
- Attendance dashboards and data visualizations.

## License

This project is developed for learning and internship purposes. Add an appropriate open-source license if you intend to distribute it publicly.
