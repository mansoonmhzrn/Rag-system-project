import json
import os
import random

# In a real scenario, you would use the OpenAI API, Anthropic API, or a local model.
# For demonstration purposes in setting up the pipeline, we are creating a mock 
# generator that creates synthetic queries based on the ground truth text.

def generate_synthetic_queries(chunk, num_queries=2):
    """
    Mocks an LLM generating natural language queries that this chunk would perfectly answer.
    """
    queries = []
    act = chunk.get('act_title', 'Unknown Act')
    section = chunk.get('section_title', '')
    text = chunk.get('text', '')
    
    # Very basic mock generation logic based on the text length and content
    if "imprisonment" in text.lower():
        queries.append(f"What is the maximum prison sentence under the {act} for {section.lower()}?")
    if "guilty" in text.lower():
         queries.append(f"Under what circumstances is someone guilty of {section.lower()} according to the {act}?")
         
    # Fallback generic query
    if not queries:
        queries.append(f"What does the {act} say about {section.lower()}?")

    # Add a more conversational/vague query
    queries.append(f"Explain the rules around {section.lower()} in UK law.")
    
    # Return up to num_queries
    return queries[:num_queries]

def build_golden_dataset(parsed_chunks_path: str, output_path: str):
    """
    Reads parsed statute chunks and generates a Golden Dataset of (Query, Ground_Truth_ID).
    """
    with open(parsed_chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    dataset = []
    
    print(f"Generating synthetic queries for {len(chunks)} chunks...")
    
    for chunk in chunks:
        # Skip chunks that are too short to hold meaningful legal substance
        if len(chunk.get('text', '')) < 50:
            continue
            
        queries = generate_synthetic_queries(chunk)
        
        for q in queries:
            dataset.append({
                "query_id": f"q_{len(dataset)}",
                "query": q,
                "ground_truth_chunk_id": chunk["id"],
                "metadata": {
                    "act": chunk["act_title"],
                    "section": chunk["section_title"]
                }
            })
            
    # Save the dataset
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Successfully generated Evaluation Dataset with {len(dataset)} queries.")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    input_file = "data/parsed/ukpga_2006_35_chunks.json"
    output_file = "data/benchmark/golden_dataset.json"
    
    if os.path.exists(input_file):
        build_golden_dataset(input_file, output_file)
    else:
        print(f"Error: {input_file} not found. Please run the parser first.")
