from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_, func
from models import (
    db, Book, Chapter, Verse,
    BookMetadata, ChapterMetadata
)

search_bp = Blueprint('search', __name__)

@search_bp.route('/books', methods=['GET'])
def search_books():
    """Search for books by name or abbreviation"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'books': []})
    
    # Search books by name or abbreviation (case-insensitive, partial match)
    books = Book.query.filter(
        or_(
            Book.name.ilike(f'%{query}%'),
            Book.abbreviation.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    return jsonify({
        'books': [{
            'id': book.id,
            'name': book.name,
            'abbreviation': book.abbreviation,
            'testament': book.testament,
            'chapter_count': len(book.chapters)
        } for book in books]
    })

@search_bp.route('/verses', methods=['GET'])
def search_verses():
    """Search verse text"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return jsonify({'verses': []})
    
    # Search verse text (case-insensitive)
    verses = db.session.query(Verse, Chapter, Book).join(
        Chapter, Verse.chapter_id == Chapter.id
    ).join(
        Book, Chapter.book_id == Book.id
    ).filter(
        Verse.text.ilike(f'%{query}%')
    ).order_by(Book.order_number, Chapter.chapter_number, Verse.verse_number).limit(50).all()
    
    return jsonify({
        'verses': [{
            'id': verse.id,
            'verse_number': verse.verse_number,
            'text': verse.text,
            'reference': f"{book.name} {chapter.chapter_number}:{verse.verse_number}",
            'chapter': {
                'id': chapter.id,
                'chapter_number': chapter.chapter_number
            },
            'book': {
                'id': book.id,
                'name': book.name,
                'abbreviation': book.abbreviation
            }
        } for verse, chapter, book in verses]
    })

@search_bp.route('/chapters', methods=['GET'])
def search_chapters():
    """Search chapter summaries"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return jsonify({'chapters': []})
    
    # Search chapter summaries (case-insensitive)
    chapters = db.session.query(Chapter, Book, ChapterMetadata).join(
        Book, Chapter.book_id == Book.id
    ).join(
        ChapterMetadata, Chapter.id == ChapterMetadata.chapter_id
    ).filter(
        ChapterMetadata.summary.ilike(f'%{query}%')
    ).order_by(Book.order_number, Chapter.chapter_number).limit(30).all()
    
    return jsonify({
        'chapters': [{
            'id': chapter.id,
            'chapter_number': chapter.chapter_number,
            'reference': f"{book.name} {chapter.chapter_number}",
            'summary': metadata.summary,
            'book': {
                'id': book.id,
                'name': book.name,
                'abbreviation': book.abbreviation
            }
        } for chapter, book, metadata in chapters]
    })

@search_bp.route('/suggestions', methods=['GET'])
def search_suggestions():
    """Get search suggestions for autocomplete"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    suggestions = []
    
    # Search books
    books = Book.query.filter(
        or_(
            Book.name.ilike(f'%{query}%'),
            Book.abbreviation.ilike(f'%{query}%')
        )
    ).limit(10).all()
    for book in books:
        suggestions.append({
            'type': 'book',
            'id': book.id,
            'name': book.name,
            'display': f"Book: {book.name}"
        })
    
    return jsonify({'suggestions': suggestions})

@search_bp.route('/comprehensive', methods=['GET'])
def comprehensive_search():
    """Comprehensive search across books, verses, and chapter summaries"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'books': [],
            'verses': [],
            'chapters': []
        })
    
    # Search books
    books = Book.query.filter(
        or_(
            Book.name.ilike(f'%{query}%'),
            Book.abbreviation.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    # Search verses
    verses = db.session.query(Verse, Chapter, Book).join(
        Chapter, Verse.chapter_id == Chapter.id
    ).join(
        Book, Chapter.book_id == Book.id
    ).filter(
        Verse.text.ilike(f'%{query}%')
    ).order_by(Book.order_number, Chapter.chapter_number, Verse.verse_number).limit(20).all()
    
    # Search chapter summaries
    chapters = db.session.query(Chapter, Book, ChapterMetadata).join(
        Book, Chapter.book_id == Book.id
    ).join(
        ChapterMetadata, Chapter.id == ChapterMetadata.chapter_id
    ).filter(
        ChapterMetadata.summary.ilike(f'%{query}%')
    ).order_by(Book.order_number, Chapter.chapter_number).limit(15).all()
    
    return jsonify({
        'books': [{
            'id': book.id,
            'name': book.name,
            'abbreviation': book.abbreviation,
            'testament': book.testament,
            'chapter_count': len(book.chapters)
        } for book in books],
        'verses': [{
            'id': verse.id,
            'verse_number': verse.verse_number,
            'text': verse.text,
            'reference': f"{book.name} {chapter.chapter_number}:{verse.verse_number}",
            'chapter': {
                'id': chapter.id,
                'chapter_number': chapter.chapter_number
            },
            'book': {
                'id': book.id,
                'name': book.name,
                'abbreviation': book.abbreviation
            }
        } for verse, chapter, book in verses],
        'chapters': [{
            'id': chapter.id,
            'chapter_number': chapter.chapter_number,
            'reference': f"{book.name} {chapter.chapter_number}",
            'summary': metadata.summary,
            'book': {
                'id': book.id,
                'name': book.name,
                'abbreviation': book.abbreviation
            }
        } for chapter, book, metadata in chapters]
    })
