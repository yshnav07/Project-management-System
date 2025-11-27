import random
import textstat
import math

def detect_ai_usage(text: str) -> float:
    if not text or not text.strip():
        return 0.0

    try:
        readability = textstat.flesch_reading_ease(text)
    except Exception:
        readability = 0

    try:
        complexity = textstat.sentence_count(text)
    except Exception:
        complexity = 0

    score = 0

    if readability > 60 and not math.isnan(readability):
        score += 30
    if complexity > 10:
        score += 30
    if len(text.split()) > 100:
        score += 20

    score += random.randint(0, 20)

    return float(min(score, 100))
