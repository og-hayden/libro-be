from flask import Blueprint, request, jsonify
from models import db, Book, Chapter, Verse, SearchCache, MessianicProphecy
from sqlalchemy import func, or_
import re

bible_bp = Blueprint('bible', __name__)

# Cache for books list - this data never changes
_books_cache = None

@bible_bp.route('/books', methods=['GET'])
def get_books():
    """Get all books of the Bible"""
    global _books_cache
    
    if _books_cache is None:
        books = Book.query.order_by(Book.order_number).all()
        _books_cache = {
            'books': [book.to_dict() for book in books]
        }
    
    return jsonify(_books_cache), 200

@bible_bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a specific book with its chapters"""
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    book_data = book.to_dict()
    book_data['chapters'] = [chapter.to_dict() for chapter in book.chapters]
    
    return jsonify({'book': book_data}), 200

@bible_bp.route('/books/<int:book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    """Get all chapters for a specific book"""
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    chapters = Chapter.query.filter_by(book_id=book_id).order_by(Chapter.chapter_number).all()
    
    return jsonify({
        'book': book.to_dict(),
        'chapters': [chapter.to_dict() for chapter in chapters]
    }), 200

@bible_bp.route('/books/<int:book_id>/chapters/<int:chapter_number>', methods=['GET'])
def get_book_chapter(book_id, chapter_number):
    """Get a specific chapter from a book with its verses"""
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    chapter = Chapter.query.filter_by(book_id=book_id, chapter_number=chapter_number).first()
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404
    
    verses = Verse.query.filter_by(chapter_id=chapter.id).order_by(Verse.verse_number).all()
    
    # Get prophecy data for this chapter
    verse_ids = [v.id for v in verses]
    
    # Find prophecies where this chapter contains the prophecy verse(s)
    prophecy_verses = MessianicProphecy.query.filter(
        or_(
            MessianicProphecy.prophecy_verse_start.in_(verse_ids),
            MessianicProphecy.prophecy_verse_end.in_(verse_ids)
        )
    ).all()
    
    # Find prophecies where this chapter contains fulfillment verse(s)
    fulfillment_prophecies = []
    for verse_id in verse_ids:
        prophecies = db.session.execute(db.text("""
            SELECT * FROM messianic_prophecies mp
            WHERE mp.fulfillment_references::text LIKE :verse_pattern
        """), {'verse_pattern': f'%"verse_start_id": {verse_id}%'}).fetchall()
        
        for prophecy_row in prophecies:
            prophecy = MessianicProphecy.query.get(prophecy_row.id)
            if prophecy not in fulfillment_prophecies:
                fulfillment_prophecies.append(prophecy)
    
    # Build prophecy highlighting data
    prophecy_data = {
        'prophecy_verses': [],  # Verses that are prophecies
        'fulfillment_verses': []  # Verses that are fulfillments
    }
    
    # Process prophecy verses
    for prophecy in prophecy_verses:
        if prophecy.start_verse.chapter_id == chapter.id:
            start_verse_num = prophecy.start_verse.verse_number
            end_verse_num = prophecy.end_verse.verse_number if prophecy.end_verse.chapter_id == chapter.id else start_verse_num
            verse_range = list(range(start_verse_num, end_verse_num + 1))
            
            prophecy_data['prophecy_verses'].append({
                'prophecy_id': prophecy.id,
                'verse_numbers': verse_range,
                'category': prophecy.category.value,
                'claim': prophecy.claim[:100] + '...' if len(prophecy.claim) > 100 else prophecy.claim
            })
    
    # Process fulfillment verses
    for prophecy in fulfillment_prophecies:
        for fulfillment_ref in prophecy.fulfillment_references:
            if fulfillment_ref.get('verse_start_id') in verse_ids:
                verse_range = list(range(
                    fulfillment_ref['verse_start'], 
                    fulfillment_ref['verse_end'] + 1
                ))
                prophecy_data['fulfillment_verses'].append({
                    'prophecy_id': prophecy.id,
                    'verse_numbers': verse_range,
                    'fulfillment_type': fulfillment_ref['fulfillment_type'],
                    'original_prophecy': f"{prophecy.start_verse.chapter.book.name} {prophecy.start_verse.chapter.chapter_number}:{prophecy.start_verse.verse_number}"
                })
    
    # Get all chapters for pagination info
    all_chapters = Chapter.query.filter_by(book_id=book_id).order_by(Chapter.chapter_number).all()
    chapter_numbers = [ch.chapter_number for ch in all_chapters]
    
    # Find current chapter index
    current_index = chapter_numbers.index(chapter_number) if chapter_number in chapter_numbers else 0
    
    # Build pagination info
    pagination_info = {
        'current_chapter': chapter_number,
        'total_chapters': len(chapter_numbers),
        'has_previous': current_index > 0,
        'has_next': current_index < len(chapter_numbers) - 1,
        'previous_chapter': chapter_numbers[current_index - 1] if current_index > 0 else None,
        'next_chapter': chapter_numbers[current_index + 1] if current_index < len(chapter_numbers) - 1 else None,
        'all_chapters': chapter_numbers
    }
    
    return jsonify({
        'book': book.to_dict(),
        'chapter': chapter.to_dict(),
        'verses': [verse.to_dict(include_strongs=True) for verse in verses],
        'pagination': pagination_info,
        'prophecies': prophecy_data
    }), 200

@bible_bp.route('/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(chapter_id):
    """Get a specific chapter with its verses"""
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404
    
    chapter_data = chapter.to_dict()
    chapter_data['verses'] = [verse.to_dict() for verse in chapter.verses]
    chapter_data['book'] = chapter.book.to_dict()
    
    return jsonify({'chapter': chapter_data}), 200

@bible_bp.route('/chapters/<int:chapter_id>/verses', methods=['GET'])
def get_chapter_verses(chapter_id):
    """Get all verses for a specific chapter"""
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404
    
    verses = Verse.query.filter_by(chapter_id=chapter_id).order_by(Verse.verse_number).all()
    
    return jsonify({
        'chapter': chapter.to_dict(),
        'book': chapter.book.to_dict(),
        'verses': [verse.to_dict() for verse in verses]
    }), 200

@bible_bp.route('/verses/<int:verse_id>', methods=['GET'])
def get_verse(verse_id):
    """Get a specific verse"""
    verse = Verse.query.get(verse_id)
    if not verse:
        return jsonify({'error': 'Verse not found'}), 404
    
    verse_data = verse.to_dict()
    verse_data['chapter'] = verse.chapter.to_dict()
    verse_data['book'] = verse.chapter.book.to_dict()
    
    return jsonify({'verse': verse_data}), 200

@bible_bp.route('/verses/range', methods=['GET'])
def get_verse_range():
    """Get a range of verses"""
    start_verse_id = request.args.get('start', type=int)
    end_verse_id = request.args.get('end', type=int)
    
    if not start_verse_id:
        return jsonify({'error': 'start parameter is required'}), 400
    
    if not end_verse_id:
        end_verse_id = start_verse_id
    
    # Validate verse IDs
    start_verse = Verse.query.get(start_verse_id)
    end_verse = Verse.query.get(end_verse_id)
    
    if not start_verse or not end_verse:
        return jsonify({'error': 'One or more verses not found'}), 404
    
    # Get all verses in the range
    verses = Verse.query.filter(
        Verse.id >= start_verse_id,
        Verse.id <= end_verse_id
    ).order_by(Verse.id).all()
    
    # Combine text for the range
    combined_text = ' '.join([verse.text for verse in verses])
    
    # Create reference string
    if start_verse_id == end_verse_id:
        reference = f"{start_verse.chapter.book.name} {start_verse.chapter.chapter_number}:{start_verse.verse_number}"
    else:
        reference = f"{start_verse.chapter.book.name} {start_verse.chapter.chapter_number}:{start_verse.verse_number}-{end_verse.verse_number}"
    
    return jsonify({
        'verses': [verse.to_dict() for verse in verses],
        'combined_text': combined_text,
        'reference': reference,
        'start_verse': start_verse.to_dict(),
        'end_verse': end_verse.to_dict()
    }), 200

@bible_bp.route('/search', methods=['GET'])
def search_verses():
    """Search for verses containing specific text"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    book_filter = request.args.get('book', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    if len(query) < 3:
        return jsonify({'error': 'Query must be at least 3 characters long'}), 400
    
    # Build query with optional book filter
    verse_query = Verse.query.filter(
        Verse.text.ilike(f'%{query}%')
    )
    
    if book_filter:
        verse_query = verse_query.join(Chapter).join(Book).filter(
            Book.name.ilike(f'%{book_filter}%')
        )
    
    # Get total count for pagination
    total_count = verse_query.count()
    
    # Apply pagination
    verses = verse_query.offset(offset).limit(limit).all()
    
    results = []
    for verse in verses:
        verse_data = verse.to_dict()
        verse_data['book'] = verse.chapter.book.to_dict()
        verse_data['chapter_info'] = verse.chapter.to_dict()
        results.append(verse_data)
    
    return jsonify({
        'query': query,
        'results': results,
        'count': len(results),
        'total': total_count,
        'offset': offset,
        'limit': limit
    }), 200

@bible_bp.route('/search/grouped', methods=['GET'])
def search_verses_grouped():
    """Search for verses grouped by book with caching"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    if len(query) < 3:
        return jsonify({'error': 'Query must be at least 3 characters long'}), 400
    
    # Try to get from database cache first
    query_hash = SearchCache.generate_query_hash(query)
    cached_search = db.session.query(SearchCache).filter_by(query_hash=query_hash).first()
    if cached_search:
        return jsonify(cached_search.result_data), 200
    
    # Search verses and group by book
    verses = Verse.query.filter(
        Verse.text.ilike(f'%{query}%')
    ).join(Chapter).join(Book).all()
    
    # Group results by book
    book_groups = {}
    for verse in verses:
        book = verse.chapter.book
        if book.id not in book_groups:
            book_groups[book.id] = {
                'book': book.to_dict(),
                'verse_count': 0,
                'sample_verses': []
            }
        
        book_groups[book.id]['verse_count'] += 1
        
        # Keep first 3 verses as samples
        if len(book_groups[book.id]['sample_verses']) < 3:
            verse_data = verse.to_dict()
            verse_data['chapter_info'] = verse.chapter.to_dict()
            book_groups[book.id]['sample_verses'].append(verse_data)
    
    # Convert to list and sort by verse count (descending)
    grouped_results = list(book_groups.values())
    grouped_results.sort(key=lambda x: x['verse_count'], reverse=True)
    
    total_verses = sum(group['verse_count'] for group in grouped_results)
    
    result = {
        'query': query,
        'book_groups': grouped_results,
        'total_books': len(grouped_results),
        'total_verses': total_verses
    }
    
    # Save the result to database cache permanently
    search_cache = SearchCache(
        query_text=query,
        query_hash=query_hash,
        result_data=result
    )
    db.session.add(search_cache)
    db.session.commit()
    
    return jsonify(result), 200

@bible_bp.route('/books/resolve/<book_slug>', methods=['GET'])
def resolve_book_slug(book_slug):
    """Resolve a book slug (e.g., 'john' or '1-kings') to book ID and metadata"""
    # Convert slug back to potential book name
    potential_name = book_slug.replace('-', ' ').title()
    
    # Try exact match first
    book = Book.query.filter(Book.name.ilike(potential_name)).first()
    
    if not book:
        # Try partial matching for common abbreviations and variations
        books = Book.query.filter(
            or_(
                Book.name.ilike(f'%{potential_name}%'),
                Book.abbreviation.ilike(f'%{potential_name}%'),
                Book.name.ilike(f'{potential_name}%')
            )
        ).all()
        
        if books:
            # Take the first match, preferring exact name matches
            book = books[0]
    
    if not book:
        return jsonify({'error': f'Book not found for slug: {book_slug}'}), 404
    
    return jsonify({
        'book': book.to_dict(),
        'slug': book_slug,
        'resolved_name': book.name
    }), 200

@bible_bp.route('/reference', methods=['GET'])
def get_by_reference():
    """Get verse(s) by reference string (e.g., 'John 3:16' or 'Romans 3:23-24')"""
    ref = request.args.get('ref', '').strip()
    
    if not ref:
        return jsonify({'error': 'Reference parameter ref is required'}), 400
    
    try:
        # Parse reference (basic implementation)
        # Format: "Book Chapter:Verse" or "Book Chapter:Verse-Verse"
        parts = ref.split(' ')
        if len(parts) < 2:
            raise ValueError("Invalid reference format")
        
        book_name = ' '.join(parts[:-1])
        chapter_verse = parts[-1]
        
        if ':' not in chapter_verse:
            raise ValueError("Invalid reference format")
        
        chapter_num, verse_part = chapter_verse.split(':', 1)
        chapter_num = int(chapter_num)
        
        # Find the book
        book = Book.query.filter(
            or_(Book.name.ilike(book_name), Book.abbreviation.ilike(book_name))
        ).first()
        
        if not book:
            return jsonify({'error': f'Book "{book_name}" not found'}), 404
        
        # Find the chapter
        chapter = Chapter.query.filter_by(book_id=book.id, chapter_number=chapter_num).first()
        
        if not chapter:
            return jsonify({'error': f'Chapter {chapter_num} not found in {book.name}'}), 404
        
        # Parse verse range
        if '-' in verse_part:
            start_verse_num, end_verse_num = verse_part.split('-', 1)
            start_verse_num = int(start_verse_num)
            end_verse_num = int(end_verse_num)
        else:
            start_verse_num = end_verse_num = int(verse_part)
        
        # Get verses
        verses = Verse.query.filter(
            Verse.chapter_id == chapter.id,
            Verse.verse_number >= start_verse_num,
            Verse.verse_number <= end_verse_num
        ).order_by(Verse.verse_number).all()
        
        if not verses:
            return jsonify({'error': f'Verses not found for reference "{ref}"'}), 404
        
        # Combine text for the range
        combined_text = ' '.join([verse.text for verse in verses])
        
        return jsonify({
            'reference': ref,
            'verses': [verse.to_dict() for verse in verses],
            'combined_text': combined_text,
            'book': book.to_dict(),
            'chapter': chapter.to_dict()
        }), 200
        
    except (ValueError, IndexError) as e:
        return jsonify({'error': f'Invalid reference format: {ref}. Use format like "John 3:16" or "Romans 3:23-24"'}), 400
