import streamlit as st
import os
from PIL import Image
import json
import sys

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

# Import custom modules
from modules.ocr_processor import OCRProcessor
from modules.data_analyzer import DataAnalyzer
from modules.chatbot import DataChatbot
from modules.form_utils import FormUtils

# Page configuration
st.set_page_config(
    page_title="📊 form processing data tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Main title
st.title("📊 Product Manager Data Tool")
st.markdown("**Extract insights from forms and documents, then chat with your data for better team and client communication.**")

# Sidebar for API configuration
with st.sidebar:
    st.header("🔐 API Configuration")
    
    # API Keys
    mistral_key = st.text_input(
        "Mistral OCR API Key", 
        type="password",
        value=os.getenv("MISTRAL_API_KEY", ""),
        help="Required for OCR text extraction"
    )
    
    groq_key = st.text_input(
        "Groq API Key (for LLaMA)", 
        type="password",
        value=os.getenv("GROQ_API_KEY", ""),
        help="Required for AI analysis and chatbot"
    )
    
    st.divider()
    
    # Data Management
    st.header("📁 Data Management")
    if st.session_state.processed_data:
        st.metric("Processed Documents", len(st.session_state.processed_data))
        if st.button("🗑️ Clear All Data", type="secondary"):
            st.session_state.processed_data = []
            st.session_state.chat_history = []
            st.success("All data cleared!")
            st.rerun()
    else:
        st.info("No documents processed yet")

# Check API keys
if not mistral_key or not groq_key:
    st.warning("⚠️ Please enter both API keys in the sidebar to proceed.")
    st.info("💡 **Tip**: You can also set environment variables `MISTRAL_API_KEY` and `GROQ_API_KEY`")
    st.stop()

# Initialize processors
try:
    ocr_processor = OCRProcessor(mistral_key)
    data_analyzer = DataAnalyzer(groq_key)
    chatbot = DataChatbot(groq_key)
    form_utils = FormUtils()
except Exception as e:
    st.error(f"Error initializing processors: {str(e)}")
    st.stop()

# Main interface tabs
tab1, tab2, tab3 = st.tabs(["📤 Document Processing", "💬 Data Chatbot", "📈 Analytics Dashboard"])

with tab1:
    st.header("📤 Document Upload & Processing")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your form/document image",
            type=["jpg", "jpeg", "png", "pdf"],
            help="Supported formats: JPG, PNG, PDF"
        )
        
        if uploaded_file:
            # Display uploaded image
            if uploaded_file.type.startswith('image/'):
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Document", use_container_width=True)
            else:
                st.info(f"📄 Uploaded: {uploaded_file.name}")
            
            # Process button
            if st.button("🚀 Process Document", type="primary"):
                with st.spinner("Processing document..."):
                    try:
                        # OCR Processing
                        st.info("🔍 Extracting text with Mistral OCR...")
                        ocr_result = ocr_processor.process_image(uploaded_file)
                        
                        if not ocr_result or not ocr_result.get('text'):
                            st.error("❌ Failed to extract text. Please check your image and API key.")
                            if ocr_result and ocr_result.get('error'):
                                st.error(f"Error details: {ocr_result['error']}")
                            st.stop()
                        
                        # Form analysis
                        st.info("🧠 Analyzing document with AI...")
                        analysis_result = data_analyzer.analyze_document(
                            ocr_result['text'], 
                            ocr_result['form_type']
                        )
                        
                        # Combine results
                        processed_doc = {
                            'filename': uploaded_file.name,
                            'timestamp': form_utils.get_timestamp(),
                            'ocr_result': ocr_result,
                            'analysis': analysis_result,
                            'id': len(st.session_state.processed_data) + 1
                        }
                        
                        # Validate document data
                        is_valid, validation_message = form_utils.validate_document_data(processed_doc)
                        if not is_valid:
                            st.error(f"Document validation failed: {validation_message}")
                            st.stop()
                        
                        # Store in session state
                        st.session_state.processed_data.append(processed_doc)
                        
                        st.success("✅ Document processed successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Processing failed: {str(e)}")
                        st.exception(e)  # Show full traceback in development
    
    with col2:
        # Results display
        if st.session_state.processed_data:
            st.subheader("📋 Latest Results")
            latest_doc = st.session_state.processed_data[-1]
            
            # Document info
            st.info(f"**File**: {latest_doc['filename']}")
            st.info(f"**Type**: {latest_doc['ocr_result']['form_type'].title()}")
            st.info(f"**Processed**: {latest_doc['timestamp']}")
            
            # Tabbed results
            result_tab1, result_tab2, result_tab3 = st.tabs(["📄 Text", "🔑 Key-Values", "📝 Summary"])
            
            with result_tab1:
                st.text_area(
                    "Extracted Text",
                    latest_doc['ocr_result']['text'],
                    height=200,
                    key="ocr_text_display"
                )
                
                # Download button
                st.download_button(
                    "📥 Download Text",
                    data=latest_doc['ocr_result']['text'],
                    file_name=f"{latest_doc['filename']}_extracted.txt",
                    mime="text/plain"
                )
            
            with result_tab2:
                st.text_area(
                    "Key-Value Pairs & Completeness",
                    latest_doc['analysis']['key_values'],
                    height=200,
                    key="kv_display"
                )
            
            with result_tab3:
                st.text_area(
                    "AI Summary",
                    latest_doc['analysis']['summary'],
                    height=200,
                    key="summary_display"
                )
        else:
            st.info("👆 Upload and process a document to see results here")

with tab2:
    st.header("💬 Chat with Your Data")
    
    if not st.session_state.processed_data:
        st.info("📤 Please process some documents first to enable the chatbot.")
    else:
        # Chat interface
        st.subheader(f"💾 Available Data: {len(st.session_state.processed_data)} documents")
        
        # Display available documents
        with st.expander("📋 View Processed Documents"):
            for i, doc in enumerate(st.session_state.processed_data):
                st.write(f"**{i+1}.** {doc['filename']} ({doc['ocr_result']['form_type']}) - {doc['timestamp']}")
        
        # Suggested questions
        if st.session_state.processed_data:
            suggested_questions = chatbot.suggest_questions(st.session_state.processed_data)
            if suggested_questions:
                st.subheader("💡 Suggested Questions")
                col1, col2 = st.columns(2)
                for i, question in enumerate(suggested_questions[:6]):  # Show max 6 suggestions
                    if i % 2 == 0:
                        with col1:
                            if st.button(question, key=f"suggestion_{i}"):
                                # Add suggestion to chat
                                st.session_state.chat_history.append({"role": "user", "content": question})
                                with st.spinner("🤖 Thinking..."):
                                    try:
                                        response = chatbot.chat_with_data(question, st.session_state.processed_data)
                                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Chatbot error: {str(e)}")
                    else:
                        with col2:
                            if st.button(question, key=f"suggestion_{i}"):
                                # Add suggestion to chat
                                st.session_state.chat_history.append({"role": "user", "content": question})
                                with st.spinner("🤖 Thinking..."):
                                    try:
                                        response = chatbot.chat_with_data(question, st.session_state.processed_data)
                                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Chatbot error: {str(e)}")
        
        # Chat input
        user_question = st.chat_input("Ask me anything about your processed documents...")
        
        if user_question:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            
            # Generate response
            with st.spinner("🤖 Thinking..."):
                try:
                    response = chatbot.chat_with_data(
                        user_question, 
                        st.session_state.processed_data
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.rerun()
                except Exception as e:
                    st.error(f"Chatbot error: {str(e)}")
        
        # Display chat history
        if st.session_state.chat_history:
            st.subheader("💬 Conversation")
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.chat_message("user").write(message["content"])
                else:
                    st.chat_message("assistant").write(message["content"])
        
        # Clear chat button
        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()

with tab3:
    st.header("📈 Analytics Dashboard")
    
    if not st.session_state.processed_data:
        st.info("📤 Process some documents to see analytics.")
    else:
        # Get statistics
        stats = form_utils.get_document_stats(st.session_state.processed_data)
        
        # Analytics overview
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Documents", stats['total_documents'])
        
        with col2:
            st.metric("Document Types", len(stats['document_types']))
        
        with col3:
            st.metric("Total Characters", f"{stats['total_characters']:,}")
        
        # Document type distribution
        st.subheader("📊 Document Type Distribution")
        if stats['document_types']:
            st.bar_chart(stats['document_types'])
        
        # Processing report
        st.subheader("📋 Processing Report")
        with st.expander("View Detailed Report"):
            report = form_utils.generate_processing_report(st.session_state.processed_data)
            st.markdown(report)
        
        # Recent documents
        st.subheader("📅 Recent Documents")
        for doc in reversed(st.session_state.processed_data[-5:]):  # Show last 5
            with st.expander(f"📄 {doc['filename']} - {doc['timestamp']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Type**: {doc['ocr_result']['form_type'].title()}")
                    st.write(f"**Text Length**: {len(doc['ocr_result']['text'])} characters")
                    if 'confidence' in doc['ocr_result']:
                        st.write(f"**OCR Confidence**: {doc['ocr_result']['confidence']}")
                with col2:
                    preview = form_utils.format_document_preview(doc, max_length=150)
                    st.markdown(preview)
        
        # Export functionality
        st.subheader("📥 Export Data")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export as JSON"):
                try:
                    export_data = form_utils.export_data(
                        st.session_state.processed_data, 
                        st.session_state.chat_history
                    )
                    
                    st.download_button(
                        "📥 Download JSON Export",
                        data=json.dumps(export_data, indent=2),
                        file_name=f"pm_data_export_{form_utils.get_timestamp().replace(':', '-').replace(' ', '_')}.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col2:
            if st.button("📈 Export as CSV"):
                try:
                    csv_data = form_utils.export_to_csv(st.session_state.processed_data)
                    if csv_data:
                        st.download_button(
                            "📥 Download CSV Export",
                            data=csv_data,
                            file_name=f"pm_documents_{form_utils.get_timestamp().replace(':', '-').replace(' ', '_')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No data to export")
                except Exception as e:
                    st.error(f"CSV export failed: {str(e)}")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
    📊 Product Manager Data Tool | Built with Streamlit, Mistral AI & Groq
</div>
""", unsafe_allow_html=True)
