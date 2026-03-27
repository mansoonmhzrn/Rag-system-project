import os
import json
from bs4 import BeautifulSoup

def parse_ukpga_xml(xml_path: str):
    """
    Parses a UK Public General Act XML file and extracts hierarchical chunks.
    Chunks are generated at the Section level (<P1> inside <P1group>).
    """
    with open(xml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml-xml')
        
    # Extract Metadata
    act_title = "Unknown Act"
    title_tag = soup.find('dc:title')
    if title_tag:
        act_title = title_tag.text.strip()
        
    year = soup.find('ukm:Year')
    year = year['Value'] if year else "Unknown"
    
    number = soup.find('ukm:Number')
    number = number['Value'] if number else "Unknown"

    chunks = []
    
    # Iterate through all P1groups (Sections)
    p1groups = soup.find_all('P1group')
    
    for i, group in enumerate(p1groups):
        # Get Section Title
        section_title_tag = group.find('Title')
        section_title = section_title_tag.text.strip() if section_title_tag else ""
        
        # Determine the parent Pblock (Part/Crossheading) if it exists
        parent_pblock = group.find_parent('Pblock')
        part_title = ""
        if parent_pblock:
            part_title_tag = parent_pblock.find('Title')
            part_title = part_title_tag.text.strip() if part_title_tag else ""
        
        # Find the actual P1 element (the section body)
        p1_tag = group.find('P1')
        if not p1_tag:
            continue
            
        section_number_tag = p1_tag.find('Pnumber')
        section_number = section_number_tag.text.strip() if section_number_tag else ""
        
        # Extract the text content from P1para
        p1para = p1_tag.find('P1para')
        if p1para:
            # We can just get all text within the section
            # A more advanced chunker might split by <P2> (subsections)
            text_content = p1para.get_text(separator=' ', strip=True)
            
            # Clean up excessive spaces
            text_content = ' '.join(text_content.split())
            
            chunk = {
                "act_title": act_title,
                "year": year,
                "act_number": number,
                "part_title": part_title,
                "section_number": section_number,
                "section_title": section_title,
                "text": text_content,
                "id": f"{year}_{number}_{section_number}_{i}"
            }
            chunks.append(chunk)

    return chunks

if __name__ == "__main__":
    import glob
    os.makedirs("data/parsed", exist_ok=True)
    
    xml_files = glob.glob("data/raw/*.xml")
    if not xml_files:
        print("No raw XML files found. Please run fetch_statute.py first.")
    else:
        for xml_file in xml_files:
            print(f"Parsing {xml_file}...")
            chunks = parse_ukpga_xml(xml_file)
            print(f"Extracted {len(chunks)} section chunks.")
            
            # Save parsed chunks per act
            base_name = os.path.basename(xml_file).replace(".xml", "_chunks.json")
            out_path = os.path.join("data/parsed", base_name)
            
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2)
            print(f"Saved {len(chunks)} chunks to {out_path}\n")
