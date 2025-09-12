#!/usr/bin/env python3
"""
Messianic Prophecy Generation Script

Generates JSON data for messianic prophecies by processing Bible books through LLM.
Uses existing JSON file as running dataset to avoid duplicates and allow resumable processing.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_client import gemini_client, ProphecyCategory, FulfillmentType, BookPropheciesGenerated
from models import db, Book, Chapter, Verse

load_dotenv()

# Configuration
JSON_OUTPUT_FILE = "messianic_prophecies.json"
BOOK_PRIORITY = [
    "Isaiah",
    "Psalms", 
    "Daniel",
    "Zechariah",
    "Micah",
    "Jeremiah",
    "Ezekiel",
    "Hosea",
    "Joel", 
    "Amos",
    "Obadiah",
    "Jonah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Malachi",
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy"
]

# Valid book names from database - to provide to LLM
VALID_BOOK_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", 
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", 
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", 
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", 
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", 
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", 
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", 
    "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians", 
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians", 
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", 
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", 
    "3 John", "Jude", "Revelation"
]

def load_existing_prophecies() -> List[Dict[str, Any]]:
    """Load existing prophecies from JSON file"""
    if os.path.exists(JSON_OUTPUT_FILE):
        with open(JSON_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_prophecies(prophecies: List[Dict[str, Any]]) -> None:
    """Save prophecies to JSON file"""
    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prophecies, f, indent=2, ensure_ascii=False)

def validate_verse_reference(connection, book_name: str, chapter: int, verse: int) -> bool:
    """Validate that a verse reference exists in the database"""
    try:
        # Query database to check if verse exists
        query = text("""
            SELECT v.id FROM verses v
            JOIN chapters c ON v.chapter_id = c.id
            JOIN books b ON c.book_id = b.id
            WHERE b.name = :book_name 
            AND c.chapter_number = :chapter 
            AND v.verse_number = :verse
        """)
        
        result = connection.execute(query, {
            'book_name': book_name,
            'chapter': chapter, 
            'verse': verse
        }).fetchone()
        
        return result is not None
    except Exception as e:
        print(f"Error validating reference {book_name} {chapter}:{verse}: {e}")
        return False

def validate_prophecy(connection, prophecy: Dict[str, Any]) -> bool:
    """Validate a prophecy object"""
    required_fields = ['claim', 'category', 'prophecy_reference', 'fulfillment_references', 'fulfillment_explanation']
    
    # Check required fields
    for field in required_fields:
        if field not in prophecy:
            print(f"Missing required field: {field}")
            return False
    
    # Validate category enum
    if prophecy['category'] not in [cat.value for cat in ProphecyCategory]:
        print(f"Invalid category: {prophecy['category']}")
        return False
    
    # Validate prophecy reference
    prop_ref = prophecy['prophecy_reference']
    if not validate_verse_reference(connection, prop_ref['book_name'], prop_ref['chapter'], prop_ref['verse_start']):
        print(f"Invalid prophecy reference: {prop_ref['book_name']} {prop_ref['chapter']}:{prop_ref['verse_start']}")
        return False
    
    if prop_ref['verse_end'] != prop_ref['verse_start']:
        if not validate_verse_reference(connection, prop_ref['book_name'], prop_ref['chapter'], prop_ref['verse_end']):
            print(f"Invalid prophecy reference end: {prop_ref['book_name']} {prop_ref['chapter']}:{prop_ref['verse_end']}")
            return False
    
    # Validate fulfillment references
    for fulfill_ref in prophecy['fulfillment_references']:
        if fulfill_ref['fulfillment_type'] not in [ft.value for ft in FulfillmentType]:
            print(f"Invalid fulfillment type: {fulfill_ref['fulfillment_type']}")
            return False
        
        if not validate_verse_reference(connection, fulfill_ref['book_name'], fulfill_ref['chapter'], fulfill_ref['verse_start']):
            print(f"Invalid fulfillment reference: {fulfill_ref['book_name']} {fulfill_ref['chapter']}:{fulfill_ref['verse_start']}")
            return False
    
    return True

def is_duplicate_prophecy(new_prophecy: Dict[str, Any], existing_prophecies: List[Dict[str, Any]]) -> bool:
    """Check if prophecy already exists"""
    new_prop_ref = new_prophecy['prophecy_reference']
    new_ref_key = f"{new_prop_ref['book_name']}_{new_prop_ref['chapter']}_{new_prop_ref['verse_start']}_{new_prop_ref['verse_end']}"
    
    for existing in existing_prophecies:
        existing_ref = existing['prophecy_reference']
        existing_ref_key = f"{existing_ref['book_name']}_{existing_ref['chapter']}_{existing_ref['verse_start']}_{existing_ref['verse_end']}"
        
        # Check if same verse reference and similar claim
        if new_ref_key == existing_ref_key:
            # Additional check: similar claim (basic similarity)
            if new_prophecy['claim'].lower()[:50] == existing['claim'].lower()[:50]:
                return True
    
    return False

def generate_prophecies_for_book(book_name: str, existing_prophecies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate prophecies for a specific book using LLM"""
    
    # Filter existing prophecies for this book
    book_prophecies = [p for p in existing_prophecies if p['prophecy_reference']['book_name'] == book_name]
    
    # Create system prompt
    system_prompt = f"""
You are a Christian biblical scholar (Presbyterian background) specializing in messianic prophecy identification. 

Your task is to identify messianic prophecies in the book of {book_name} that predict aspects of the coming Messiah.

The goal of this is to create a comprehensive list of messianic prophecies for the Messiah, Jesus Christ. 

STRICT REQUIREMENTS:
1. Only identify clear messianic prophecies - passages that predict or foreshadow the coming Messiah
2. Use EXACT book names from this list: {', '.join(VALID_BOOK_NAMES)}
3. Use only these category values: {', '.join([cat.value for cat in ProphecyCategory])}
4. Use only these fulfillment_type values: {', '.join([ft.value for ft in FulfillmentType])}
5. Provide verse ranges using verse_start and verse_end (same number for single verses)
6. Include 2-4 sentence fulfillment_explanation showing how NT fulfills the prophecy
7. Do not explicitly mention being Presbyterian or Protestant - assume general Christian background for reader

AVOID DUPLICATES: These prophecies already exist for {book_name}:
{json.dumps([{'claim': p['claim'][:100], 'reference': f"{p['prophecy_reference']['book_name']} {p['prophecy_reference']['chapter']}:{p['prophecy_reference']['verse_start']}"} for p in book_prophecies], indent=2)}

Focus on different passages or aspects not already covered.
"""

    user_prompt = f"""
Analyze the book of {book_name} and identify messianic prophecies. For each prophecy:

1. Write a clear, specific claim about what the prophecy predicts regarding the Messiah
2. Categorize it appropriately
3. Identify the exact verse reference(s) where the prophecy appears
4. Find New Testament verse(s) that fulfill this prophecy
5. Explain in 2-4 sentences how the fulfillment connects to the prophecy

Output as JSON matching the BookPropheciesGenerated schema.
"""

    try:
        response = gemini_client.client.models.generate_content(
            model="gemini-2.5-pro",
            contents=user_prompt,
            config={
                'system_instruction': system_prompt,
                'response_mime_type': 'application/json',
                'response_schema': BookPropheciesGenerated
            }
        )
        
        result = response.parsed
        return [prophecy.model_dump() for prophecy in result.prophecies]
        
    except Exception as e:
        print(f"Error generating prophecies for {book_name}: {e}")
        return []

def main():
    """Main script execution"""
    print("Starting Messianic Prophecy Generation...")
    print(f"Output file: {JSON_OUTPUT_FILE}")
    
    # Initialize database connection
    DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        
        # Load existing prophecies
        existing_prophecies = load_existing_prophecies()
        print(f"Loaded {len(existing_prophecies)} existing prophecies")
        
        # Process each book
        for book_name in BOOK_PRIORITY:
            print(f"\n--- Processing {book_name} ---")
            
            # Generate new prophecies for this book
            new_prophecies = generate_prophecies_for_book(book_name, existing_prophecies)
            print(f"LLM generated {len(new_prophecies)} prophecies")
            
            # Validate and add new prophecies
            added_count = 0
            for prophecy in new_prophecies:
                prophecy['generated_from_book'] = book_name
                prophecy['created_at'] = datetime.now(timezone.utc).isoformat()
                
                if validate_prophecy(connection, prophecy) and not is_duplicate_prophecy(prophecy, existing_prophecies):
                    existing_prophecies.append(prophecy)
                    added_count += 1
                else:
                    print(f"Skipped invalid/duplicate prophecy: {prophecy.get('claim', 'Unknown')[:50]}")
            
            # Save progress after each book
            save_prophecies(existing_prophecies)
            print(f"Added {added_count} valid prophecies. Total: {len(existing_prophecies)}")
    
    print(f"\n✓ Complete! Generated {len(existing_prophecies)} total prophecies")
    print(f"✓ Saved to {JSON_OUTPUT_FILE}")

if __name__ == "__main__":
    main()
