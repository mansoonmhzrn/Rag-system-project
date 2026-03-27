import urllib.request
import urllib.error
import os

def download_act_xml(year: str, act_number: str, output_dir: str = "data/raw"):
    """
    Downloads the XML representation of a UK Public General Act from legislation.gov.uk.
    
    Args:
        year: The year the act was passed (e.g., '2006').
        act_number: The act number for that year (e.g., '35' for Fraud Act 2006).
        output_dir: Directory to save the XML file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # URL format for UK Public General Acts (ukpga)
    url = f"https://www.legislation.gov.uk/ukpga/{year}/{act_number}/data.xml"
    output_path = os.path.join(output_dir, f"ukpga_{year}_{act_number}.xml")
    
    print(f"Fetching data from: {url}")
    try:
        # We need to spoof a User-Agent because legislation.gov.uk might block plain urllib
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Successfully saved to: {output_path}")
        return output_path
    
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason} for URL: {url}")
        return None
    except Exception as e:
        print(f"Failed to download: {e}")
        return None

if __name__ == "__main__":
    # Test cases:
    # 1. Fraud Act 2006 (Year: 2006, Act Number: 35)
    download_act_xml("2006", "35")
    
    # 2. Housing Act 1988 (Year: 1988, Act Number: 50)
    download_act_xml("1988", "50")
    
    # 3. Employment Rights Act 1996 (Year: 1996, Act Number: 18)
    download_act_xml("1996", "18")
