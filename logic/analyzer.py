import json
import os
import re
import requests
import nltk

# Download necessary data for splitting sentences
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab') # Add this line
    nltk.download('punkt')

# Load your 18,000+ line dictionary
rules_path = os.path.join("data", "asd_rules.json")
ste_data = {}
if os.path.exists(rules_path):
    with open(rules_path, "r") as f:
        ste_data = json.load(f)

def get_batch_corrections(error_list):
    if not error_list:
        return []
    
    formatted_input = "\n".join([f"{i+1}. {item['original']}" for i, item in enumerate(error_list)])
    
    # We add a very strict instruction here
    prompt = f"""
    [INST] You are an ASD-STE100 implementation tool. 
    Rewrite the following sentences into Simplified Technical English.

    STRICT RULES:
    1. Output ONLY the rewritten sentences.
    2. Do NOT include any introductory text like "Here are the sentences" or "Sure, I can help".
    3. Maintain the numbering (1., 2., 3.).
    4. One sentence per line.

    SENTENCES TO REWRITE:
    {formatted_input}
    [/INST]
    """
    
    print(f"--- Processing {len(error_list)} sentences... ---")
    
    try:
        response = requests.post("http://localhost:11434/api/generate", 
                                 json={"model": "llama3", "prompt": prompt, "stream": False}, 
                                 timeout=120)
        
        raw_response = response.json().get("response", "").strip()
        
        # Split into lines and filter out any line that doesn't look like a result
        # This regex removes the "1. " from the start of the line
        replies = []
        for line in raw_response.split('\n'):
            cleaned = re.sub(r'^\d+\.\s*', '', line).strip()
            if cleaned and len(cleaned) > 5: # Ignore short chatter or empty lines
                replies.append(cleaned)
        
        # If the AI added a "Here is the result" line at the very top, remove it
        if "here" in replies[0].lower() and "sentence" in replies[0].lower():
            replies.pop(0)

        # Pad or trim to match input length
        while len(replies) < len(error_list):
            replies.append("AI could not generate a valid STE rewrite.")
            
        return replies[:len(error_list)]
        
    except Exception as e:
        print(f"AI Error: {e}")
        return ["Correction unavailable"] * len(error_list)

def analyze_document(extracted_blocks):
    all_sentences_with_errors = []
    
    # 1. Identify all errors first (Fast)
    for block in extracted_blocks:
        sentences = nltk.sent_tokenize(block["text"])
        for sent_text in sentences:
            suggestions = []
            words = re.findall(r'\w+', sent_text)
            
            # 1. Length Check
            if len(words) > 20:
                suggestions.append("Sentence too long")
            
            # 2. Passive Voice Check (Simplified)
            passive_patterns = [r'\bis\b.*\b\w+ed\b', r'\bare\b.*\b\w+ed\b', r'\bbe\b.*\b\w+ed\b']
            if any(re.search(p, sent_text, re.IGNORECASE) for p in passive_patterns):
                suggestions.append("Passive voice detected")

            # 3. Dictionary Check
            for word in words:
                word_lower = word.lower()
                if word_lower in ste_data:
                    entry = ste_data[word_lower]
                    if not entry.get("is_approved", False):
                        suggestions.append(f"Unapproved word: {word}")

            if suggestions:
                all_sentences_with_errors.append({
                    "original": sent_text,
                    "page": block["page"],
                    "suggestions": list(set(suggestions))
                })
                
    # 2. Process AI corrections in small chunks of 5 (Prevents mismatching and AI chatter)
    all_final_results = []
    
    for i in range(0, len(all_sentences_with_errors), 5):
        chunk = all_sentences_with_errors[i : i + 5]
        print(f"Processing chunk {i//5 + 1}...")
        
        corrections = get_batch_corrections(chunk)
        
        # 3. Merge corrections back into the chunk results
        for j, item in enumerate(chunk):
            # Check if we have a matching correction from the AI
            if j < len(corrections):
                item["correction"] = corrections[j]
            else:
                item["correction"] = "AI could not generate a rewrite for this sentence."
            
            all_final_results.append(item)
                
    return all_final_results