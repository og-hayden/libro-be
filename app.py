import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import config

app = Flask(__name__)

# Database configuration from config.py
DATABASE_URL = f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize extensions
from models import db
db.init_app(app)
migrate = Migrate(app, db)

# Configure CORS to allow all origins (NOT SECURE - for quick deployment only)
CORS(app, origins="*", supports_credentials=True)

# Import models after db initialization
from models import Book, Chapter, Verse, VerseSummary, SearchCache, StrongsEntry, VerseStrongsMapping, BookMetadata, ChapterMetadata

# Import and register blueprints
from routes.bible import bible_bp
from routes.analysis import analysis_bp
from routes.strongs import strongs_bp
from routes.metadata import metadata_bp
from routes.search import search_bp
from routes.prophecy import prophecy_bp

app.register_blueprint(bible_bp, url_prefix='/api/bible')
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
app.register_blueprint(strongs_bp, url_prefix='/api/strongs')
app.register_blueprint(metadata_bp, url_prefix='/api/metadata')
app.register_blueprint(search_bp, url_prefix='/api/search')
app.register_blueprint(prophecy_bp, url_prefix='/api/prophecy')

@app.route('/')
def health_check():
    return {'status': 'healthy', 'message': 'Libro Bible API is running'}

@app.route('/health')
def health_check_endpoint():
    try:
        # Basic database connectivity check
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'healthy', 'message': 'Libro Bible API is running', 'database': 'connected'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': 'Database connection failed', 'error': str(e)}, 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = config.FLASK_ENV != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
