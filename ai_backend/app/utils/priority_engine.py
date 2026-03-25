def category_weight(category: str) -> int:
    c = (category or "").lower()

    if "fire" in c:
        return 80

    if "sewage" in c or "overflow" in c:
        return 60

    if "garbage" in c or "waste" in c or "trash" in c:
        return 50

    if "water" in c or "leak" in c:
        return 55
    if "electric" in c or "wire" in c:
        return 45


    if "pothole" in c or "road" in c:
        return 45

    # ✅ IMPORTANT FIX
    if "drain" in c or "drainage" in c or "manhole" in c:
        return 50

    return 25

 
def severity_weight(severity: str) -> int:
     s = (severity or "").lower()
     if "high" in s:
         return 35
     if "medium" in s:
         return 20
     if "low" in s:
         return 10
     return 15

def priority_label(score: int) -> str:
    if score >= 90:
        return "Emergency"
    elif score >= 75:
        return "High"
    elif score >= 60:
        return "Medium"
    else:
        return "Low"
def compute_scores(category: str, severity: str):
    base = category_weight(category) + severity_weight(severity)

    urgency_score = min(base, 100)
    priority_score = min(base, 100)

    return urgency_score, priority_score, priority_label(priority_score)