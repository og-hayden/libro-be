from flask import Blueprint, jsonify, request
from models import (
    db, Book, Chapter,
    BookMetadata, ChapterMetadata
)
from sqlalchemy.orm import joinedload

metadata_bp = Blueprint('metadata', __name__)

@metadata_bp.route('/book/<int:book_id>', methods=['GET'])
def get_book_metadata(book_id):
    """Get complete metadata for a book"""
    try:
        book = Book.query.options(
            joinedload(Book.metadata)
        ).filter_by(id=book_id).first()
        
        if not book:
            return jsonify({'error': 'Book not found'}), 404
        
        if not book.metadata:
            return jsonify({'error': 'Book metadata not available'}), 404
        
        response = {
            'book': {
                'id': book.id,
                'name': book.name,
                'abbreviation': book.abbreviation,
                'testament': book.testament,
                'order_number': book.order_number,
                'metadata': book.metadata.to_dict()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@metadata_bp.route('/chapter/<int:chapter_id>', methods=['GET'])
def get_chapter_metadata(chapter_id):
    """Get complete metadata for a chapter including book context"""
    try:
        chapter = Chapter.query.options(
            joinedload(Chapter.book).joinedload(Book.metadata),
            joinedload(Chapter.metadata)
        ).filter_by(id=chapter_id).first()
        
        if not chapter:
            return jsonify({'error': 'Chapter not found'}), 404
        
        # Build response with book and chapter data
        response = {
            'book': {
                'id': chapter.book.id,
                'name': chapter.book.name,
                'abbreviation': chapter.book.abbreviation,
                'testament': chapter.book.testament,
                'order_number': chapter.book.order_number
            },
            'chapter': {
                'id': chapter.id,
                'number': chapter.chapter_number,
                'verse_count': len(chapter.verses)
            }
        }
        
        # Add book metadata if available
        if chapter.book.metadata:
            response['book']['metadata'] = chapter.book.metadata.to_dict()
        
        # Add chapter summary if available
        if chapter.metadata:
            response['chapter']['metadata'] = chapter.metadata.to_dict()
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

