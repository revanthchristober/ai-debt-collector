# Debt Collector AI

Debt Collector AI is an advanced Python application that automates debt management by integrating with Airtable and Stripe APIs. It retrieves new contact data from Airtable, creates Stripe customers and prices, generates or updates payment links, and synchronizes records—all while operating strictly within business hours (defaulted to Brisbane time, but easily customizable).

## Key Features

- **Automated Contact Retrieval:**  
  Seamlessly fetches new contact records from Airtable based on pre-defined criteria.
  
- **Stripe Integration:**  
  Automatically creates Stripe customers and pricing objects based on the contact’s debt details.
  
- **Dynamic Payment Links:**  
  Generates or updates payment links with Stripe, ensuring a smooth payment process.
  
- **Record Synchronization:**  
  Updates Airtable records with the latest payment link and process status.
  
- **Business Hours Enforcement:**  
  Tasks run only during business hours (Brisbane by default), minimizing off-hours processing.

## System Architecture

The application is built on a modern Django framework with asynchronous task handling via Celery. Here's an overview of the components:

- **Django Web Interface:**  
  A basic web server that provides a status endpoint and acts as the central hub.
  
- **Celery Task Scheduler:**  
  Background tasks are scheduled to run at fixed intervals (e.g., every 30 seconds) using Celery with a Redis broker.
  
- **External API Integrations:**  
  Uses Airtable for data storage and management and Stripe for payment processing.

## Prerequisites

- **Python 3.6+**
- **Redis:** Required for Celery task management.
- **Airtable Account:** With an API key, Base ID, and Contacts Table ID.
- **Stripe Account:** With a valid API key for handling payments.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/VW3st/debt-collector-ai.git
cd debt-collector-ai
```

### 2. Install Dependencies

Install the required packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root of your project with the following content (customize values as needed):

```ini
API_KEY=your_airtable_api_key
BASE_ID=your_airtable_base_id
CONTACTS_TABLE_ID=your_airtable_contacts_table_id
STRIPE_API_KEY=your_stripe_api_key
DJANGO_SECRET_KEY=your_django_secret_key
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Customizing the Timezone

By default, the application processes contacts using the Brisbane timezone. To change this:
- Open `contacts/tasks.py`
- Modify the `get_brisbane_time` function by replacing `'Australia/Brisbane'` with your desired timezone.

## Running the Application

### 1. Apply Database Migrations

```bash
python manage.py migrate
```

### 2. Start the Django Server

```bash
python manage.py runserver
```

### 3. Start Celery Workers and Scheduler

Open two separate terminal windows and run the following commands:

**Celery Worker:**

```bash
celery -A myproject worker --loglevel=info
```

**Celery Beat Scheduler:**

```bash
celery -A myproject beat --loglevel=info
```

The Django server will be available at `http://localhost:8000/`, and Celery will continuously process background tasks at the configured interval.

## Contributing

Contributions are welcome! To get started:
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Describe your feature"
   ```
4. Push the branch:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a pull request with a detailed description of your changes.

## License

This project is licensed under The GNU General Public License v3.0. Please refer to the [LICENSE](LICENSE) file for further details.

## Contact

If you have any questions or need further assistance, please open an issue in the repository or contact me directly.
