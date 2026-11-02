"""Content-based event recommendations with a popularity fallback."""

from sqlalchemy import func

from ..extensions import db
from ..models import Event, Registration
from ..timeutils import now_local


def recommend_events(student, limit=6):
    """Return (events, method_label).

    The profile combines declared interests and categories from previous
    registrations. TF-IDF/cosine similarity is used when scikit-learn is
    available and a profile can be built. Otherwise, popular upcoming events
    are returned as the documented cold-start fallback.
    """
    registered_ids = {
        registration.event_id
        for registration in student.registrations
        if registration.status == "registered"
    }
    candidates = Event.query.filter(
        Event.is_published.is_(True), Event.starts_at > now_local()
    ).all()
    candidates = [event for event in candidates if event.id not in registered_ids]
    if not candidates:
        return [], "No upcoming events available"

    interest_terms = [part.strip().lower() for part in (student.interests or "").split(",") if part.strip()]
    history_categories = [
        registration.event.category.lower()
        for registration in student.registrations
        if registration.status == "registered"
        and registration.event is not None
        and registration.attendance is not None
    ]
    profile_terms = interest_terms + history_categories

    if profile_terms:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            profile_text = " ".join(profile_terms)
            event_texts = [
                f"{event.event_name} {event.category} {event.description}" for event in candidates
            ]
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            matrix = vectorizer.fit_transform([profile_text] + event_texts)
            scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            ranked = sorted(zip(scores, candidates), key=lambda item: (item[0], item[1].starts_at), reverse=True)
            matching = [event for score, event in ranked if score > 0]
            if matching:
                return matching[:limit], "Matched to your interests and participation history"
        except (ImportError, ValueError):
            # Empty vocabularies and missing optional ML dependencies fall back safely.
            pass

    popularity = dict(
        db.session.query(Registration.event_id, func.count(Registration.id))
        .filter(Registration.status == "registered")
        .group_by(Registration.event_id)
        .all()
    )
    candidates.sort(key=lambda event: (popularity.get(event.id, 0), event.starts_at), reverse=True)
    return candidates[:limit], "Popular upcoming events (recommended when there is not enough history)"
