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
st.title("📊 form processing data tool")
st.markdown("**Extract insights from forms and documents, then chat with your data for better team and client communication.**")

# Sidebar for data management (API keys now handled via secrets)
with st.sidebar:
    st.header("📊 Application Status")
    
    # Check API keys from secrets
    try:
        mistral_key = st.secrets["MISTRAL_API_KEY"]
        groq_key = st.secrets["GROQ_API_KEY"]
        st.success("🔐 API Keys: Configured")
        st.info("Ready to process documents!")
    except KeyError as e:
        st.error(f"🔐 Missing API Key: {str(e)}")
        st.error("Please configure secrets in Streamlit Cloud or local secrets.toml file")
        st.stop()
    except Exception as e:
        st.error(f"🔐 Configuration Error: {str(e)}")
        st.stop()
    
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

# Initialize processors with API keys from secrets
try:
    ocr_processor = OCRProcessor(mistral_key)
    data_analyzer = DataAnalyzer(groq_key)
    chatbot = DataChatbot(groq_key)
    form_utils = FormUtils()
except Exception as e:
    st.error(f"Error initializing processors: {str(e)}")
    st.error("Please check your API keys configuration in secrets")
    st.stop()

# Main interface tabs
tab1, tab2, tab3 = st.tabs(["📤 Document Processing", "💬 Data Chatbot", "📈 Analytics Dashboard"])

with tab1:
    st.header("📤 Document Upload & Processing")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your form/document image",
            type=["jpg", "jpeg", "png"],
            help="Supported formats: JPG, PNG"
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
                            st.error("❌ Failed to extract text. Please check your image quality.")
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
        st.subheader("📄 Processing Report")
        report_data = []
        for doc in st.session_state.processed_data:
            report_data.append({
                'Document': doc['filename'],
                'Type': doc['ocr_result']['form_type'],
                'Processed': doc['timestamp'],
                'Characters': len(doc['ocr_result']['text'])
            })
        
        if report_data:
            st.dataframe(report_data, use_container_width=True)
        
        # Export functionality
        st.subheader("📥 Export Data")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export Analytics as JSON"):
                export_data = {
                    'stats': stats,
                    'documents': st.session_state.processed_data,
                    'export_timestamp': form_utils.get_timestamp()
                }
                st.download_button(
                    "📥 Download Analytics Data",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"form_analytics_{form_utils.get_timestamp().replace(':', '-').replace(' ', '_')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📋 Export Processing Summary"):
                summary_text = f"Form Processing Summary - {form_utils.get_timestamp()}\n"
                summary_text += "=" * 50 + "\n\n"
                summary_text += f"Total Documents Processed: {stats['total_documents']}\n"
                summary_text += f"Document Types: {len(stats['document_types'])}\n"
                summary_text += f"Total Characters Extracted: {stats['total_characters']:,}\n\n"
                
                summary_text += "Document Details:\n"
                summary_text += "-" * 20 + "\n"
                for i, doc in enumerate(st.session_state.processed_data):
                    summary_text += f"{i+1}. {doc['filename']}\n"
                    summary_text += f"   Type: {doc['ocr_result']['form_type']}\n"
                    summary_text += f"   Processed: {doc['timestamp']}\n"
                    summary_text += f"   Summary: {doc['analysis']['summary'][:100]}...\n\n"
                
                st.download_button(
                    "📥 Download Summary Report",
                    data=summary_text,
                    file_name=f"processing_summary_{form_utils.get_timestamp().replace(':', '-').replace(' ', '_')}.txt",
                    mime="text/plain"
                )

# Footer
st.divider()
st.markdown("---")
st.markdown("**📊 Form Processing Data Tool** - Powered by Mistral OCR & Groq LLaMA AI")
st.markdown("Process documents seamlessly without managing API keys. Ready for production deployment!")
