import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF, for reading PDFs
import io     # For handling in-memory files

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="LectureLama 🦙", 
    page_icon="f_A6_99", # Llama emoji
    layout="wide"
)

# --- API KEY & MODEL CONFIGURATION ---
try:
    # Get the API key from Streamlit's secret management
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except (KeyError, FileNotFoundError):
    # This error shows up on the app if the key is missing
    st.error("⚠️ **API Key not found!** Please add your `GOOGLE_API_KEY` to the Streamlit Secrets.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
# 'session_state' is Streamlit's way of remembering variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- 1. LOGIN PAGE FUNCTION ---
def show_login_page():
    """Displays the login page."""
    
    st.title("Welcome to LectureLama")
    st.subheader("Your AI Study Buddy")
    
    st.write("") 
    st.info("Built for B.Tech CSE Students. This is a demo—you can enter any username and password to proceed.")

    # Center the login form
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g., cse_student")
            password = st.text_input("Password", type="password", placeholder="e.g., 12345")
            
            login_button = st.form_submit_button("Sign In", use_container_width=True)
            
            if login_button:
                if username and password:
                    # If login is successful, set these session variables
                    st.session_state.logged_in = True
                    st.session_state.username = username 
                    st.rerun() # Rerun the script to show the main app
                else:
                    st.error("Please enter both username and password.")

# --- 2. MAIN APP FUNCTION ---
def show_main_app():
    """Displays the main application after login."""
    
    # --- Sidebar (for user info and logout) ---
    with st.sidebar:
        st.success(f"Welcome, **{st.session_state.username}**!")
        st.markdown("---")
        
        if st.button("Clear Chat History", use_container_width=True, type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

        if st.button("Logout", use_container_width=True):
            # Reset all session variables on logout
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.chat_history = []
            st.rerun() 

    # --- Main Chat Interface ---
    st.title("LectureLama 🦙")
    st.caption(f"Ready to help you, {st.session_state.username}! Upload an image or PDF to start.")

    # Two-column layout
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Upload Your Material")
        
        # Added 'pdf' to the accepted types
        uploaded_file = st.file_uploader(
            "Upload notes, diagrams, or PDF lectures", 
            type=["jpg", "jpeg", "png", "pdf"]
        )
        
        # This list will hold all images (from PDF or single upload)
        images_to_process = []
        
        if uploaded_file:
            # Logic to handle PDF files
            if uploaded_file.type == "application/pdf":
                with st.spinner("Converting PDF pages to images..."):
                    # Read the PDF file into memory
                    pdf_bytes = uploaded_file.read()
                    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    # Loop through each page of the PDF
                    for page_num in range(len(pdf_doc)):
                        page = pdf_doc.load_page(page_num)
                        # Convert the page to a high-quality PNG image
                        pix = page.get_pixmap(dpi=150) # Higher DPI for better quality
                        img_bytes = pix.tobytes("png")
                        pil_image = Image.open(io.BytesIO(img_bytes))
                        images_to_process.append(pil_image)
                    
                    st.success(f"Converted {len(images_to_process)} PDF pages.")
                    # Display the first page as a preview
                    # --- FIX: Replaced use_column_width with use_container_width ---
                    st.image(images_to_process[0], caption=f"Page 1 of {len(images_to_process)}", use_container_width=True)
            
            # This is the original logic for single images
            else:
                pil_image = Image.open(uploaded_file)
                images_to_process.append(pil_image)
                # Display the single uploaded image
                # --- FIX: Replaced use_column_width with use_container_width ---
                st.image(pil_image, caption="Your uploaded image", use_container_width=True)

        user_question = st.text_input("What's confusing you about this material?")

        if st.button("Ask LectureLama"):
            # Check the list instead of the file
            if not images_to_process:
                st.warning("Please upload an image or PDF first!")
            elif not user_question:
                st.warning("Please ask a question!")
            else:
                with st.spinner("Lama is reading your material... 🦙"):
                    try:
                        model = genai.GenerativeModel('models/gemini-flash-latest')
                        
                        prompt = f"""
                        You are LectureLama, an expert university tutor.
                        The user has provided one or more images (which could be pages from a PDF) and a question.
                        Analyze all images to answer the question.
                        If it's handwritten, do your best to read it.
                        Explain concepts simply and clearly.
                        
                        User Question: {user_question}
                        """
                        
                        # Create a content list with the prompt + all images
                        # This sends the prompt first, then every page of the PDF
                        content_list = [prompt] + images_to_process
                        
                        response = model.generate_content(content_list)
                        
                        # Store in chat history
                        st.session_state.chat_history.append(("You (Material)", user_question))
                        st.session_state.chat_history.append(("Lama 🦙", response.text))
                        st.rerun() # Rerun to show the new chat history immediately
                        
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
    
    with col2:
        st.subheader("Chat History")
        
        # Create a scrollable container for the chat
        with st.container(height=500, border=True):
            if not st.session_state.chat_history:
                st.info("Your chat with LectureLama will appear here.")
            else:
                # Display the chat history
                for role, text in st.session_state.chat_history:
                    if role == "Lama 🦙":
                        st.markdown(f"**{role}:** {text}")
                    else:
                        st.markdown(f"**{role}:** *{text}*")

# --- MAIN LOGIC ---
# This is the "gatekeeper" of the app.
if st.session_state.logged_in:
    show_main_app()
else:
    show_login_page()