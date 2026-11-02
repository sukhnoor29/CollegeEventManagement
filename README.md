# College Event Management System

A web-based College Event Management System built using Python, Flask, MySQL, HTML, CSS and JavaScript.

## 1. Requirements

Install the following:

- Python 3.10 or newer
- MySQL Server
- MySQL Workbench

## 2. Set Up MySQL Database

Open MySQL Workbench and connect to your local MySQL Server.

Open a new SQL tab and execute:

    CREATE DATABASE college_event_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

    CREATE USER IF NOT EXISTS 'event_app'@'localhost'
    IDENTIFIED BY 'my_password';

    GRANT ALL PRIVILEGES ON college_event_management.*
    TO 'event_app'@'localhost';

    FLUSH PRIVILEGES;

## 3. Create a Virtual Environment

In the VS Code terminal, run:

    python -m venv .venv

Activate the virtual environment using PowerShell:

    .venv\Scripts\Activate.ps1

If PowerShell blocks activation, run:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Then activate the environment again.

## 4. Install Dependencies

Run:

    pip install -r requirements.txt

## 5. Configure Environment Variables

Create the `.env` file by copying `.env.example`.

In PowerShell, run:

    Copy-Item .env.example .env

Open `.env` and configure:

    SECRET_KEY=your_random_secret_key

    DATABASE_URL=mysql+pymysql://event_app:my_password@localhost:3306/college_event_management?charset=utf8mb4

    FLASK_DEBUG=1

    APP_TIMEZONE=Asia/Kolkata

Save the file.

Make sure the database username and password match the details used in MySQL Workbench.

## 6. Initialize the Database

Run:

    python -m flask --app run.py init-db

This creates the required database tables.

## 7. Add Sample Data

Run:

    python -m flask --app run.py seed-demo

This adds sample users and events to the database.

### Demo Login Credentials

| Role | Email | Password |
| Student | student@example.com | Demo@123 |
| Organizer | organizer@example.com | Demo@123 |
| Administrator | admin@example.com | Demo@123 |

## 8. Run the Application

Run:

    python -m flask --app run.py run

Open your browser and visit:

http://127.0.0.1:5000

## 9. Running the Project Again

After completing the initial setup, you only need to:

1. Start the MySQL Server.
2. Open the project folder in VS Code.
3. Activate the virtual environment:

       .venv\Scripts\Activate.ps1

4. Start the application:

       python -m flask --app run.py run

5. Open http://127.0.0.1:5000 in your browser.

You do not need to recreate the database or add sample data every time.

## Basic Notes

- Make sure MySQL Server is running before starting the application.
- Keep the VS Code terminal open while using the application.
- Do not share your `.env` file or database password publicly.
- Press `Ctrl + C` in the terminal to stop the application.