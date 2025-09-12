from flask import Blueprint, request, jsonify
from models import Verse, VerseSummary, db
from ai_client import gemini_client, TheologicalPerspective, TheologicalAnalysis
from marshmallow import Schema, fields, ValidationError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)

class SummaryRequestSchema(Schema):
    verse_range_start = fields.Int(required=True)
    verse_range_end = fields.Int(required=False)
    perspectives = fields.List(fields.Str(), required=False)

class QuestionRequestSchema(Schema):
    verse_range_start = fields.Int(required=True)
    verse_range_end = fields.Int(required=False)
    question = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    perspectives = fields.List(fields.Str(), required=False)

class ScholarlyConsensusRequestSchema(Schema):
    verse_range_start = fields.Int(required=True)
    verse_range_end = fields.Int(required=False)
    existing_analysis_id = fields.Str(required=False)  # Future: reference to cached analysis
    perspectives = fields.List(fields.Str(), required=False)
    existing_analyses = fields.List(fields.Dict(), required=False)  # Accept existing analyses from frontend

def validate_perspectives(perspective_names):
    """Validate that perspective names are valid"""
    valid_perspectives = [p.value for p in TheologicalPerspective]
    invalid = [p for p in perspective_names if p not in valid_perspectives]
    if invalid:
        raise ValidationError(f"Invalid perspectives: {invalid}. Valid options: {valid_perspectives}")
    return [TheologicalPerspective(p) for p in perspective_names]

def get_verse_text_and_reference(start_verse_id, end_verse_id=None):
    """Get combined text and reference for verse range"""
    if end_verse_id is None:
        end_verse_id = start_verse_id
    
    start_verse = Verse.query.get(start_verse_id)
    end_verse = Verse.query.get(end_verse_id)
    
    if not start_verse or not end_verse:
        return None, None, "Verse(s) not found"
    
    # Get all verses in range
    verses = Verse.query.filter(
        Verse.id >= start_verse_id,
        Verse.id <= end_verse_id
    ).order_by(Verse.id).all()
    
    if not verses:
        return None, None, "No verses found in range"
    
    # Combine text
    combined_text = ' '.join([verse.text for verse in verses])
    
    # Create reference
    if start_verse_id == end_verse_id:
        reference = f"{start_verse.chapter.book.name} {start_verse.chapter.chapter_number}:{start_verse.verse_number}"
    else:
        reference = f"{start_verse.chapter.book.name} {start_verse.chapter.chapter_number}:{start_verse.verse_number}-{end_verse.verse_number}"
    
    return combined_text, reference, None

@analysis_bp.route('/summary', methods=['POST'])
def generate_summary():
    """Generate theological summary for verse(s) from multiple perspectives"""
    
    schema = SummaryRequestSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation failed', 'messages': err.messages}), 400
    
    start_verse_id = data['verse_range_start']
    end_verse_id = data.get('verse_range_end', start_verse_id)
    
    # Get verse text and reference
    verse_text, reference, error = get_verse_text_and_reference(start_verse_id, end_verse_id)
    if error:
        return jsonify({'error': error}), 404
    
    # Determine perspectives to use
    requested_perspectives = data.get('perspectives', ['catholic', 'baptist'])
    try:
        perspectives = validate_perspectives(requested_perspectives)
    except ValidationError as err:
        return jsonify({'error': str(err)}), 400
    
    # Check if summary already exists in cache
    text_hash = VerseSummary.generate_text_hash(verse_text)
    cached_summary = VerseSummary.query.filter_by(
        verse_range_start=start_verse_id,
        verse_range_end=end_verse_id,
        selected_text_hash=text_hash
    ).first()
    
    if cached_summary:
        # Filter cached perspectives based on requested ones
        filtered_perspectives = {}
        for perspective in perspectives:
            perspective_key = perspective.value
            if perspective_key in cached_summary.perspectives:
                filtered_perspectives[perspective_key] = cached_summary.perspectives[perspective_key]
        
        if filtered_perspectives:
            return jsonify({
                'verse_range_start': start_verse_id,
                'verse_range_end': end_verse_id,
                'reference': reference,
                'verse_text': verse_text,
                'perspectives': filtered_perspectives,
                'cross_references': cached_summary.cross_references,
                'cached': True
            }), 200
    
    # Prepare Strong's data if available
    strongs_data = None
    # Get verses for Strong's data
    verse_objects = Verse.query.filter(
        Verse.id >= start_verse_id,
        Verse.id <= end_verse_id
    ).order_by(Verse.id).all()
    
    if verse_objects and verse_objects[0].text_with_strongs:
        strongs_data = {
            'text_with_strongs': verse_objects[0].text_with_strongs,
            'strongs_numbers': verse_objects[0].strongs_numbers or []
        }
    
    # Generate new analysis
    try:
        analysis_result = gemini_client.generate_verse_summary(verse_text, reference, perspectives, strongs_data)
        
        # Convert to storage format
        perspectives_data = {}
        all_cross_references = []
        
        for analysis in analysis_result.analyses:
            perspective_key = analysis.perspective_name.value
            perspectives_data[perspective_key] = {
                'response_text': analysis.response_text,
                'cross_references': [ref.dict() for ref in analysis.cross_references]
            }
            all_cross_references.extend([ref.dict() for ref in analysis.cross_references])
        
        # Save to cache if we don't have it already
        if not cached_summary:
            summary = VerseSummary(
                verse_range_start=start_verse_id,
                verse_range_end=end_verse_id,
                selected_text_hash=text_hash,
                perspectives=perspectives_data,
                cross_references=all_cross_references
            )
            db.session.add(summary)
            db.session.commit()
        else:
            # Update existing cache with new perspectives
            cached_summary.perspectives.update(perspectives_data)
            cached_summary.cross_references.extend(all_cross_references)
            db.session.commit()
        
        return jsonify({
            'verse_range_start': start_verse_id,
            'verse_range_end': end_verse_id,
            'reference': reference,
            'verse_text': verse_text,
            'perspectives': perspectives_data,
            'cross_references': all_cross_references,
            'cached': False
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate analysis: {str(e)}'}), 500

@analysis_bp.route('/question', methods=['POST'])
def answer_question():
    """Answer a specific question about verse(s) from multiple theological perspectives"""
    
    schema = QuestionRequestSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation failed', 'messages': err.messages}), 400
    
    start_verse_id = data['verse_range_start']
    end_verse_id = data.get('verse_range_end', start_verse_id)
    question = data['question'].strip()
    
    # Get verse text and reference
    verse_text, reference, error = get_verse_text_and_reference(start_verse_id, end_verse_id)
    if error:
        return jsonify({'error': error}), 404
    
    # Determine perspectives to use
    requested_perspectives = data.get('perspectives', ['catholic', 'baptist'])
    try:
        perspectives = validate_perspectives(requested_perspectives)
    except ValidationError as err:
        return jsonify({'error': str(err)}), 400
    
    # Prepare Strong's data if available
    strongs_data = None
    # Get verses for Strong's data
    verse_objects = Verse.query.filter(
        Verse.id >= start_verse_id,
        Verse.id <= end_verse_id
    ).order_by(Verse.id).all()
    
    if verse_objects and verse_objects[0].text_with_strongs:
        strongs_data = {
            'text_with_strongs': verse_objects[0].text_with_strongs,
            'strongs_numbers': verse_objects[0].strongs_numbers or []
        }
    
    # Generate response (never cached for questions)
    try:
        analysis_result = gemini_client.generate_question_response(verse_text, reference, question, perspectives, strongs_data)
        
        # Convert to storage format
        perspectives_data = {}
        all_cross_references = []
        
        for analysis in analysis_result.analyses:
            perspective_key = analysis.perspective_name.value
            perspectives_data[perspective_key] = {
                'response_text': analysis.response_text,
                'cross_references': [ref.dict() for ref in analysis.cross_references]
            }
            all_cross_references.extend([ref.dict() for ref in analysis.cross_references])
        
        return jsonify({
            'verse_range_start': start_verse_id,
            'verse_range_end': end_verse_id,
            'reference': reference,
            'verse_text': verse_text,
            'question': question,
            'perspectives': perspectives_data,
            'cross_references': all_cross_references,
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate response: {str(e)}'}), 500

@analysis_bp.route('/scholarly-consensus', methods=['POST'])
def generate_scholarly_consensus():
    """Generate comprehensive scholarly consensus analysis from existing denominational perspectives"""
    
    logger.info("=== SCHOLARLY CONSENSUS REQUEST ===")
    logger.info(f"Request JSON: {request.json}")
    
    schema = ScholarlyConsensusRequestSchema()
    
    try:
        data = schema.load(request.json)
        logger.info(f"Validated data: {data}")
    except ValidationError as err:
        logger.error(f"Validation error: {err.messages}")
        return jsonify({'error': 'Validation failed', 'messages': err.messages}), 400
    
    start_verse_id = data['verse_range_start']
    end_verse_id = data.get('verse_range_end', start_verse_id)
    
    # Get verse text and reference
    verse_text, reference, error = get_verse_text_and_reference(start_verse_id, end_verse_id)
    logger.info(f"Verse text: {verse_text}")
    logger.info(f"Reference: {reference}")
    if error:
        logger.error(f"Verse lookup error: {error}")
        return jsonify({'error': error}), 404
    
    # Determine perspectives to use
    requested_perspectives = data.get('perspectives', ['catholic', 'baptist', 'eastern_orthodox', 'lutheran', 'reformed'])
    logger.info(f"Requested perspectives: {requested_perspectives}")
    try:
        perspectives = validate_perspectives(requested_perspectives)
        logger.info(f"Validated perspectives: {[p.value for p in perspectives]}")
    except ValidationError as err:
        logger.error(f"Perspective validation error: {err}")
        return jsonify({'error': str(err)}), 400
    
    # First, get the existing denominational analyses
    # Check if summary already exists in cache
    text_hash = VerseSummary.generate_text_hash(verse_text)
    cached_summary = VerseSummary.query.filter_by(
        verse_range_start=start_verse_id,
        verse_range_end=end_verse_id,
        selected_text_hash=text_hash
    ).first()
    
    existing_analyses = []
    
    logger.info(f"Cached summary found: {cached_summary is not None}")
    
    if cached_summary:
        logger.info(f"Cached perspectives available: {list(cached_summary.perspectives.keys())}")
        # Use cached analyses
        for perspective in perspectives:
            perspective_key = perspective.value
            if perspective_key in cached_summary.perspectives:
                cached_data = cached_summary.perspectives[perspective_key]
                logger.info(f"Using cached data for {perspective_key}")
                # Convert cached data back to TheologicalAnalysis objects
                from ai_client import CrossReference
                cross_refs = [CrossReference(**ref) for ref in cached_data.get('cross_references', [])]
                analysis = TheologicalAnalysis(
                    perspective_name=perspective,
                    response_text=cached_data['response_text'],
                    cross_references=cross_refs
                )
                existing_analyses.append(analysis)
            else:
                logger.info(f"No cached data for {perspective_key}")
    
    # If we don't have enough cached analyses, generate them
    logger.info(f"Have {len(existing_analyses)} analyses, need {len(perspectives)}")
    if len(existing_analyses) < len(perspectives):
        logger.info("Need to generate missing analyses")
        # Prepare Strong's data if available
        strongs_data = None
        verse_objects = Verse.query.filter(
            Verse.id >= start_verse_id,
            Verse.id <= end_verse_id
        ).order_by(Verse.id).all()
        
        if verse_objects and verse_objects[0].text_with_strongs:
            strongs_data = {
                'text_with_strongs': verse_objects[0].text_with_strongs,
                'strongs_numbers': verse_objects[0].strongs_numbers or []
            }
        
        # Generate missing analyses
        missing_perspectives = [p.value for p in perspectives if p.value not in [a.perspective_name.value for a in existing_analyses]]
        logger.info(f"Missing perspectives: {missing_perspectives}")
        if missing_perspectives:
            logger.info("Generating analyses for missing perspectives...")
            analysis_result = gemini_client.generate_verse_summary(verse_text, reference, [TheologicalPerspective(p) for p in missing_perspectives], strongs_data)
            existing_analyses.extend(analysis_result.analyses)
            logger.info(f"Generated {len(analysis_result.analyses)} new analyses")
    
    # Now generate the scholarly consensus analysis
    logger.info(f"Starting scholarly consensus generation with {len(existing_analyses)} analyses")
    try:
        logger.info("Calling gemini_client.generate_scholarly_consensus_analysis...")
        consensus_result = gemini_client.generate_scholarly_consensus_analysis(verse_text, reference, existing_analyses)
        logger.info("Successfully generated scholarly consensus")
        logger.info(f"Raw consensus result: {consensus_result}")
        
        # Convert consensus result to JSON-serializable format with flattened structure
        consensus_data = {
            'overall_consensus_score': consensus_result.overall_consensus_score,
            'consensus_classification': consensus_result.consensus_classification,
            'summary': consensus_result.summary,
            'theological_dimensions': [
                {
                    'dimension_name': dim_analysis.dimension_name,
                    'consensus_score': dim_analysis.consensus_score,
                    'agreement_summary': dim_analysis.agreement_summary,
                    'disagreement_summary': dim_analysis.disagreement_summary,
                    'denominational_positions': dim_analysis.denominational_positions
                }
                for dim_analysis in consensus_result.theological_dimensions
            ],
            'interpretive_approach_alignment': consensus_result.interpretive_approach_alignment,
            'literal_vs_figurative': consensus_result.literal_vs_figurative,
            'historical_context_emphasis': consensus_result.historical_context_emphasis,
            'application_focus': consensus_result.application_focus,
            'cross_reference_overlap': consensus_result.cross_reference_overlap,
            'early_church_alignment': consensus_result.early_church_alignment,
            'reformation_era_impact': consensus_result.reformation_era_impact,
            'modern_theological_development': consensus_result.modern_theological_development,
            'historical_trajectory': consensus_result.historical_trajectory,
            'creedal_connections': [
                {
                    'creed_name': connection.creed_name,
                    'relevant_doctrine': connection.relevant_doctrine,
                    'denominational_adherence': connection.denominational_adherence,
                    'interpretive_influence': connection.interpretive_influence
                }
                for connection in consensus_result.creedal_connections
            ]
        }
        
        logger.info(f"Formatted consensus_data: {consensus_data}")
        
        # Also include the original denominational analyses for the modal
        denominational_analyses = {}
        for analysis in existing_analyses:
            perspective_key = analysis.perspective_name.value
            denominational_analyses[perspective_key] = {
                'response_text': analysis.response_text,
                'cross_references': [ref.dict() for ref in analysis.cross_references]
            }
        
        logger.info("Preparing response data...")
        response_data = {
            'scholarly_analysis': consensus_data,
            'denominational_analyses': denominational_analyses
        }
        
        logger.info(f"Final response_data being sent to frontend: {response_data}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error generating scholarly consensus: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to generate scholarly consensus: {str(e)}'}), 500

