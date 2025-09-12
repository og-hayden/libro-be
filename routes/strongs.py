from flask import Blueprint, request, jsonify
from models import StrongsEntry, VerseStrongsMapping, Verse, Chapter, Book, StrongsConcordanceCache, db
from sqlalchemy import or_
from marshmallow import Schema, fields, ValidationError
import re

strongs_bp = Blueprint('strongs', __name__)

class StrongsSearchSchema(Schema):
    query = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    language = fields.Str(required=False, validate=lambda x: x in ['hebrew', 'greek', 'both'])

@strongs_bp.route('/lookup/<strongs_number>', methods=['GET'])
def lookup_strongs_number(strongs_number):
    """Look up a specific Strong's number (e.g., H430, G2316)"""
    # Validate format
    if not re.match(r'^[HG]\d+$', strongs_number):
        return jsonify({'error': 'Invalid Strong\'s number format. Use H#### for Hebrew or G#### for Greek.'}), 400
    
    entry = StrongsEntry.query.filter_by(strongs_number=strongs_number).first()
    if not entry:
        return jsonify({'error': f'Strong\'s number {strongs_number} not found'}), 404
    
    # Get verses that use this Strong's number
    mappings = VerseStrongsMapping.query.filter_by(strongs_number=strongs_number).limit(10).all()
    verse_examples = []
    
    for mapping in mappings:
        verse = mapping.verse
        verse_data = verse.to_dict(include_strongs=True)
        verse_examples.append({
            'verse': verse_data,
            'word_position': mapping.word_position,
            'grammatical_info': mapping.grammatical_info
        })
    
    return jsonify({
        'strongs_entry': entry.to_dict(),
        'verse_examples': verse_examples,
        'total_occurrences': VerseStrongsMapping.query.filter_by(strongs_number=strongs_number).count()
    }), 200

@strongs_bp.route('/search', methods=['GET'])
def search_strongs():
    """Search Strong's entries by definition or transliteration"""
    query = request.args.get('q', '').strip()
    language = request.args.get('language', 'both').lower()
    limit = request.args.get('limit', 20, type=int)
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters long'}), 400
    
    if limit > 100:
        limit = 100
    
    # Build query based on language filter
    base_query = StrongsEntry.query.filter(
        or_(
            StrongsEntry.definition.ilike(f'%{query}%'),
            StrongsEntry.transliteration.ilike(f'%{query}%'),
            StrongsEntry.kjv_usage.ilike(f'%{query}%')
        )
    )
    
    if language == 'hebrew':
        base_query = base_query.filter(StrongsEntry.language == 'Hebrew')
    elif language == 'greek':
        base_query = base_query.filter(StrongsEntry.language == 'Greek')
    
    entries = base_query.limit(limit).all()
    
    return jsonify({
        'query': query,
        'language_filter': language,
        'results': [entry.to_dict() for entry in entries],
        'count': len(entries)
    }), 200

@strongs_bp.route('/concordance/<strongs_number>', methods=['GET'])
def get_concordance(strongs_number):
    """Get all verses that contain a specific Strong's number (concordance view)"""
    # Validate format
    if not re.match(r'^[HG]\d+$', strongs_number):
        return jsonify({'error': 'Invalid Strong\'s number format. Use H#### for Hebrew or G#### for Greek.'}), 400
    
    # Check cache first
    cached_result = StrongsConcordanceCache.query.filter_by(strongs_number=strongs_number).first()
    if cached_result:
        return jsonify(cached_result.result_data), 200
    
    # Get the Strong's entry
    entry = StrongsEntry.query.filter_by(strongs_number=strongs_number).first()
    if not entry:
        return jsonify({'error': f'Strong\'s number {strongs_number} not found'}), 404
    
    # Get all verses with this Strong's number, grouped by book
    mappings = VerseStrongsMapping.query.filter_by(strongs_number=strongs_number)\
        .join(Verse)\
        .join(Chapter)\
        .join(Book)\
        .order_by(Book.id, Chapter.chapter_number, Verse.verse_number)\
        .all()
    
    # Group by book
    book_groups = {}
    total_verses = 0
    
    for mapping in mappings:
        verse = mapping.verse
        book = verse.chapter.book
        
        if book.id not in book_groups:
            book_groups[book.id] = {
                'book': book.to_dict(),
                'verse_count': 0,
                'sample_verses': []
            }
        
        book_groups[book.id]['verse_count'] += 1
        total_verses += 1
        
        # Add first 3 verses as samples
        if len(book_groups[book.id]['sample_verses']) < 3:
            verse_data = verse.to_dict(include_strongs=True)
            verse_data['book'] = book.to_dict()
            verse_data['chapter_info'] = verse.chapter.to_dict()
            book_groups[book.id]['sample_verses'].append(verse_data)
    
    book_groups_list = list(book_groups.values())
    
    result_data = {
        'strongs_entry': entry.to_dict(),
        'book_groups': book_groups_list,
        'total_books': len(book_groups_list),
        'total_verses': total_verses
    }
    
    # Cache the result (handle duplicates properly)
    try:
        cache_entry = StrongsConcordanceCache(
            strongs_number=strongs_number,
            result_data=result_data
        )
        db.session.add(cache_entry)
        db.session.commit()
    except Exception as e:
        # If duplicate key error, just rollback and continue
        db.session.rollback()
        print(f"Cache entry already exists for {strongs_number}, skipping cache update")
    
    return jsonify(result_data), 200

@strongs_bp.route('/concordance/<strongs_number>/book/<book_name>', methods=['GET'])
def get_concordance_by_book(strongs_number, book_name):
    """Get all verses with a Strong's number in a specific book"""
    # Validate format
    if not re.match(r'^[HG]\d+$', strongs_number):
        return jsonify({'error': 'Invalid Strong\'s number format. Use H#### for Hebrew or G#### for Greek.'}), 400
    
    # Get the book
    book = Book.query.filter_by(name=book_name).first()
    if not book:
        return jsonify({'error': f'Book {book_name} not found'}), 404
    
    # Get all verses with this Strong's number in this book, grouped by verse to avoid duplicates
    mappings = VerseStrongsMapping.query.filter_by(strongs_number=strongs_number)\
        .join(Verse)\
        .join(Chapter)\
        .filter(Chapter.book_id == book.id)\
        .order_by(Chapter.chapter_number, Verse.verse_number, VerseStrongsMapping.word_position)\
        .all()
    
    # Group by verse to merge duplicates and collect word positions
    verse_groups = {}
    for mapping in mappings:
        verse = mapping.verse
        if verse.id not in verse_groups:
            verse_groups[verse.id] = {
                'verse': verse,
                'word_positions': []
            }
        verse_groups[verse.id]['word_positions'].append(mapping.word_position)
    
    results = []
    for verse_group in verse_groups.values():
        verse = verse_group['verse']
        verse_data = verse.to_dict(include_strongs=True)
        verse_data['book'] = book.to_dict()
        verse_data['chapter_info'] = verse.chapter.to_dict()
        verse_data['word_positions'] = verse_group['word_positions']  # Add word positions for highlighting
        results.append(verse_data)
    
    return jsonify({
        'results': results
    }), 200

@strongs_bp.route('/verse/<int:verse_id>/strongs', methods=['GET'])
def get_verse_strongs(verse_id):
    """Get all Strong's numbers and their definitions for a specific verse"""
    verse = Verse.query.get(verse_id)
    if not verse:
        return jsonify({'error': 'Verse not found'}), 404
    
    # Get all Strong's mappings for this verse
    mappings = VerseStrongsMapping.query.filter_by(verse_id=verse_id)\
        .order_by(VerseStrongsMapping.word_position).all()
    
    strongs_data = []
    unique_numbers = set()
    
    for mapping in mappings:
        if mapping.strongs_number not in unique_numbers:
            entry = StrongsEntry.query.filter_by(strongs_number=mapping.strongs_number).first()
            if entry:
                strongs_data.append({
                    'mapping': mapping.to_dict(),
                    'definition': entry.to_dict()
                })
                unique_numbers.add(mapping.strongs_number)
    
    return jsonify({
        'verse': verse.to_dict(include_strongs=True),
        'strongs_analysis': strongs_data,
        'total_strongs_numbers': len(unique_numbers)
    }), 200

@strongs_bp.route('/stats', methods=['GET'])
def get_strongs_stats():
    """Get statistics about Strong's concordance data"""
    hebrew_count = StrongsEntry.query.filter_by(language='Hebrew').count()
    greek_count = StrongsEntry.query.filter_by(language='Greek').count()
    total_mappings = VerseStrongsMapping.query.count()
    verses_with_strongs = Verse.query.filter(Verse.strongs_numbers.isnot(None)).count()
    
    return jsonify({
        'hebrew_entries': hebrew_count,
        'greek_entries': greek_count,
        'total_entries': hebrew_count + greek_count,
        'total_word_mappings': total_mappings,
        'verses_with_strongs': verses_with_strongs
    }), 200
