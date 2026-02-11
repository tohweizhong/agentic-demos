#!/usr/bin/env python3
"""
Fast Assistant Q&A System
Uses StreamAssist logic but returns only the final answer for speed
"""

from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions
import re

def ask_fast(question: str) -> str:
    """
    Ask a question and get the final answer quickly using Assistant API
    
    Args:
        question: Your question like "What's the date of birth of Alice?"
        
    Returns:
        Direct final answer without streaming steps
    """
    # Configuration from stream_assist.py
    project_id = "weizhong-project01"
    location = "global"
    engine_id = 'enterprise-search-17484208_1748420861365'
    
    # Create AssistantService client (not SearchService)
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine_v1.AssistantServiceClient(client_options=client_options)
    
    print(f"🤔 Question: {question}")
    print("🔍 Querying assistant...")
    
    try:
        # Create the request using AssistantService (same as stream_assist.py)
        request = discoveryengine_v1.StreamAssistRequest(
            name=f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant",
            query=discoveryengine_v1.types.Query(text=question),
        )
        
        # Get the stream response
        stream = client.stream_assist(request=request)
        
        # Collect all responses and extract only the final answer
        final_answer_parts = []
        final_response = None
        
        for response in stream:
            final_response = response
            # Look for the actual content (not thought process)
            if hasattr(response, 'answer'):
                for reply in response.answer.replies:
                    if hasattr(reply, 'grounded_content') and reply.grounded_content:
                        # Check for direct content
                        if hasattr(reply.grounded_content, 'content') and reply.grounded_content.content:
                            if not getattr(reply.grounded_content.content, 'thought', False):
                                if hasattr(reply.grounded_content.content, 'text'):
                                    content_text = reply.grounded_content.content.text.strip()
                                    # Skip thinking markers and search indicators
                                    if (content_text and 
                                        not content_text.startswith('**') and 
                                        not content_text.startswith('Searching for') and
                                        len(content_text) > 10 and
                                        not 'thought' in str(reply.grounded_content.content)):
                                        final_answer_parts.append(content_text)
        
        # Process collected answer parts
        if final_answer_parts:
            # Join the parts and clean up
            final_answer = ' '.join(final_answer_parts)
            final_answer = re.sub(r'\*\*[^*]+\*\*\s*', '', final_answer)
            final_answer = final_answer.strip()
            
            # If this looks like a complete answer, return it
            if len(final_answer) > 10:
                return final_answer
        
        # Fallback: try to extract from the final response structure
        if final_response and hasattr(final_response, 'answer'):
            answer_obj = final_response.answer
            if hasattr(answer_obj, 'replies'):
                for reply in answer_obj.replies:
                    if hasattr(reply, 'grounded_content'):
                        # Look for text grounding metadata which often contains the clean answer
                        if hasattr(reply.grounded_content, 'text_grounding_metadata'):
                            metadata = reply.grounded_content.text_grounding_metadata
                            if hasattr(metadata, 'segments'):
                                # Extract text segments to build the answer
                                segments_text = []
                                for segment in metadata.segments:
                                    if hasattr(segment, 'text'):
                                        segments_text.append(segment.text)
                                if segments_text:
                                    return ' '.join(segments_text)
        
        return "I couldn't extract a clear final answer from the assistant response."
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# def ask_data_store_question() -> str:
#     """Quick function specifically for Alice's birth date"""
#     return ask_fast("Jam berapa Bank Jakarta beroperasi?")

def main():
    """Test the fast assistant Q&A"""
    
    print("=== Fast Assistant Q&A System ===")
    print("Using the powerful AssistantService for direct answers\n")
    
    # Test questions
    test_questions = [
        "What documents do I need to complete my onboarding at Fried Rice?",
        "How do I apply for annual leave?", 
        " Where can I find details about the Fried Rice's health insurance and other benefits?",
        " Does Fried Rice offer training or professional development opportunities?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}:")
        print("-" * 50)
        answer = ask_fast(question)
        print(f"Answer: {answer}")
        print()
    
    print("="*50)
    print("✅ Fast Assistant ready!")
    print("Use ask_fast('your question') for quick answers")

if __name__ == "__main__":
    main()