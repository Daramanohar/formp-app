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
            context += f"- Type: {doc['ocr_result'].get('form_type', 'unknown')}\n"
            context += f"- Processed: {doc['timestamp']}\n"
            context += f"- Text Preview: {doc['ocr_result'].get('text', '')[:200]}...\n"

            if 'analysis' in doc and 'summary' in doc['analysis']:
                context += f"- Summary: {doc['analysis']['summary'][:150]}...\n"

            if 'structured_data' in doc:
                context += "- Extracted Key Fields:\n"
                for k, v in doc['structured_data'].items():
                    context += f"   - {k}: {v}\n"

            context += "\n" + "="*50 + "\n\n"

        return context

    def generate_response(self, user_question: str, context: str) -> str:
        """Generate chatbot response based on user question and document context."""
        try:
            system_prompt = """
            You are a helpful AI assistant that provides accurate insights from document processing.

            Your responsibilities:
            - Accurately answer user questions using ONLY the structured data and summaries provided.
            - If the required data isn't in the context, explain that clearly and suggest next steps.
            - Do NOT make up values. Focus on practical business insights from ANY type of form (tax, medical, insurance, college, employment, etc).
            - Be concise, factual, and helpful for team communication and decision-making.
            """

            user_prompt = f"""
            Below is the available context from processed documents:

            {context}

            Now answer this question clearly and factually:

            {user_question}
            """

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"I encountered an error while processing your question: {str(e)}. Please try rephrasing your question or check if the API service is available."

    def suggest_questions(self, processed_data: List[Dict[str, Any]]) -> List[str]:
        """Suggest relevant questions based on processed data."""
        if not processed_data:
            return []

        form_types = [doc['ocr_result'].get('form_type', '') for doc in processed_data]
        unique_types = set(form_types)

        suggestions = [
            "What are the key insights from all processed documents?",
            "Can you summarize the main findings for my team?",
            "What action items should I communicate to stakeholders?",
        ]

        if 'medical' in unique_types:
            suggestions.extend([
                "What are the key diagnoses or treatments mentioned?",
                "Which patient conditions are most critical?"
            ])

        if 'insurance' in unique_types:
            suggestions.extend([
                "What policy or claim details are extracted?",
                "Are there any expired policies or unpaid claims?"
            ])

        if 'financial' in unique_types:
            suggestions.extend([
                "What is the tax amount due or refund expected?",
                "Are there any inconsistencies in income or deductions?"
            ])

        if 'college' in unique_types:
            suggestions.extend([
                "What academic information is extracted?",
                "Are there missing transcripts or GPA fields?"
            ])

        if 'employment' in unique_types:
            suggestions.extend([
                "What job roles or hiring statuses are mentioned?",
                "Is the employment history complete?"
            ])

        if len(processed_data) > 1:
            suggestions.extend([
                "Compare summary fields across documents",
                "What trends do you notice between documents?",
                "Which document has the most important action item?"
            ])

        return suggestions[:10]

    def chat_with_data(self, user_question: str, processed_data: List[Dict[str, Any]]) -> str:
        if not processed_data:
            return "I don't have any processed documents to analyze yet. Please upload and process some documents first."

        context = self.prepare_context(processed_data)
        return self.generate_response(user_question, context)

    def get_document_stats(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not processed_data:
            return {}

        stats = {
            "total_documents": len(processed_data),
            "form_types": {},
            "total_text_length": 0,
            "latest_document": None,
            "oldest_document": None
        }

        for doc in processed_data:
            form_type = doc['ocr_result'].get('form_type', 'unknown')
            stats["form_types"][form_type] = stats["form_types"].get(form_type, 0) + 1
            stats["total_text_length"] += len(doc['ocr_result'].get('text', ''))

            if not stats["latest_document"] or doc['timestamp'] > stats["latest_document"]['timestamp']:
                stats["latest_document"] = doc
            if not stats["oldest_document"] or doc['timestamp'] < stats["oldest_document"]['timestamp']:
                stats["oldest_document"] = doc

        return stats
