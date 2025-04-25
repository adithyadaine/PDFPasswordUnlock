from flask import Flask, request, send_file, render_template, flash, redirect, url_for, jsonify, g
import fitz  # PyMuPDF
import io
import logging
import os
import time
# import sys # No longer needed

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
    if request.path != '/health':  # Don't log health checks
        now = time.time()
        duration = round(now - g.start, 2)
        log_params = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration': duration,
            'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
        }
        logger.info(f"Request: {log_params}")
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            logger.debug("Starting PDF processing")

            if 'pdf_file' not in request.files:
                flash('No file uploaded', 'danger')
                return redirect(url_for('index'))

            file = request.files['pdf_file']
            password = request.form['password']

            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(url_for('index'))

            if not file.filename.lower().endswith('.pdf'):
                flash('Please upload a PDF file', 'danger')
                return redirect(url_for('index'))

            # Check file size
            file.seek(0, io.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_FILE_SIZE:
                flash(f'File too large. Maximum size is {MAX_FILE_SIZE/1024/1024:.1f}MB', 'danger')
                return redirect(url_for('index'))

            try:
                # Read the PDF file
                pdf_data = file.read()

                # Open the PDF with PyMuPDF
                original_pdf = fitz.open(stream=pdf_data, filetype="pdf")
                logger.debug(f"PDF opened successfully. Encrypted: {original_pdf.is_encrypted}")

                # Check if the PDF is encrypted
                if original_pdf.is_encrypted:
                    logger.debug("PDF is encrypted. Checking for password.")
                    # Check if password was provided for encrypted PDF
                    if not password:
                        logger.warning("Encrypted PDF uploaded, but no password provided.")
                        flash('This PDF is password-protected. Please provide the password.', 'warning')
                        original_pdf.close() # Close the document before redirecting
                        return redirect(url_for('index'))

                    logger.debug("Attempting to decrypt PDF with provided password.")
                    try:
                        # Attempt authentication
                        if not original_pdf.authenticate(password):
                            logger.warning("Incorrect password provided.")
                            flash('Incorrect password provided.', 'danger')
                            original_pdf.close() # Close the document before redirecting
                            return redirect(url_for('index'))
                        # If authentication succeeds, PyMuPDF removes encryption internally for this object
                        logger.debug("PDF decrypted successfully with password.")
                    except Exception as e:
                        # This might catch rare errors during the authentication process itself
                        logger.error(f"Error during password authentication: {str(e)}")
                        flash('Error decrypting PDF. Please check the password or the file.', 'danger')
                        original_pdf.close() # Close the document before redirecting
                        return redirect(url_for('index'))
                else:
                    logger.debug("PDF is not encrypted.")

                # Create a new PDF document (this effectively saves without encryption)
                logger.debug("Creating new unlocked PDF")
                output_pdf = fitz.open()
                output_pdf.insert_pdf(original_pdf)
                logger.debug(f"New PDF created. Page count: {output_pdf.page_count}")

                # Save to bytes
                output_buffer = io.BytesIO()
                # Optional: Experiment with save options if quality issues persist
                output_pdf.save(output_buffer) # , garbage=4, deflate=True)
                output_buffer.seek(0)

                # Close both PDF documents
                original_pdf.close()
                output_pdf.close()

                logger.info(f"Successfully processed and unlocked '{file.filename}'")

                # --- Flash success message ---
                flash(f'Successfully unlocked "{file.filename}"!', 'success')
                # ---------------------------

                return send_file(
                    output_buffer,
                    as_attachment=True,
                    download_name=f'unlocked_{file.filename}',
                    mimetype='application/pdf'
                )

            except fitz.FileDataError:
                logger.warning(f"Invalid or corrupted PDF file uploaded: {file.filename}")
                flash('Invalid or corrupted PDF file', 'danger')
                return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"An unexpected error occurred during POST: {str(e)}", exc_info=True)
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('index'))

    # GET request or initial page load
    return render_template('index.html')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found error for path: {request.path}")
    return render_template('index.html'), 404 # Consider a dedicated 404.html

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}", exc_info=True)
    return render_template('index.html'), 500 # Consider a dedicated 500.html

if __name__ == '__main__':
    # This will only be used when running locally
    port = int(os.environ.get('PORT', 10000))
    # Use debug=True for development (auto-reload, detailed errors)
    # WARNING: Do NOT use debug=True in a production environment!
    app.run(host='0.0.0.0', port=port, debug=True)