# Usage Guide

## Start from source

Install the required dependencies:

```text
pip install -r requirements.txt
```

Start the application:

```text
python run.py
```

## Basic workflow

1. Select or enter the month you want to track.
2. Enter the monthly target hours.
3. Enter the yearly vacation allowance if vacation tracking is needed.
4. Set the standard day hours used for vacation and sick-day calculations.
5. Add work days, vacation days or sick days.
6. Check the monthly overview for target status and balance.
7. Review the carry-over balance for the following months.

## Data storage

The application saves data locally as JSON in the user profile application-data area.

The data is not uploaded automatically and is not synchronized with external services.

## Important notes

- Always create backups before replacing the application or editing data files manually.
- Check all calculations manually before using them for payroll, tax, legal or official documentation.
- This software is a helper tool and does not replace professional payroll or legal advice.
