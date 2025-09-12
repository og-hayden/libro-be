from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import json
import enum

db = SQLAlchemy()

# ===== ENUMS =====

class BookGenre(enum.Enum):
    LAW = "Law"
    HISTORY = "History" 
    WISDOM = "Wisdom"
    PROPHECY = "Prophecy"
    GOSPEL = "Gospel"
    EPISTLE = "Epistle"
    APOCALYPTIC = "Apocalyptic"

class ProphecyCategory(enum.Enum):
    BIRTH_CIRCUMSTANCES = "birth_circumstances"
    GENEALOGY_LINEAGE = "genealogy_lineage"
    GEOGRAPHIC_LOCATIONS = "geographic_locations"
    MINISTRY_MISSION = "ministry_mission"
    CHARACTER_ATTRIBUTES = "character_attributes"
    DEATH_CRUCIFIXION = "death_crucifixion"
    RESURRECTION_EXALTATION = "resurrection_exaltation"
    SECOND_COMING = "second_coming"
    KINGDOM_REIGN = "kingdom_reign"
    PRIESTLY_WORK = "priestly_work"
    PROPHETIC_OFFICE = "prophetic_office"
    DIVINE_NATURE = "divine_nature"

class FulfillmentType(enum.Enum):
    DIRECT = "direct"
    TYPOLOGICAL = "typological"
    THEMATIC = "thematic"
    PROGRESSIVE = "progressive"
    INAUGURATED = "inaugurated"

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    abbreviation = db.Column(db.String(10), nullable=False)
    testament = db.Column(db.String(10), nullable=False)  # 'Old' or 'New'
    order_number = db.Column(db.Integer, nullable=False)
    
    # Relationships
    chapters = db.relationship('Chapter', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'testament': self.testament,
            'order_number': self.order_number,
            'chapter_count': len(self.chapters)
        }

class Chapter(db.Model):
    __tablename__ = 'chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False)
    
    # Relationships
    verses = db.relationship('Verse', backref='chapter', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'chapter_number': self.chapter_number,
            'verse_count': len(self.verses)
        }

class Verse(db.Model):
    __tablename__ = 'verses'
    
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    verse_number = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    text_with_strongs = db.Column(db.Text, nullable=True)  # Original text with Strong's numbers
    strongs_numbers = db.Column(db.JSON, nullable=True)  # Array of Strong's numbers in this verse
    
    # Relationships
    
    def to_dict(self, include_strongs=False):
        result = {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'verse_number': self.verse_number,
            'text': self.text,
            'reference': f"{self.chapter.book.name} {self.chapter.chapter_number}:{self.verse_number}"
        }
        
        if include_strongs and self.text_with_strongs:
            result['text_with_strongs'] = self.text_with_strongs
            result['strongs_numbers'] = self.strongs_numbers or []
            
        return result


class VerseSummary(db.Model):
    __tablename__ = 'verse_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    verse_range_start = db.Column(db.Integer, db.ForeignKey('verses.id'), nullable=False)
    verse_range_end = db.Column(db.Integer, db.ForeignKey('verses.id'), nullable=False)
    selected_text_hash = db.Column(db.String(64), nullable=False, index=True)
    perspectives = db.Column(db.JSON, nullable=False)  # JSON with all theological perspectives
    cross_references = db.Column(db.JSON, nullable=False)  # JSON array of verse references
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    start_verse = db.relationship('Verse', foreign_keys=[verse_range_start])
    end_verse = db.relationship('Verse', foreign_keys=[verse_range_end])
    
    @staticmethod
    def generate_text_hash(text):
        """Generate a hash for the selected text to enable caching"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def to_dict(self):
        return {
            'id': self.id,
            'verse_range_start': self.verse_range_start,
            'verse_range_end': self.verse_range_end,
            'perspectives': self.perspectives,
            'cross_references': self.cross_references,
            'created_at': self.created_at.isoformat()
        }

class SearchCache(db.Model):
    __tablename__ = 'search_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    query_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    query_text = db.Column(db.Text, nullable=False)
    result_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_query_hash(query_text):
        """Generate a hash for the search query to enable caching"""
        return hashlib.sha256(query_text.encode('utf-8')).hexdigest()
    
    def __repr__(self):
        return f'<SearchCache {self.query_text[:50]}...>'

class StrongsConcordanceCache(db.Model):
    __tablename__ = 'strongs_concordance_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    strongs_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    result_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<StrongsConcordanceCache {self.strongs_number}>'

class StrongsEntry(db.Model):
    __tablename__ = 'strongs_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    strongs_number = db.Column(db.String(10), unique=True, nullable=False, index=True)  # e.g., "H430", "G2316"
    language = db.Column(db.String(10), nullable=False)  # "Hebrew" or "Greek"
    transliteration = db.Column(db.String(100))
    pronunciation = db.Column(db.String(100))
    definition = db.Column(db.Text)
    kjv_usage = db.Column(db.Text)  # How it's used in KJV
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    verse_mappings = db.relationship('VerseStrongsMapping', 
                                    primaryjoin='StrongsEntry.strongs_number == VerseStrongsMapping.strongs_number',
                                    foreign_keys='VerseStrongsMapping.strongs_number',
                                    backref='strongs_entry', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'strongs_number': self.strongs_number,
            'language': self.language,
            'transliteration': self.transliteration,
            'pronunciation': self.pronunciation,
            'definition': self.definition,
            'kjv_usage': self.kjv_usage,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class VerseStrongsMapping(db.Model):
    __tablename__ = 'verse_strongs_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    verse_id = db.Column(db.Integer, db.ForeignKey('verses.id'), nullable=False)
    strongs_number = db.Column(db.String(10), nullable=False, index=True)
    word_position = db.Column(db.Integer, nullable=False)  # Position of word in verse
    grammatical_info = db.Column(db.String(20), nullable=True)  # e.g., (H8804) for verb forms
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    verse = db.relationship('Verse', backref='strongs_mappings')
    
    def to_dict(self):
        return {
            'id': self.id,
            'verse_id': self.verse_id,
            'strongs_number': self.strongs_number,
            'word_position': self.word_position,
            'grammatical_info': self.grammatical_info,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ===== BOOK AND CHAPTER METADATA TABLES =====

class BookMetadata(db.Model):
    __tablename__ = 'book_metadata'
    
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), primary_key=True)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.Enum(BookGenre), nullable=False)
    primary_audience = db.Column(db.String(255), nullable=False)
    start_year = db.Column(db.Integer, nullable=False)  # Negative for BC
    end_year = db.Column(db.Integer, nullable=False)    # Negative for BC
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    book = db.relationship('Book', backref=db.backref('metadata', uselist=False))
    
    def to_dict(self):
        return {
            'book_id': self.book_id,
            'author': self.author,
            'genre': self.genre.value if self.genre else None,
            'primary_audience': self.primary_audience,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'date_range_display': self._format_date_range(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def _format_date_range(self):
        """Format the date range for display"""
        start_display = f"{abs(self.start_year)} BC" if self.start_year < 0 else f"{self.start_year} AD"
        end_display = f"{abs(self.end_year)} BC" if self.end_year < 0 else f"{self.end_year} AD"
        
        if self.start_year == self.end_year:
            return start_display
        else:
            return f"{start_display} - {end_display}"

class ChapterMetadata(db.Model):
    __tablename__ = 'chapter_metadata'
    
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), primary_key=True)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    chapter = db.relationship('Chapter', backref=db.backref('metadata', uselist=False))
    
    def to_dict(self):
        return {
            'chapter_id': self.chapter_id,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MessianicProphecy(db.Model):
    __tablename__ = 'messianic_prophecies'
    
    id = db.Column(db.Integer, primary_key=True)
    claim = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum(ProphecyCategory), nullable=False)
    
    # Prophecy verse references (stored as FK after conversion)
    prophecy_verse_start = db.Column(db.Integer, db.ForeignKey('verses.id'), nullable=False)
    prophecy_verse_end = db.Column(db.Integer, db.ForeignKey('verses.id'), nullable=False)
    
    # Fulfillment data (JSON array)
    fulfillment_references = db.Column(db.JSON, nullable=False)
    fulfillment_explanation = db.Column(db.Text, nullable=False)
    
    # Metadata
    generated_from_book = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    start_verse = db.relationship('Verse', foreign_keys=[prophecy_verse_start])
    end_verse = db.relationship('Verse', foreign_keys=[prophecy_verse_end])
    
    def to_dict(self):
        return {
            'id': self.id,
            'claim': self.claim,
            'category': self.category.value if self.category else None,
            'prophecy_verse_start': self.prophecy_verse_start,
            'prophecy_verse_end': self.prophecy_verse_end,
            'fulfillment_references': self.fulfillment_references,
            'fulfillment_explanation': self.fulfillment_explanation,
            'generated_from_book': self.generated_from_book,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'start_verse_reference': f"{self.start_verse.chapter.book.name} {self.start_verse.chapter.chapter_number}:{self.start_verse.verse_number}" if self.start_verse else None
        }
