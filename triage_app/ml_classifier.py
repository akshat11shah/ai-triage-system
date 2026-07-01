import os
import joblib
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.neighbors import NearestNeighbors
from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'fallback_model.pkl')

def train_fallback_model():
    """Trains a Random Forest classifier on historical TriageResult data."""
    from triage_app.models import TriageResult
    
    results = TriageResult.objects.select_related('message').all()
    if len(results) < 5:
        logger.info("Not enough data to train ML model. Need at least 5 records.")
        return False
        
    texts = []
    y_cat = []
    y_pri = []
    y_human = []
    summaries = []
    actions = []
    
    for r in results:
        texts.append(r.message.text)
        y_cat.append(r.final_category)
        y_pri.append(r.final_priority)
        y_human.append(str(r.final_needs_human))
        # Safely extract historical text for k-NN retrieval
        summaries.append(r.final_summary if r.final_summary else "No historical summary available.")
        actions.append(r.final_suggested_action if r.final_suggested_action else "Review manually.")
        
    # Build NLP pipelines for discrete classification
    pipe_cat = Pipeline([('tfidf', TfidfVectorizer(max_features=1000)), ('clf', RandomForestClassifier(n_estimators=50))])
    pipe_pri = Pipeline([('tfidf', TfidfVectorizer(max_features=1000)), ('clf', RandomForestClassifier(n_estimators=50))])
    pipe_human = Pipeline([('tfidf', TfidfVectorizer(max_features=1000)), ('clf', RandomForestClassifier(n_estimators=50))])
    
    logger.info(f"Training ML models on {len(texts)} records...")
    pipe_cat.fit(texts, y_cat)
    pipe_pri.fit(texts, y_pri)
    pipe_human.fit(texts, y_human)
    
    # Build k-NN Vectorizer for dynamic text retrieval
    nn_tfidf = TfidfVectorizer(max_features=1000)
    X_tfidf = nn_tfidf.fit_transform(texts)
    nn_model = NearestNeighbors(n_neighbors=1, metric='cosine')
    nn_model.fit(X_tfidf)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    model_bundle = {
        'category_model': pipe_cat,
        'priority_model': pipe_pri,
        'human_model': pipe_human,
        'nn_tfidf': nn_tfidf,
        'nn_model': nn_model,
        'historical_summaries': summaries,
        'historical_actions': actions
    }
    
    joblib.dump(model_bundle, MODEL_PATH)
    logger.info("ML Fallback models trained and saved successfully.")
    return True

def predict_fallback(text):
    """Predicts categorization using the local ML models if the Groq API fails."""
    if not os.path.exists(MODEL_PATH):
        return None
        
    try:
        model_bundle = joblib.load(MODEL_PATH)
        cat = model_bundle['category_model'].predict([text])[0]
        pri = model_bundle['priority_model'].predict([text])[0]
        human_str = model_bundle['human_model'].predict([text])[0]
        
        needs_human = human_str == 'True'
        
        # k-NN Dynamic Text Retrieval
        dyn_summary = "[ML Fallback] Predicted based on historical database patterns."
        dyn_action = "Manually review (Predicted by local ML model)."
        
        nn_tfidf = model_bundle.get('nn_tfidf')
        nn_model = model_bundle.get('nn_model')
        hist_summaries = model_bundle.get('historical_summaries', [])
        hist_actions = model_bundle.get('historical_actions', [])
        
        if nn_model and nn_tfidf and hist_summaries and hist_actions:
            try:
                vec = nn_tfidf.transform([text])
                distances, indices = nn_model.kneighbors(vec)
                best_idx = indices[0][0]
                dyn_summary = f"[ML Fallback] {hist_summaries[best_idx]}"
                dyn_action = f"{hist_actions[best_idx]}"
            except Exception as e:
                logger.error(f"k-NN retrieval failed: {e}")
        
        return {
            "category": cat,
            "priority": pri,
            "summary": dyn_summary,
            "suggested_action": dyn_action,
            "needs_human": needs_human,
            "confidence": 0.85
        }
    except Exception as e:
        logger.error(f"Error predicting with ML model: {e}")
        return None
