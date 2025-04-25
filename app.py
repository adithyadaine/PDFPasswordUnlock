from flask import Flask, request, send_file, render_template, flash, redirect, url_for, jsonify, g
import fitz  # PyMuPDF
import io
import logging
import os
import time
import uuid # For generating unique IDs
from threading import Lock # For basic thread safety on the dictionary

# --- Temporary Storage (In-Memory) ---
# WARNING: This is simple but not robust for production with multiple workers
# or long-running processes. Data is lost on restart. Consider Redis or
# a temporary file system with cleanup for production.
temp_unlocked_files = {}
temp_file_lock = Lock()
# -------------------------------------

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Maximum file size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Monitoring middleware
@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def log_request(response):
    # Log all requests now, including successful AJAX and downloads
    now = time.time()
    duration = round(now - g.start, 2)
    log_params = {
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'duration': duration,
        'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
    }
    # Don't log file data for downloads
    if request.path.startswith('/download/'):
         logger.info(f"Download Request: {log_params}")
    else:
        logger.info(f"Request: {log_params}")
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET', 'POST'])
def index():
    # --- Handle POST requests via AJAX ---
    if request.method == 'POST':
        original_pdf = None # Ensure cleanup happens
        try:
            logger.debug("Starting PDF processing (AJAX)")

            if 'pdf_file' not in request.files:
                logger.warning("AJAX POST: No file part")
                return jsonify({"success": False, "error": "No file uploaded"}), 400

            file = request.files['pdf_file']
            password = request.form.get('password', '') # Use .get for safety

            if file.filename == '':
                logger.warning("AJAX POST: No file selected")
                return jsonify({"success": False, "error": "No file selected"}), 400

            if not file.filename.lower().endswith('.pdf'):
                logger.warning(f"AJAX POST: Invalid file type: {file.filename}")
                return jsonify({"success": False, "error": "Please upload a PDF file"}), 400

            # Check file size (read into memory - careful with very large limits)
            pdf_data = file.read()
            file_size = len(pdf_data)

            if file_size == 0:
                 logger.warning("AJAX POST: Empty file uploaded")
                 return jsonify({"success": False, "error": "Empty file uploaded"}), 400

            if file_size > MAX_FILE_SIZE:
                logger.warning(f"AJAX POST: File too large: {file_size} bytes")
                return jsonify({"success": False, "error": f'File too large. Maximum size is {MAX_FILE_SIZE/1024/1024:.1f}MB'}), 413 # Payload Too Large

            # --- PDF Processing Logic ---
            try:
                original_pdf = fitz.open(stream=pdf_data, filetype="pdf")
                logger.debug(f"PDF opened. Encrypted: {original_pdf.is_encrypted}")

                if original_pdf.is_encrypted:
                    if not password:
                        logger.warning("AJAX POST: Password required but not provided.")
                        # No need to close original_pdf here, finally block handles it
                        return jsonify({"success": False, "error": "This PDF is password-protected. Please provide the password."}), 422 # Unprocessable Entity

                    logger.debug("Attempting authentication")
                    if not original_pdf.authenticate(password):
                        logger.warning("AJAX POST: Incorrect password.")
                        # No need to close original_pdf here, finally block handles it
                        return jsonify({"success": False, "error": "Incorrect password provided."}), 422 # Unprocessable Entity
                    logger.debug("Authentication successful.")

                # Create unlocked PDF
                output_pdf_doc = fitz.open()
                output_pdf_doc.insert_pdf(original_pdf)
                output_buffer = io.BytesIO()
                output_pdf_doc.save(output_buffer)
                output_pdf_doc.close()
                output_pdf_data = output_buffer.getvalue()

                # --- Store temporarily ---
                download_id = str(uuid.uuid4())
                with temp_file_lock:
                    temp_unlocked_files[download_id] = {
                        "data": output_pdf_data,
                        "filename": f'unlocked_{file.filename}',
                        "timestamp": time.time()
                        # Add cleanup logic here if needed (e.g., based on timestamp)
                    }
                logger.info(f"Stored unlocked file with ID: {download_id}")

                return jsonify({
                    "success": True,
                    "message": f'Successfully unlocked "{file.filename}"!',
                    "download_id": download_id
                }), 200

            except fitz.FileDataError:
                logger.warning(f"AJAX POST: Invalid or corrupted PDF: {file.filename}")
                return jsonify({"success": False, "error": "Invalid or corrupted PDF file"}), 422
            except Exception as e: # Catch auth errors or other fitz errors
                 logger.error(f"Error during PDF processing/auth: {str(e)}", exc_info=True)
                 return jsonify({"success": False, "error": "Error processing PDF. Check password or file."}), 500
            finally:
                 if original_pdf:
                     original_pdf.close() # Ensure original PDF is closed

        except Exception as e:
            logger.error(f"Unexpected error during AJAX POST: {str(e)}", exc_info=True)
            return jsonify({"success": False, "error": "An unexpected server error occurred."}), 500

    # --- Handle GET requests (initial page load) ---
    # Flash messages might still be useful if navigating directly after an action
    # or for non-AJAX errors, though less common now.
    return render_template('index.html')


# --- New Download Route ---
@app.route('/download/<download_id>')
def download_file(download_id):
    logger.debug(f"Download request received for ID: {download_id}")
    file_info = None
    with temp_file_lock:
        # Use .pop() to retrieve and remove the item atomically (if found)
        file_info = temp_unlocked_files.pop(download_id, None)

    if file_info:
        logger.info(f"Serving file for download ID: {download_id}, Filename: {file_info['filename']}")
        return send_file(
            io.BytesIO(file_info["data"]),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=file_info["filename"]
        )
    else:
        logger.warning(f"Download ID not found or already used: {download_id}")
        flash("Download link expired or invalid.", "warning") # Flash for the redirect
        return redirect(url_for('index')) # Redirect back to main page


# Error handlers (keep these, they handle direct access errors etc.)
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found error for path: {request.path}")
    # Check if request expects JSON (AJAX) or HTML
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(error='Not Found'), 404
    return render_template('index.html'), 404 # Or a dedicated 404.html

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(error='Internal Server Error'), 500
    return render_template('index.html'), 500 # Or a dedicated 500.html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True) # Keep debug=True for development
