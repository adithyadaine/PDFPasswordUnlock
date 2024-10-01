# app.py
from flask import Flask, request, send_file, render_template
import fitz  # PyMuPDF
import io
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Maximum file size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            logger.debug("Starting PDF processing")
            if 'pdf_file' not in request.files:
                return 'No file uploaded', 400
            
            file = request.files['pdf_file']
            password = request.form['password']
            
            if file.filename == '':
                return 'No file selected', 400
            
            # Check file size
            file.seek(0, io.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return 'File too large. Maximum size is 10 MB', 400
            
            # Read the PDF file
            pdf_data = file.read()
            
            # Open the PDF with PyMuPDF
            original_pdf = fitz.open(stream=pdf_data, filetype="pdf")
            logger.debug(f"PDF opened successfully. Encrypted: {original_pdf.is_encrypted}")
            
            # Check if the PDF is encrypted
            if original_pdf.is_encrypted:
                logger.debug("Attempting to decrypt PDF")
                try:
                    if not original_pdf.authenticate(password):
                        logger.error("Password authentication failed")
                        return 'Incorrect password', 400
                except:
                    return 'Error decrypting PDF', 400
                logger.debug("PDF decrypted successfully")
            
            # Create a new PDF document
            logger.debug("Creating new PDF")
            output_pdf = fitz.open()
            output_pdf.insert_pdf(original_pdf)
            logger.debug(f"New PDF created. Page count: {output_pdf.page_count}")
            
            # Save to bytes
            output_buffer = io.BytesIO()
            output_pdf.save(output_buffer)
            output_buffer.seek(0)
            
            # Close both PDF documents
            original_pdf.close()
            output_pdf.close()
            
            return send_file(
                output_buffer,
                as_attachment=True,
                download_name='unlocked.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
            return f'An error occurred: {str(e)}', 500
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)