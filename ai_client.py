from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import enum
import config

# ===== METADATA GENERATION MODELS =====

class BookGenre(str, enum.Enum):
    LAW = "Law"
    HISTORY = "History" 
    WISDOM = "Wisdom"
    PROPHECY = "Prophecy"
    GOSPEL = "Gospel"
    EPISTLE = "Epistle"
    APOCALYPTIC = "Apocalyptic"

class BookMetadataAI(BaseModel):
    author: str
    genre: BookGenre
    primary_audience: str
    book_level_themes: List[str]
    start_year: int   # Negative for BC, positive for AD
    end_year: int

class ChapterMetadataAI(BaseModel):
    summary: str  # 2-sentence summary
    characters: List[str]
    locations: List[str]
    chapter_level_themes: List[str]

# ===== PROPHECY GENERATION MODELS =====

class ProphecyCategory(str, enum.Enum):
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

class FulfillmentType(str, enum.Enum):
    DIRECT = "direct"           # Explicit quote/reference
    TYPOLOGICAL = "typological" # Shadow/type fulfilled  
    THEMATIC = "thematic"       # Broader theme completion
    PROGRESSIVE = "progressive" # Partial fulfillment, more to come
    INAUGURATED = "inaugurated" # Already/not yet fulfillment

class ProphecyReference(BaseModel):
    book_name: str
    chapter: int
    verse_start: int
    verse_end: int

class FulfillmentReference(BaseModel):
    book_name: str
    chapter: int
    verse_start: int
    verse_end: int
    fulfillment_type: FulfillmentType

class MessianicProphecyGenerated(BaseModel):
    claim: str
    category: ProphecyCategory
    prophecy_reference: ProphecyReference
    fulfillment_references: List[FulfillmentReference]
    fulfillment_explanation: str

class BookPropheciesGenerated(BaseModel):
    prophecies: List[MessianicProphecyGenerated]

# ===== EXISTING ANALYSIS MODELS =====

class TheologicalPerspective(str, enum.Enum):
    # Catholic
    CATHOLIC = "catholic"
    
    # Orthodox
    EASTERN_ORTHODOX = "eastern_orthodox"
    ORIENTAL_ORTHODOX = "oriental_orthodox"
    CHURCH_OF_THE_EAST = "church_of_the_east"
    
    # Protestant
    BAPTIST = "baptist"
    ANGLICAN = "anglican"
    METHODIST = "methodist"
    PENTECOSTAL = "pentecostal"
    LUTHERAN = "lutheran"
    PRESBYTERIAN = "presbyterian"
    PURITAN = "puritan"
    DUTCH_REFORMED = "dutch_reformed"
    MORAVIAN = "moravian"

class CrossReference(BaseModel):
    book: str
    chapter: int
    verse_start: int
    verse_end: Optional[int] = None
    reference_display: str
    relevance_note: str

class TheologicalAnalysis(BaseModel):
    perspective_name: TheologicalPerspective
    response_text: str
    cross_references: List[CrossReference]

class MultiPerspectiveAnalysis(BaseModel):
    analyses: List[TheologicalAnalysis]

class DimensionAnalysis(BaseModel):
    dimension_name: str
    consensus_score: float  # 0.0-1.0
    agreement_summary: str
    disagreement_summary: str
    denominational_positions: List[str]  # Flattened: ["perspective:position", ...]

class CreedConnection(BaseModel):
    creed_name: str
    relevant_doctrine: str
    denominational_adherence: List[str]  # Flattened: ["perspective:adherence", ...]
    interpretive_influence: str

class ConsensusAnalysis(BaseModel):
    overall_consensus_score: float  # 0.0-1.0
    consensus_classification: str  # "unanimous", "strong", "moderate", "divided", "contentious"
    summary: str
    
    # Theological dimensions as a list instead of dict
    theological_dimensions: List[DimensionAnalysis]
    
    # Flattened hermeneutical consensus
    interpretive_approach_alignment: float  # 0.0-1.0
    literal_vs_figurative: List[str]  # ["perspective:approach", ...]
    historical_context_emphasis: List[str]  # ["perspective:emphasis", ...]
    application_focus: List[str]  # ["perspective:focus", ...]
    cross_reference_overlap: float  # 0.0-1.0
    
    # Flattened historical consensus
    early_church_alignment: List[str]  # ["perspective:alignment", ...]
    reformation_era_impact: List[str]  # ["perspective:impact", ...]
    modern_theological_development: List[str]  # ["perspective:development", ...]
    historical_trajectory: str  # Overall narrative
    
    creedal_connections: List[CreedConnection]

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=config.GOOGLE_AI_STUDIO_API_KEY)
        
        # Base system prompt (70% static)
        self.base_system_prompt = """
You are a biblical scholar providing theological analysis from a {perspective} perspective. 

Analyze the provided biblical text and respond with:
1. A thoughtful analysis rooted in {perspective} theology and tradition
2. Relevant cross-references that support your interpretation
3. Historical and doctrinal context where appropriate

Guidelines:
- Be respectful of other theological traditions while maintaining your perspective
- Cite specific verses that relate to your analysis using the format: Book Chapter:Verse or Book Chapter:Verse-Verse
- When Strong's numbers are mentioned, reference the original language meanings to deepen your analysis. However, never directly reference Strong's numbers in your response.
- Focus on practical application when relevant
- Use scholarly but accessible language
- Provide 2-5 cross-references that directly support your analysis (must be from the Bible directly)
- Keep your response between 50-70 words
- The only markdown formatting allowed is bold. Use this to add emphasis to specific terms or ideas. 2-3 uses per response.

{perspective_instructions}

For cross-references, use these exact book names: Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Joshua, Judges, Ruth, 1 Samuel, 2 Samuel, 1 Kings, 2 Kings, 1 Chronicles, 2 Chronicles, Ezra, Nehemiah, Esther, Job, Psalms, Proverbs, Ecclesiastes, Song of Solomon, Isaiah, Jeremiah, Lamentations, Ezekiel, Daniel, Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Habakkuk, Zephaniah, Haggai, Zechariah, Malachi, Matthew, Mark, Luke, John, Acts, Romans, 1 Corinthians, 2 Corinthians, Galatians, Ephesians, Philippians, Colossians, 1 Thessalonians, 2 Thessalonians, 1 Timothy, 2 Timothy, Titus, Philemon, Hebrews, James, 1 Peter, 2 Peter, 1 John, 2 John, 3 John, Jude, Revelation
"""
        
        # Perspective-specific instructions (30% variable)
        self.perspective_instructions = {
            TheologicalPerspective.CATHOLIC: """
Emphasize Catholic teaching including:
- The role of Sacred Tradition alongside Scripture
- Magisterial authority in interpretation
- Sacramental theology and grace
- The communion of saints and Mary's intercession
- Social justice and human dignity themes
""",
            TheologicalPerspective.EASTERN_ORTHODOX: """
Emphasize Eastern Orthodox theology including:
- Theosis (deification) as the goal of Christian life
- Patristic sources and church fathers
- Liturgical and mystical tradition
- The Trinity and divine energies
- Iconography and sacramental life
""",
            TheologicalPerspective.ORIENTAL_ORTHODOX: """
Emphasize Oriental Orthodox theology including:
- Miaphysite Christology
- Ancient liturgical traditions
- Patristic heritage of the early church
- Monastic spirituality
- Cultural and historical context of ancient Christianity
""",
            TheologicalPerspective.CHURCH_OF_THE_EAST: """
Emphasize Church of the East theology including:
- Dyophysite Christology (two natures, two persons)
- Syriac liturgical and theological tradition
- Nestorian theological heritage
- East Syriac Rite and cultural context
- Historical development in Mesopotamia and Asia
- Emphasis on Christ's distinct divine and human natures
""",
            TheologicalPerspective.LUTHERAN: """
Emphasize Lutheran theology including:
- Justification by faith alone (sola fide)
- Scripture alone (sola scriptura)
- Grace alone (sola gratia)
- The priesthood of all believers
- Law and Gospel distinction
- Sacramental understanding of baptism and communion
""",
            TheologicalPerspective.BAPTIST: """
Emphasize Baptist theology including:
- Believer's baptism by immersion
- Congregational church governance
- Soul liberty and religious freedom
- The authority of Scripture
- Personal relationship with Jesus Christ
- The priesthood of all believers
""",
            TheologicalPerspective.METHODIST: """
Emphasize Methodist theology including:
- Prevenient grace and free will
- Personal holiness and sanctification
- Social justice and care for the poor
- The quadrilateral: Scripture, tradition, reason, experience
- Evangelical revival and personal conversion
- Works of mercy and piety
""",
            TheologicalPerspective.PENTECOSTAL: """
Emphasize Pentecostal theology including:
- Baptism in the Holy Spirit with evidence of speaking in tongues
- Divine healing and miracles
- The gifts of the Spirit (charismata)
- Personal relationship with Jesus as Savior, Baptizer, Healer, and Coming King
- Evangelism and missions
- Expectation of Christ's imminent return
""",
            TheologicalPerspective.ANGLICAN: """
Emphasize Anglican theology including:
- Via media between Catholicism and Protestantism
- The Book of Common Prayer and liturgical worship
- Episcopal polity and apostolic succession
- The threefold ministry: bishops, priests, deacons
- Scripture, tradition, and reason as authorities
- Comprehensive approach to theology
""",
            TheologicalPerspective.PRESBYTERIAN: """
Emphasize Presbyterian theology including:
- Reformed theology and Westminster standards
- Presbyterian polity with elected elders
- The sovereignty of God in salvation
- Covenant theology and infant baptism
- The authority and sufficiency of Scripture
- The importance of education and intellectual faith
""",
            TheologicalPerspective.PURITAN: """
Emphasize Puritan theology including:
- Covenant theology and federal headship
- Experimental religion and personal piety
- The regulative principle of worship
- Sabbatarianism and holy living
- Scripture as the sole authority for faith and practice
- The importance of preaching and catechesis
""",
            TheologicalPerspective.DUTCH_REFORMED: """
Emphasize Dutch Reformed theology including:
- Three Forms of Unity (Belgic Confession, Heidelberg Catechism, Canons of Dort)
- Covenant theology and infant baptism
- The sovereignty of God in all areas of life
- Cultural mandate and sphere sovereignty
- Reformed epistemology and worldview
- The antithesis between belief and unbelief
""",
            TheologicalPerspective.MORAVIAN: """
Emphasize Moravian theology including:
- Personal relationship with Christ as Savior
- Unity of the Spirit in the bond of peace
- Simple, heartfelt worship and liturgy
- Missionary zeal and global evangelism
- Community life and mutual care
- The blood and wounds theology of Christ's sacrifice
"""
        }
    
    def generate_verse_summary(self, verse_text: str, verse_reference: str, perspectives: List[TheologicalPerspective], strongs_data: dict = None) -> MultiPerspectiveAnalysis:
        """Generate theological summaries from multiple perspectives for given verse(s)"""
        analyses = []
        
        for perspective in perspectives:
            system_instruction = self.base_system_prompt.format(
                perspective=perspective.value.replace('_', ' ').title(),
                perspective_instructions=self.perspective_instructions[perspective]
            )
            
            # Build enhanced prompt with Strong's data if available
            strongs_info = ""
            if strongs_data and strongs_data.get('text_with_strongs'):
                strongs_info = f"""
Text with Strong's numbers: "{strongs_data['text_with_strongs']}"
Key Strong's numbers in this passage: {', '.join(strongs_data.get('strongs_numbers', []))}

Note: Use the Strong's numbers to provide deeper insights into the original Hebrew/Greek meanings where relevant to your theological perspective.
"""
            
            prompt = f"""
Analyze this biblical passage from a {perspective.value.replace('_', ' ')} perspective:

Reference: {verse_reference}
Text: "{verse_text}"
{strongs_info}

Provide your theological analysis with relevant cross-references.
"""
            
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=TheologicalAnalysis,
                    )
                )
                
                analysis = response.parsed
                analyses.append(analysis)
                
            except Exception as e:
                print(f"Error generating analysis for {perspective.value}: {str(e)}")
                # Create a fallback response
                analyses.append(TheologicalAnalysis(
                    perspective_name=perspective,
                    response_text=f"Analysis temporarily unavailable for {perspective.value.replace('_', ' ')} perspective.",
                    cross_references=[]
                ))
        
        return MultiPerspectiveAnalysis(analyses=analyses)
    
    def generate_scholarly_consensus_analysis(self, verse_text: str, verse_reference: str, existing_analyses: List[TheologicalAnalysis]) -> ConsensusAnalysis:
        """Generate comprehensive scholarly consensus analysis from existing perspective analyses"""
        
        # Prepare the analyses for the LLM
        analyses_text = "\n\n".join([
            f"**{analysis.perspective_name.value} Perspective:**\n{analysis.response_text}\n\nCross-references: {', '.join([f'{ref.book} {ref.chapter}:{ref.verse_start}' for ref in analysis.cross_references])}"
            for analysis in existing_analyses
        ])
        
        system_prompt = """
You are a theological scholar conducting a comprehensive consensus analysis across multiple Christian denominational perspectives.

Your task is to analyze the provided denominational responses to a biblical passage and generate a scholarly consensus report that examines:
1. Overall agreement and disagreement patterns
2. Theological dimensions where consensus exists or diverges
3. Hermeneutical approaches and their alignment
4. Historical development of interpretations
5. Connections to major creeds and councils

Be thorough but precise. Focus on substantive theological analysis rather than surface-level observations.

IMPORTANT: Format all perspective-specific data as "perspective:description" strings in lists.

For theological dimensions, analyze these key areas:
- Soteriology (salvation doctrine)
- Christology (nature and work of Christ)
- Pneumatology (Holy Spirit's role)
- Ecclesiology (church doctrine and authority)
- Eschatology (end times doctrine)
- Sacramentology (sacraments and ordinances)

For each dimension, provide:
- A consensus score (0.0-1.0, where 1.0 = complete agreement)
- Summary of agreements
- Summary of disagreements
- denominational_positions as list of "perspective:position" strings

For hermeneutical analysis, provide:
- interpretive_approach_alignment score (0.0-1.0)
- literal_vs_figurative as list of "perspective:approach" strings
- historical_context_emphasis as list of "perspective:emphasis" strings
- application_focus as list of "perspective:focus" strings
- cross_reference_overlap score (0.0-1.0)

For historical consensus, provide:
- early_church_alignment as list of "perspective:alignment" strings
- reformation_era_impact as list of "perspective:impact" strings
- modern_theological_development as list of "perspective:development" strings
- historical_trajectory as overall narrative string

For creedal connections, provide list of connections with:
- creed_name
- relevant_doctrine
- denominational_adherence as list of "perspective:adherence" strings
- interpretive_influence as string

Example format for lists: ["catholic:emphasizes sacramental grace", "baptist:focuses on personal faith", "lutheran:balances grace and faith"]

Provide specific examples and avoid generalizations. Your analysis should be scholarly, nuanced, and respectful of all traditions.
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=f"""
Biblical Passage: {verse_reference}
Text: {verse_text}

Denominational Analyses:
{analyses_text}

Generate a comprehensive scholarly consensus analysis examining the agreement and disagreement patterns across these denominational perspectives.
""",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type='application/json',
                    response_schema=ConsensusAnalysis
                )
            )
            
            return response.parsed
            
        except Exception as e:
            print(f"Error generating scholarly consensus analysis: {e}")
            # Return a basic fallback response with flattened structure
            return ConsensusAnalysis(
                overall_consensus_score=0.5,
                consensus_classification="moderate",
                summary="Unable to generate detailed consensus analysis at this time.",
                theological_dimensions=[],
                interpretive_approach_alignment=0.5,
                literal_vs_figurative=[],
                historical_context_emphasis=[],
                application_focus=[],
                cross_reference_overlap=0.5,
                early_church_alignment=[],
                reformation_era_impact=[],
                modern_theological_development=[],
                historical_trajectory="Analysis unavailable",
                creedal_connections=[]
            )
    
    def generate_question_response(self, verse_text: str, verse_reference: str, user_question: str, perspectives: List[str], strongs_data: dict = None) -> MultiPerspectiveAnalysis:
        """Generate responses to user questions from multiple theological perspectives"""
        analyses = []
        
        for perspective_str in perspectives:
            perspective = TheologicalPerspective(perspective_str)
            system_instruction = self.base_system_prompt.format(
                perspective=perspective.value.replace('_', ' ').title(),
                perspective_instructions=self.perspective_instructions[perspective]
            )
            
            # Add Strong's information if available
            strongs_info = ""
            if strongs_data:
                strongs_info = f"""
Text with Strong's numbers: "{strongs_data['text_with_strongs']}"
Key Strong's numbers in this passage: {', '.join(strongs_data.get('strongs_numbers', []))}

Note: Use the Strong's numbers to provide deeper insights into the original Hebrew/Greek meanings where relevant to answering the question.
"""
            
            prompt = f"""
Answer this specific question about the biblical passage from a {perspective.value.replace('_', ' ')} perspective:

Reference: {verse_reference}
Text: "{verse_text}"
{strongs_info}

Question: {user_question}

Provide a thoughtful answer that addresses the question directly, supported by relevant cross-references.
"""
            
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=TheologicalAnalysis,
                    )
                )
                
                analysis = response.parsed
                analyses.append(analysis)
                
            except Exception as e:
                print(f"Error generating response for {perspective.value}: {str(e)}")
                # Create a fallback response
                analyses.append(TheologicalAnalysis(
                    perspective_name=perspective,
                    response_text=f"Response temporarily unavailable for {perspective.value.replace('_', ' ')} perspective.",
                    cross_references=[]
                ))
        
        return MultiPerspectiveAnalysis(analyses=analyses)

# Initialize the client
gemini_client = GeminiClient()
