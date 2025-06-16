import base64
import json
from mistralai import Mistral
from PIL import Image
import streamlit as st
from typing import Optional, Dict, Any
try:
    from .form_utils import FormUtils
except ImportError:
    from modules.form_utils import FormUtils

class OCRProcessor:
    """Handles OCR processing using Mistral AI API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Mistral(api_key=api_key)
        self.form_utils = FormUtils()
    
    def encode_image(self, image_file) -> Optional[str]:
        """Encode the uploaded image to base64."""
        try:
            return base64.b64encode(image_file.getvalue()).decode('utf-8')
        except Exception as e:
            st.error(f"Error encoding image: {e}")
            return None
    
    def identify_form_type(self, text: str, filename: str = "") -> str:
        """Identify the type of form based on its content and filename."""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Special case for empty or minimal text with image references
        if len(text_lower.strip()) < 20 or "![img-" in text_lower:
            # Check filename for clues
            if any(term in filename_lower for term in ["med", "health", "patient", "doctor", "rx", "script", "scripus", "prior"]):
                return "medical"
            elif any(term in filename_lower for term in ["ins", "claim", "policy"]):
                return "insurance"
            elif any(term in filename_lower for term in ["edu", "school", "college"]):
                return "college"
            elif any(term in filename_lower for term in ["work", "job", "employ"]):
                return "employment"
            elif any(term in filename_lower for term in ["tax", "irs"]):
                return "tax"
        
        # Updated keywords for more accurate form type detection
        form_types = {
            "medical": [
                "medical", "patient", "diagnosis", "health", "doctor", "hospital", "treatment", 
                "prescription", "pharmacy", "medication", "authorization", "scripius", "provider", 
                "prior authorization", "dosage", "xolair", "birth", "physician", "clinic", 
                "consultation", "healthcare", "referral", "medical record", "symptoms"
            ],
            "insurance": [
                "insurance", "policy", "coverage", "claim", "premium", "insurer", "policyholder", 
                "beneficiary", "deductible", "underwriter", "co-pay", "claim number", "provider ID", 
                "authorization number", "network"
            ],
            "college": [
                "college", "university", "school", "education", "student", "admission", "academic", 
                "course", "degree", "gpa", "transcript", "semester", "department", "roll number", 
                "institute", "faculty", "certificate", "marksheet"
            ],
            "employment": [
                "employment", "job", "work", "salary", "employer", "employee", "position", "resume", 
                "hiring", "application", "hr", "interview", "designation", "joining", "pay slip", 
                "offer letter", "experience", "department", "employee ID"
            ],
            "tax": [
                "tax", "income", "return", "deduction", "credit", "taxpayer", "irs", "filing", 
                "refund", "asset", "liability", "form 16", "tds", "gst", "assessment", "pan", 
                "gross income", "taxable", "section"
            ],
            "financial": [
                "financial", "bank", "loan", "credit", "payment", "account", "finance", "mortgage", 
                "investment", "statement", "transfer", "cheque", "ifsc", "account number", 
                "routing", "transaction", "deposit", "withdrawal", "branch", "balance", "passbook",
                "rupees", "amount", "total", "depositor"
            ],
            "government": [
                "government", "official", "certificate", "id", "passport", "license", "registration", 
                "aadhaar", "voter", "rto", "issued by", "department", "authority", "seal", "stamp", 
                "dob", "national"
            ],
            "invoice": [
                "invoice", "receipt", "bill", "amount", "total", "paid", "due", "balance", 
                "invoice number", "billing", "tax", "gst", "item", "vendor", "client", "quantity", 
                "rate", "net", "subtotal"
            ]
        }
        
        # Check for keywords in the text
        form_matches = {}
        for form_type, keywords in form_types.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                form_matches[form_type] = matches
        
        # Determine the most likely form type
        if form_matches:
            most_likely_type = max(form_matches.items(), key=lambda x: x[1])[0]
            return most_likely_type
        
        return "general"
    
    def process_with_mistral_ocr(self, base64_image: str, file_extension: str) -> Optional[Any]:
        """Process image with Mistral OCR API."""
        try:
            # Prepare the message for OCR with improved prompt
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract all text from this image with high accuracy. Pay special attention to:
1. Distinguishing between field labels and field values (e.g., 'Depositor's Name' vs the actual name)
2. Properly identifying currency amounts vs names (e.g., 'Rupees' should not be part of a person's name)
3. Separating different sections of the form clearly
4. Maintaining the logical structure and hierarchy of the document
5. Identifying what text belongs to which field or section

For financial documents, be especially careful to:
- Separate currency indicators (Rs., Rupees, $) from actual names
- Distinguish between amount fields and name/address fields
- Preserve the original field structure

Provide the text content in a clear, structured format that preserves the form's organization."""
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/{file_extension};base64,{base64_image}"
                        }
                    ]
                }
            ]
            
            # Make the API call
            response = self.client.chat.complete(
                model="pixtral-12b-2409",
                messages=messages,
                max_tokens=2000,
                temperature=0.1
            )
            
            return response
            
        except Exception as e:
            st.error(f"OCR processing error: {str(e)}")
            return None
    
    def extract_text_from_response(self, ocr_result: Any) -> str:
        """Extract text content from OCR response."""
        try:
            # Handle different response formats
            if hasattr(ocr_result, 'choices') and ocr_result.choices:
                return ocr_result.choices[0].message.content
            elif hasattr(ocr_result, 'text'):
                return ocr_result.text
            else:
                return str(ocr_result)
        except Exception as e:
            st.error(f"Error extracting text from OCR response: {e}")
            return ""
    
    def post_process_financial_text(self, text: str) -> str:
        """Post-process financial document text to fix common misinterpretations."""
        import re
        
        # Fix common misinterpretations in financial documents
        processed_text = text
        
        # Pattern to fix "Rupees" being included in depositor name
        # Look for patterns like "Depositor's Name / डिपॉज़िटर का नाम: Rupees / रुपये:"
        depositor_pattern = r"(Depositor'?s?\s*Name\s*[/]\s*[^\:]*\s*:\s*)(Rupees?\s*[/]\s*[^\:]*\s*:)"
        match = re.search(depositor_pattern, processed_text, re.IGNORECASE)
        if match:
            # Replace the incorrect part
            processed_text = processed_text.replace(match.group(0), match.group(1))
            # Add the Rupees part to a separate line
            processed_text += f"\n{match.group(2)}"
        
        # Fix amount patterns that might be misplaced
        # Pattern for "Total Rs. / कुल रु: Amount"
        amount_pattern = r"(Total\s+Rs\.\s*[/]\s*[^\:]*\s*:\s*)([A-Za-z\s]+)"
        processed_text = re.sub(amount_pattern, r"\1", processed_text, flags=re.IGNORECASE)
        
        # Separate currency indicators from names
        processed_text = re.sub(r"(Depositor'?s?\s*Name[^:]*:)\s*(Rupees?)", r"\1\n\2", processed_text, flags=re.IGNORECASE)
        
        return processed_text
    
    def convert_to_json(self, ocr_result: Any, ocr_text: str, form_type: str) -> Dict[str, Any]:
        """Convert OCR result to structured JSON."""
        json_data = {
            "document_type": form_type,
            "full_text": ocr_text,
            "model_used": "pixtral-12b-2409",
            "text": ocr_text,
            "processing_timestamp": self.form_utils.get_timestamp(),
            "attributes": {}
        }
        
        # Extract attributes from OCR result
        try:
            for attr in dir(ocr_result):
                if not attr.startswith('_') and not callable(getattr(ocr_result, attr, None)):
                    try:
                        value = getattr(ocr_result, attr)
                        json_data["attributes"][attr] = str(value)
                    except Exception:
                        continue
        except Exception:
            pass
        
        return json_data
    
    def process_image(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """Main method to process an uploaded image file."""
        try:
            # Encode image
            base64_img = self.encode_image(uploaded_file)
            if not base64_img:
                return None
            
            # Get file extension
            ext = uploaded_file.name.split(".")[-1].lower()
            if ext == "jpg":
                ext = "jpeg"
            
            # Process with OCR
            ocr_result = self.process_with_mistral_ocr(base64_img, ext)
            if not ocr_result:
                return None
            
            # Extract text
            ocr_text = self.extract_text_from_response(ocr_result)
            if not ocr_text:
                st.warning("No text could be extracted from the image.")
                return None
            
            # Identify form type
            form_type = self.identify_form_type(ocr_text, uploaded_file.name)
            
            # Post-process financial documents to fix common issues
            if form_type == "financial":
                ocr_text = self.post_process_financial_text(ocr_text)
            
            # Convert to structured format
            json_data = self.convert_to_json(ocr_result, ocr_text, form_type)
            
            return {
                'text': ocr_text,
                'form_type': form_type,
                'json_data': json_data,
                'raw_response': ocr_result
            }
            
        except Exception as e:
            st.error(f"Image processing failed: {str(e)}")
            return None
