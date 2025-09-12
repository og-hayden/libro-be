#!/usr/bin/env python3
"""
Import Messianic Prophecies from JSON to Database

Converts the generated messianic_prophecies.json file to database records.
Handles reference conversion from book/chapter/verse to verse IDs.
"""

import json
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, MessianicProphecy, ProphecyCategory, Verse, Chapter, Book
from app import app

load_dotenv()

JSON_INPUT_FILE = "messianic_prophecies.json"

def get_verse_id(connection, book_name: str, chapter: int, verse: int) -> int:
    """Get verse ID from book/chapter/verse reference"""
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
    
    if result is None:
        raise ValueError(f"Verse not found: {book_name} {chapter}:{verse}")
    
    return result[0]

def convert_fulfillment_references_to_verse_ids(connection, fulfillment_refs):
    """Convert fulfillment references to include verse IDs"""
    converted_refs = []
    for ref in fulfillment_refs:
        try:
            verse_start_id = get_verse_id(connection, ref['book_name'], ref['chapter'], ref['verse_start'])
            verse_end_id = get_verse_id(connection, ref['book_name'], ref['chapter'], ref['verse_end'])
            
            converted_ref = {
                'book_name': ref['book_name'],
                'chapter': ref['chapter'],
                'verse_start': ref['verse_start'],
                'verse_end': ref['verse_end'],
                'verse_start_id': verse_start_id,
                'verse_end_id': verse_end_id,
                'fulfillment_type': ref['fulfillment_type']
            }
            converted_refs.append(converted_ref)
        except ValueError as e:
            print(f"Warning: Skipping fulfillment reference due to error: {e}")
    
    return converted_refs

def import_prophecy(connection, prophecy_data):
    """Import a single prophecy into the database"""
    try:
        # Get verse IDs for prophecy reference
        prophecy_start_id = get_verse_id(
            connection,
            prophecy_data['prophecy_reference']['book_name'],
            prophecy_data['prophecy_reference']['chapter'],
            prophecy_data['prophecy_reference']['verse_start']
        )
        
        prophecy_end_id = get_verse_id(
            connection,
            prophecy_data['prophecy_reference']['book_name'],
            prophecy_data['prophecy_reference']['chapter'],
            prophecy_data['prophecy_reference']['verse_end']
        )
        
        # Convert fulfillment references
        fulfillment_refs = convert_fulfillment_references_to_verse_ids(
            connection, 
            prophecy_data['fulfillment_references']
        )
        
        # Parse created_at timestamp
        created_at = None
        if prophecy_data.get('created_at'):
            created_at = datetime.fromisoformat(prophecy_data['created_at'].replace('Z', '+00:00'))
        
        # Create database record
        prophecy = MessianicProphecy(
            claim=prophecy_data['claim'],
            category=ProphecyCategory(prophecy_data['category']),
            prophecy_verse_start=prophecy_start_id,
            prophecy_verse_end=prophecy_end_id,
            fulfillment_references=fulfillment_refs,
            fulfillment_explanation=prophecy_data['fulfillment_explanation'],
            generated_from_book=prophecy_data.get('generated_from_book'),
            created_at=created_at or datetime.now(timezone.utc)
        )
        
        return prophecy
        
    except ValueError as e:
        print(f"Error importing prophecy '{prophecy_data['claim'][:50]}...': {e}")
        return None
    except Exception as e:
        print(f"Unexpected error importing prophecy '{prophecy_data['claim'][:50]}...': {e}")
        return None

def main():
    """Main import execution"""
    print("Starting Messianic Prophecy Import...")
    print(f"Input file: {JSON_INPUT_FILE}")
    
    # Check if JSON file exists
    if not os.path.exists(JSON_INPUT_FILE):
        print(f"Error: {JSON_INPUT_FILE} not found!")
        return
    
    # Load JSON data
    with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f:
        prophecies_data = json.load(f)
    
    print(f"Loaded {len(prophecies_data)} prophecies from JSON")
    
    # Initialize database connection using Flask app context
    with app.app_context():
        # Clear existing prophecies (optional - remove if you want to keep existing data)
        print("Clearing existing messianic prophecies...")
        db.session.query(MessianicProphecy).delete()
        db.session.commit()
        
        # Use database engine connection for reference lookups
        with db.engine.connect() as connection:
            # Import prophecies
            imported_count = 0
            skipped_count = 0
            
            for i, prophecy_data in enumerate(prophecies_data):
                print(f"Processing prophecy {i+1}/{len(prophecies_data)}: {prophecy_data['claim'][:50]}...")
                
                prophecy = import_prophecy(connection, prophecy_data)
                if prophecy:
                    db.session.add(prophecy)
                    imported_count += 1
                    
                    # Commit in batches of 50
                    if imported_count % 50 == 0:
                        db.session.commit()
                        print(f"  Committed batch of 50... Total imported: {imported_count}")
                else:
                    skipped_count += 1
            
            # Final commit
            db.session.commit()
        
        print(f"\n✓ Import Complete!")
        print(f"✓ Imported: {imported_count} prophecies")
        print(f"✓ Skipped: {skipped_count} prophecies")
        print(f"✓ Total in database: {db.session.query(MessianicProphecy).count()}")

if __name__ == "__main__":
    main()
