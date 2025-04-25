# PDF Password Unlocker

A simple web application built with Flask to remove password protection from PDF files. It allows users to upload a PDF, provide the password if it's encrypted, and download an unlocked version. This application uses PyMuPDF (fitz) for PDF manipulation.

## Features

*   Upload PDF files via a web interface.
*   Accepts optional password input for encrypted PDFs.
*   Removes password protection using PyMuPDF.
*   Provides immediate user feedback (success/error messages) using AJAX.
*   Initiates download of the unlocked PDF upon success.
*   Handles unencrypted PDFs gracefully.
*   Includes basic file size validation (default 10MB).
*   Structured with separate static files (CSS, JS).
*   Configured for deployment using Gunicorn.

## Technology Stack

*   **Backend:** Python 3, Flask, PyMuPDF (fitz), Gunicorn
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
*   **Deployment:** Configured for Render (using Python Runtime or Docker)

## Local Setup and Installation

Follow these steps to run the application locally:

1.  **Prerequisites:**
    *   Python 3 (e.g., 3.9 or newer recommended)
    *   `pip` (Python package installer)
    *   Git
    *   (Optional but recommended) A virtual environment tool (`venv`)

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd PDFPasswordUnlock
    ```

3.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    # Create environment
    python3 -m venv venv
    # Activate environment
    # On Windows:
    # .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: PyMuPDF might require system libraries (like `libmupdf-dev` on Debian/Ubuntu) if a pre-built wheel isn't available for your OS/architecture.*

## Running the Application Locally

1.  **Start the Flask Development Server:**
    ```bash
    python app.py
    ```
    *(Use `python3 app.py` if `python` defaults to Python 2)*

2.  **Access the Application:**
    Open your web browser and navigate to `http://127.0.0.1:10000` (or the address provided in the terminal).

The application will run in debug mode locally, providing auto-reloading and more detailed error messages.

## Attribution

Maintained with ❤️ by Adithya D M