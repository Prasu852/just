import os
import PyPDF2  # Import PyPDF2 for PDF text extraction
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
request: I am seeking a comprehensive analysis and optimization of my CV (x) in alignment with a specific job description (y). Please provide detailed recommendations for enhancing the relevance of my CV to the targeted job opportunity. Additionally, I request the creation of 9-10 concise, impactful sentences that will strengthen my CV and increase my chances of securing the position.

Objective: To optimize my CV to effectively showcase my qualifications and experiences in a manner that aligns with the requirements of the job description (y), thereby increasing my likelihood of securing the position.

Please note: I have attached both my CV (x) and the job description (y) for your reference.
"""
resume_prompt_template = PromptTemplate(
    input_variables=["resume_text", "jd_text"],
    template="""Resume Text: {resume_text}
 Job Description: {jd_text}
 provide extact  modify  sentence the based on the job description, without  mentoined the  educaion background  .
 Include summary adding required skills, writing important notes,priovde. 
 provide the 4 to  5 variations   sentence for each sentence in each section.
 *example:Variation 1: [First sentence].
- Variation 2: [Second sentence].
- Variation 3: [Third sentence].
- Variation 4: [Fourth sentence].
- Variation 5: [Fifth sentence].
 separatly  in each section and making other relevant changes to improve the resume's alignment with the JD.all the sentence should be segrigate in difference."""

    
)

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to extract text from PDF using PyPDF2
def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
    
    print(f"Opening PDF file: {pdf_path}")
    
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()
    
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
def process_resume_and_jd(resume_path, jd_path=None, jd_text=None):
    # Extract resume text
    ext = resume_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        resume_text = extract_text_from_pdf(resume_path)
    elif ext == 'docx':
        resume_text = extract_text_from_docx(resume_path)

    # Extract JD text
    if jd_path:
        jd_ext = jd_path.rsplit('.', 1)[1].lower()
        if jd_ext == 'pdf':
            jd_text = extract_text_from_pdf(jd_path)
        elif jd_ext == 'docx':
            jd_text = extract_text_from_docx(jd_path)
    
    # Create prompt text using the template
    prompt_text = resume_prompt_template.format(resume_text=resume_text, jd_text=jd_text)
    
    # Use the language model to get the response
    response = llm(prompt_text)
    response=response.replace("**", "")
    
    return response
    
    

# Route for handling file upload and processing
@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == "POST":
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
        
        resume_file = request.files['resume']
        jd_text = request.form.get('jd')  # JD text can be pasted as input
        
        jd_file = request.files.get('jd_file')  # JD file can also be uploaded
        
        if resume_file and allowed_file(resume_file.filename):
            filename = secure_filename(resume_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(file_path)
            print(f"Resume file saved at: {file_path}")
            
            # Check if JD is uploaded as file
            if jd_file and allowed_file(jd_file.filename):
                jd_filename = secure_filename(jd_file.filename)
                jd_file_path = os.path.join(app.config['UPLOAD_FOLDER'], jd_filename)
                jd_file.save(jd_file_path)
                print(f"JD file saved at: {jd_file_path}")
                
                # Process the resume and JD (JD as file)
                try:
                    suggestions = process_resume_and_jd(file_path, jd_path=jd_file_path)
                    print(f"Suggestions generated: {suggestions}")
                    return jsonify({'suggestions': suggestions})
                except Exception as e:
                    print(f"Error processing files: {e}")
                    return jsonify({'error': f"Error processing files: {e}"}), 500

            # Check if JD text is provided
            elif jd_text:
                print(f"JD text received.")
                
                # Process the resume and JD (JD as text)
                try:
                    suggestions = process_resume_and_jd(file_path, jd_text=jd_text)
                    print(f"Suggestions generated: {suggestions}")
                    return jsonify({'suggestions': suggestions})
                except Exception as e:
                    print(f"Error processing files: {e}")
                    return jsonify({'error': f"Error processing files: {e}"}), 500
            
            return jsonify({'error': 'No job description provided. Upload a file or paste the text.'}), 400
        
        return jsonify({'error': 'Invalid file format. Please upload PDF or DOCX.'}), 400

    elif request.method == 'GET':
        return jsonify({'message': 'success'}), 200

# Main function to run the app
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host="0.0.0.0", port=8080)
