from flask import Blueprint, request, jsonify
from models import db, MessianicProphecy, Verse, Chapter, Book
from sqlalchemy import or_, and_, text

prophecy_bp = Blueprint('prophecy', __name__)

@prophecy_bp.route('/chapter/<int:book_id>/<int:chapter_number>', methods=['GET'])
def get_chapter_prophecies(book_id, chapter_number):
    """Get all prophecies related to a specific chapter (both prophecies and fulfillments)"""
    
    # Get the chapter
    chapter = Chapter.query.filter_by(book_id=book_id, chapter_number=chapter_number).first()
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404
    
    # Get all verse IDs in this chapter
    verse_ids = [v.id for v in chapter.verses]
    
    # Find prophecies where this chapter contains the prophecy verse(s)
    prophecy_verses = MessianicProphecy.query.filter(
        or_(
            MessianicProphecy.prophecy_verse_start.in_(verse_ids),
            MessianicProphecy.prophecy_verse_end.in_(verse_ids)
        )
    ).all()
    
    # Find prophecies where this chapter contains fulfillment verse(s)
    # Need to check JSON fulfillment_references for verse IDs
    fulfillment_prophecies = []
    for verse_id in verse_ids:
        prophecies = db.session.execute(text("""
            SELECT * FROM messianic_prophecies mp
            WHERE mp.fulfillment_references::text LIKE :verse_pattern
        """), {'verse_pattern': f'%"verse_start_id": {verse_id}%'}).fetchall()
        
        for prophecy_row in prophecies:
            # Convert row to MessianicProphecy object
            prophecy = MessianicProphecy.query.get(prophecy_row.id)
            if prophecy not in fulfillment_prophecies:
                fulfillment_prophecies.append(prophecy)
    
    # Format response
    result = {
        'book_id': book_id,
        'chapter_number': chapter_number,
        'prophecy_verses': [],  # Verses in this chapter that are prophecies
        'fulfillment_verses': [],  # Verses in this chapter that are fulfillments
        'prophecies': []  # Full prophecy objects for sidebar display
    }
    
    # Process prophecy verses
    for prophecy in prophecy_verses:
        # Get verse numbers for highlighting
        start_verse_num = prophecy.start_verse.verse_number if prophecy.start_verse.chapter_id == chapter.id else None
        end_verse_num = prophecy.end_verse.verse_number if prophecy.end_verse.chapter_id == chapter.id else None
        
        if start_verse_num:
            verse_range = list(range(start_verse_num, (end_verse_num or start_verse_num) + 1))
            result['prophecy_verses'].append({
                'prophecy_id': prophecy.id,
                'verse_numbers': verse_range,
                'category': prophecy.category.value,
                'claim': prophecy.claim
            })
    
    # Process fulfillment verses
    for prophecy in fulfillment_prophecies:
        for fulfillment_ref in prophecy.fulfillment_references:
            if fulfillment_ref.get('verse_start_id') in verse_ids:
                # Find the verse number
                verse = Verse.query.get(fulfillment_ref['verse_start_id'])
                if verse and verse.chapter_id == chapter.id:
                    verse_range = list(range(
                        fulfillment_ref['verse_start'], 
                        fulfillment_ref['verse_end'] + 1
                    ))
                    result['fulfillment_verses'].append({
                        'prophecy_id': prophecy.id,
                        'verse_numbers': verse_range,
                        'fulfillment_type': fulfillment_ref['fulfillment_type'],
                        'original_prophecy': f"{prophecy.start_verse.chapter.book.name} {prophecy.start_verse.chapter.chapter_number}:{prophecy.start_verse.verse_number}"
                    })
    
    # Add full prophecy data for sidebar
    all_prophecies = set(prophecy_verses + fulfillment_prophecies)
    for prophecy in all_prophecies:
        result['prophecies'].append({
            'id': prophecy.id,
            'claim': prophecy.claim,
            'category': prophecy.category.value,
            'prophecy_reference': f"{prophecy.start_verse.chapter.book.name} {prophecy.start_verse.chapter.chapter_number}:{prophecy.start_verse.verse_number}",
            'fulfillment_explanation': prophecy.fulfillment_explanation,
            'fulfillment_references': [
                {
                    'reference': f"{ref['book_name']} {ref['chapter']}:{ref['verse_start']}" + (f"-{ref['verse_end']}" if ref['verse_end'] != ref['verse_start'] else ""),
                    'fulfillment_type': ref['fulfillment_type']
                }
                for ref in prophecy.fulfillment_references
            ]
        })
    
    return jsonify(result), 200

@prophecy_bp.route('/prophecy/<int:prophecy_id>', methods=['GET'])
def get_prophecy_details(prophecy_id):
    """Get detailed information about a specific prophecy"""
    prophecy = MessianicProphecy.query.get(prophecy_id)
    if not prophecy:
        return jsonify({'error': 'Prophecy not found'}), 404
    
    return jsonify({
        'id': prophecy.id,
        'claim': prophecy.claim,
        'category': prophecy.category.value,
        'prophecy_reference': {
            'book': prophecy.start_verse.chapter.book.name,
            'chapter': prophecy.start_verse.chapter.chapter_number,
            'verse_start': prophecy.start_verse.verse_number,
            'verse_end': prophecy.end_verse.verse_number,
            'text': ' '.join([v.text for v in Verse.query.filter(
                Verse.id >= prophecy.prophecy_verse_start,
                Verse.id <= prophecy.prophecy_verse_end
            ).order_by(Verse.id).all()])
        },
        'fulfillment_references': [
            {
                'book': ref['book_name'],
                'chapter': ref['chapter'],
                'verse_start': ref['verse_start'],
                'verse_end': ref['verse_end'],
                'fulfillment_type': ref['fulfillment_type'],
                'text': Verse.query.get(ref['verse_start_id']).text if ref.get('verse_start_id') else None
            }
            for ref in prophecy.fulfillment_references
        ],
        'fulfillment_explanation': prophecy.fulfillment_explanation,
        'generated_from_book': prophecy.generated_from_book
    }), 200

@prophecy_bp.route('/stats', methods=['GET'])
def get_prophecy_stats():
    """Get statistics about prophecies"""
    total = MessianicProphecy.query.count()
    by_category = db.session.execute(text("""
        SELECT category, COUNT(*) as count 
        FROM messianic_prophecies 
        GROUP BY category 
        ORDER BY count DESC
    """)).fetchall()
    
    return jsonify({
        'total_prophecies': total,
        'by_category': [{'category': row.category, 'count': row.count} for row in by_category]
    }), 200
