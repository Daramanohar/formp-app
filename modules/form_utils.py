import json
from datetime import datetime
from typing import Any, Dict, List
import streamlit as st

class FormUtils:
    """Utility functions for form processing and data management."""
    
    def __init__(self):
        pass
    
    def get_timestamp(self) -> str:
        """Get current timestamp in a readable format."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported."""
        supported_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        file_extension = filename.split('.')[-1].lower()
        return file_extension in supported_extensions
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove special characters that might cause issues
        text = text.replace('\x00', '')  # Remove null characters
        
        return text.strip()
    
    def extract_key_fields(self, text: str, form_type: str) -> Dict[str, Any]:
        """Extract key fields based on form type."""
        key_fields = {}
        text_lower = text.lower()
        
        if form_type == "medical":
            # Medical form key fields
            patterns = {
                "patient_name": ["patient name", "name:", "patient:"],
                "date_of_birth": ["dob:", "date of birth", "birth date"],
                "diagnosis": ["diagnosis:", "condition:", "icd"],
                "medication": ["medication:", "drug:", "prescription:"],
                "provider": ["provider:", "doctor:", "physician:"]
            }
        elif form_type == "insurance":
            # Insurance form key fields
            patterns = {
                "policy_number": ["policy no", "policy number", "policy #"],
                "insured_name": ["insured:", "policyholder:", "name:"],
                "coverage": ["coverage:", "benefits:", "limits:"],
                "premium": ["premium:", "payment:", "cost:"],
                "claim_number": ["claim no", "claim number", "claim #"]
            }
        elif form_type == "financial":
            # Financial form key fields
            patterns = {
                "account_number": ["account no", "account number", "acct #"],
                "balance": ["balance:", "amount:", "total:"],
                "date": ["date:", "as of:", "statement date"],
                "transaction": ["transaction:", "payment:", "deposit:"]
            }
        else:
            # General patterns
            patterns = {
                "name": ["name:", "full name"],
                "date": ["date:", "dated:"],
                "amount": ["amount:", "total:", "$"],
                "reference": ["ref:", "reference:", "#"]
            }
        
        # Extract fields based on patterns
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in text_lower:
                    # Try to extract the value after the pattern
                    start_idx = text_lower.find(pattern)
                    if start_idx != -1:
                        # Look for the value after the pattern
                        value_start = start_idx + len(pattern)
                        line_end = text.find('\n', value_start)
                        if line_end == -1:
                            line_end = len(text)
                        
                        value = text[value_start:line_end].strip()
                        # Clean up the value
                        value = value.split(':')[-1].strip() if ':' in value else value
                        
                        if value and len(value) > 0:
                            key_fields[field] = value
                            break
        
        return key_fields
    
    def generate_summary_report(self, processed_data: List[Dict[str, Any]]) -> str:
        """Generate a summary report of all processed documents."""
        if not processed_data:
            return "No documents have been processed yet."
        
        report = "📊 PROCESSING SUMMARY REPORT\n"
        report += "=" * 50 + "\n\n"
        
        # Overview
        report += f"📈 Total Documents Processed: {len(processed_data)}\n"
        report += f"🕒 Report Generated: {self.get_timestamp()}\n\n"
        
        # Document types breakdown
        form_types = {}
        for doc in processed_data:
            form_type = doc['ocr_result']['form_type']
            form_types[form_type] = form_types.get(form_type, 0) + 1
        
        report += "📋 Document Types:\n"
        for form_type, count in form_types.items():
            report += f"  • {form_type.title()}: {count} document(s)\n"
        
        report += "\n" + "=" * 50 + "\n\n"
        
        # Individual document summaries
        report += "📄 INDIVIDUAL DOCUMENTS:\n\n"
        for i, doc in enumerate(processed_data, 1):
            report += f"{i}. {doc['filename']}\n"
            report += f"   Type: {doc['ocr_result']['form_type'].title()}\n"
            report += f"   Processed: {doc['timestamp']}\n"
            report += f"   Text Length: {len(doc['ocr_result']['text'])} characters\n"
            
            # Add summary if available
            if 'analysis' in doc and 'summary' in doc['analysis']:
                summary_preview = doc['analysis']['summary'][:100] + "..." if len(doc['analysis']['summary']) > 100 else doc['analysis']['summary']
                report += f"   Summary: {summary_preview}\n"
            
            report += "\n"
        
        report += "=" * 50 + "\n"
        report += "📊 End of Report"
        
        return report
    
    def export_data(self, processed_data: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Export all data in a structured format."""
        export_data = {
            "metadata": {
                "export_timestamp": self.get_timestamp(),
                "total_documents": len(processed_data),
                "total_chat_messages": len(chat_history)
            },
            "documents": [],
            "chat_history": chat_history,
            "summary": {
                "form_types": {},
                "processing_dates": []
            }
        }
        
        # Process documents for export
        for doc in processed_data:
            export_doc = {
                "filename": doc['filename'],
                "timestamp": doc['timestamp'],
                "form_type": doc['ocr_result']['form_type'],
                "extracted_text": doc['ocr_result']['text'],
                "text_length": len(doc['ocr_result']['text']),
                "key_fields": self.extract_key_fields(doc['ocr_result']['text'], doc['ocr_result']['form_type'])
            }
            
            # Add analysis if available
            if 'analysis' in doc:
                export_doc['analysis'] = {
                    "summary": doc['analysis']['summary'],
                    "completeness_score": doc['analysis'].get('completeness_analysis', {}).get('ai_analysis', ''),
                }
            
            export_data["documents"].append(export_doc)
            
            # Update summary
            form_type = doc['ocr_result']['form_type']
            export_data["summary"]["form_types"][form_type] = export_data["summary"]["form_types"].get(form_type, 0) + 1
            export_data["summary"]["processing_dates"].append(doc['timestamp'])
        
        return export_data
    
    def validate_api_keys(self, mistral_key: str, groq_key: str) -> Dict[str, bool]:
        """Validate API keys format (basic validation)."""
        validation = {
            "mistral_valid": bool(mistral_key and len(mistral_key) > 10),
            "groq_valid": bool(groq_key and len(groq_key) > 10),
        }
        validation["both_valid"] = validation["mistral_valid"] and validation["groq_valid"]
        return validation
    
    def get_processing_stats(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get processing statistics for dashboard."""
        if not processed_data:
            return {
                "total_documents": 0,
                "total_characters": 0,
                "form_types": {},
                "avg_text_length": 0,
                "processing_dates": []
            }
        
        stats = {
            "total_documents": len(processed_data),
            "total_characters": sum(len(doc['ocr_result']['text']) for doc in processed_data),
            "form_types": {},
            "processing_dates": []
        }
        
        # Calculate form type distribution
        for doc in processed_data:
            form_type = doc['ocr_result']['form_type']
            stats["form_types"][form_type] = stats["form_types"].get(form_type, 0) + 1
            stats["processing_dates"].append(doc['timestamp'])
        
        # Calculate average text length
        stats["avg_text_length"] = stats["total_characters"] // stats["total_documents"] if stats["total_documents"] > 0 else 0
        
        return stats
