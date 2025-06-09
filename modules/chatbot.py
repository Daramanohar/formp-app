from groq import Groq
import streamlit as st
from typing import List, Dict, Any
import json

class DataChatbot:
    """Chatbot for interacting with processed document data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Groq(api_key=api_key)
    
    def prepare_context(self, processed_data: List[Dict[str, Any]]) -> str:
        """Prepare context from processed documents for the chatbot."""
        context = "Available Documents and Data:\n\n"
        
        for i, doc in enumerate(processed_data, 1):
            context += f"Document {i}: {doc['filename']}\n"
            context += f"- Type: {doc['ocr_result']['form_type']}\n"
            context += f"- Processed: {doc['timestamp']}\n"
            context += f"- Text Preview: {doc['ocr_result']['text'][:200]}...\n"
            
            # Add key insights from analysis
            if 'analysis' in doc and 'summary' in doc['analysis']:
                context += f"- Summary: {doc['analysis']['summary'][:150]}...\n"
            
            context += "\n" + "="*50 + "\n\n"
        
        return context
    
    def generate_response(self, user_question: str, context: str) -> str:
        """Generate chatbot response based on user question and document context."""
        try:
            system_prompt = """
            You are a helpful AI assistant for product managers. You help them analyze and communicate insights from processed documents.
            
            Your role is to:
            1. Answer questions about the processed documents
            2. Provide insights for team and client communication
            3. Suggest action items based on document analysis
            4. Help create summaries and reports
            5. Identify trends and patterns across documents
            
            Be conversational, helpful, and focus on practical insights that would be valuable for product management and team communication.
            
            If you don't have specific information to answer a question, be honest about it and suggest what additional information might be helpful.
            """
            
            user_prompt = f"""
            Based on the following processed documents:

            {context}

            Please answer this question: {user_question}
            
            Provide a helpful response that focuses on actionable insights for product management and team communication.
            """

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content
            
        except Exception as e:
            return f"I encountered an error while processing your question: {str(e)}. Please try rephrasing your question or check if the API service is available."
    
    def suggest_questions(self, processed_data: List[Dict[str, Any]]) -> List[str]:
        """Suggest relevant questions based on processed data."""
        if not processed_data:
            return []
        
        # Analyze document types and generate relevant questions
        form_types = [doc['ocr_result']['form_type'] for doc in processed_data]
        unique_types = set(form_types)
        
        suggestions = [
            "What are the key insights from all processed documents?",
            "Can you summarize the main findings for my team?",
            "What action items should I communicate to stakeholders?",
        ]
        
        # Add type-specific suggestions
        if 'medical' in unique_types:
            suggestions.extend([
                "What are the key medical findings across the documents?",
                "Are there any compliance issues I should be aware of?",
                "What patient data insights are most important?"
            ])
        
        if 'insurance' in unique_types:
            suggestions.extend([
                "What are the key coverage details from insurance documents?",
                "Are there any claim issues that need attention?",
                "What policy information should I highlight to the team?"
            ])
        
        if 'financial' in unique_types:
            suggestions.extend([
                "What are the key financial metrics from the documents?",
                "Are there budget implications I should communicate?",
                "What financial risks should the team be aware of?"
            ])
        
        # Add document count specific suggestions
        if len(processed_data) > 1:
            suggestions.extend([
                "Can you compare the key differences between documents?",
                "What trends do you see across all documents?",
                "Which document requires the most urgent attention?"
            ])
        
        return suggestions[:8]  # Return top 8 suggestions
    
    def chat_with_data(self, user_question: str, processed_data: List[Dict[str, Any]]) -> str:
        """Main method for chatting with processed document data."""
        if not processed_data:
            return "I don't have any processed documents to analyze yet. Please upload and process some documents first, then I'll be happy to help you analyze them!"
        
        # Prepare context from all processed documents
        context = self.prepare_context(processed_data)
        
        # Generate and return response
        return self.generate_response(user_question, context)
    
    def get_document_stats(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about processed documents for chatbot context."""
        if not processed_data:
            return {}
        
        stats = {
            "total_documents": len(processed_data),
            "form_types": {},
            "total_text_length": 0,
            "latest_document": None,
            "oldest_document": None
        }
        
        # Calculate statistics
        for doc in processed_data:
            form_type = doc['ocr_result']['form_type']
            stats["form_types"][form_type] = stats["form_types"].get(form_type, 0) + 1
            stats["total_text_length"] += len(doc['ocr_result']['text'])
            
            # Track latest and oldest
            if not stats["latest_document"] or doc['timestamp'] > stats["latest_document"]['timestamp']:
                stats["latest_document"] = doc
            if not stats["oldest_document"] or doc['timestamp'] < stats["oldest_document"]['timestamp']:
                stats["oldest_document"] = doc
        
        return stats
