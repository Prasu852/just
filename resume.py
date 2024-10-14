import os
import fitz  # PyMuPDF
import docx
from flask import Flask, request, jsonify
from langchain_community.llms import ollama
from langchain.prompts import PromptTemplate
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Initialize the language model
llm = ollama.Ollama(model="llama3", temperature=0.7)

# Flask app setup
app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from React
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}

# Initialize the prompt template
DEFAULT_SYSTEM_PROMPT = """\
As an expert in resume review and analysis, I will analyze the provided resume and job description (JD) to suggest key improvements. This includes adding important skills, highlighting critical points, and making relevant changes to better align the resume with the JD. I ensure my suggestions are accurate, professional, and reflect proficient vocabulary.
"""

resume_prompt_template = PromptTemplate(
    input_variables=["resume_text", "jd_text"],
    template="""Resume Text: {resume_text}

Job Description: {jd_text}

Please provide suggestions to modify the resume based on the job description. Include adding required skills, writing important notes, and making other relevant changes to improve the resume's alignment with the JD."""
)

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    print(f"Opening PDF file: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    print("PDF text extraction completed.")
    return text

# Function to extract text from DOCX
def extract_text_from_docx(docx_path):
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")
    
    print(f"Opening DOCX file: {docx_path}")
    
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    print("DOCX text extraction completed.")
    return text

# Process the resume and JD based on file types
def process_resume_and_jd(resume_path, jd_text):
    # Extract resume text
    ext = resume_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        resume_text = extract_text_from_pdf(resume_path)
    elif ext == 'docx':
        resume_text = extract_text_from_docx(resume_path)
    
    # Create prompt text using the template
    prompt_text = resume_prompt_template.format(resume_text=resume_text, jd_text=jd_text)
    
    # Use the language model to get the response
    response = llm(prompt_text)
    return response.replace("**", "")

# Route for handling file upload and processing
@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == "POST":
        if 'resume' not in request.files or 'jd' not in request.form:
            return jsonify({'error': 'No file or job description uploaded'}), 400

        resume_file = request.files['resume']
        jd_text = request.form['jd']

        if resume_file and allowed_file(resume_file.filename):
            filename = secure_filename(resume_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(file_path)
            print(f"Resume file saved at: {file_path}")

            # Process the resume and job description
            try:
                suggestions = process_resume_and_jd(file_path, jd_text)
                print(f"Suggestions generated: {suggestions}")
                return jsonify({'suggestions': suggestions})
            except Exception as e:
                print(f"Error processing files: {e}")
                return jsonify({'error': f"Error processing files: {e}"}), 500
        
        return jsonify({'error': 'Invalid file format. Please upload PDF or DOCX.'}), 400

    elif request.method == 'GET':
        return jsonify({'message': 'success'}), 200

# Main function to run the app
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host="0.0.0.0", port=8080)


