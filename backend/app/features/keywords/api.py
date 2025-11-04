from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ... import db # Import the db module from the app's root
# This blueprint is already registered in your __init__.py
bp = Blueprint("keywords", __name__, url_prefix="/api/keywords")


@bp.post("/match")
@jwt_required()
def match_keywords():
    try:
        # 1. Get the logged-in user's ID from the JWT token
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({"message": "Authentication required."}), 401

        # 2. Get the job description from the frontend
        data = request.get_json()
        job_description = data.get('job_description')
        if not job_description:
            return jsonify({"message": "Job description is required."}), 400

        # 3. Get the user's most recent resume from the database
        db_conn = db.get_db()
        cursor = db_conn.cursor()

        cursor.execute(
            """
            SELECT parsed_json 
            FROM resumes 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (current_user_id,)
        )
        resume_row = cursor.fetchone()

        if not resume_row:
            return jsonify({"message": "No resume found. Please upload one first."}), 404

        # 4. Extract the full text from the parsed JSON
        # --- THIS SECTION IS NOW UPDATED ---
        try:
            # Load the JSON text blob from the database
            parsed_data = json.loads(resume_row['parsed_json'])
            
            # Find the full text from the 'sections' list
            # based on your ai_helper.py
            resume_text = None
            if 'sections' in parsed_data and isinstance(parsed_data['sections'], list):
                for section in parsed_data['sections']:
                    if section.get('name') == 'full_content':
                        resume_text = section.get('content')
                        break
            
            if not resume_text:
                return jsonify({"message": "Resume parsed, but 'full_content' section not found. Please check your AIHelper."}), 500
        
        except json.JSONDecodeError:
            return jsonify({"message": "Failed to read resume data from database. It may be corrupted."}), 500
        except Exception as e:
            return jsonify({"message": f"Error parsing resume JSON: {str(e)}"}), 500
        # --- END OF UPDATED SECTION ---


        # 5. Perform the TF-IDF and Cosine Similarity
        corpus = [resume_text, job_description]
        vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Calculate cosine similarity
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        # 6. Extract Keywords
        feature_names = np.array(vectorizer.get_feature_names_out())
        
        # Get the tf-idf vectors for resume and job description
        resume_vec = tfidf_matrix[0].toarray().flatten()
        jd_vec = tfidf_matrix[1].toarray().flatten()

        # Get indices of words with non-zero tf-idf score (using a small threshold)
        resume_keywords = set(feature_names[resume_vec > 0.1])
        jd_keywords = set(feature_names[jd_vec > 0.1]) # Get important words from JD

        matched_keywords = sorted(list(resume_keywords.intersection(jd_keywords)))
        missing_keywords = sorted(list(jd_keywords.difference(resume_keywords)))

        # 7. Return the results
        return jsonify({
            "score": float(score), # Ensure score is a JSON-friendly float
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords
        }), 200

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500