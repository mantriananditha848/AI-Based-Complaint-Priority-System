def override_severity(category: str, severity: str) -> str:
    c = (category or "").lower()
    s = (severity or "Medium").capitalize()

    # Strong civic overrides
    if "sewage" in c:
        return "High"

    if "electric" in c or "wire" in c:
        return "High"

    if "fire" in c or "smoke" in c:
        return "High"

    if "garbage" in c or "waste" in c:
        # garbage is usually at least medium
        if s == "Low":
            return "Medium"
        return s

    if "pothole" in c or "road" in c:
        # potholes mostly medium
        if s == "High":
            return "Medium"
        return s

    if "street light" in c:
        if s == "High":
            return "Medium"
        return s

    return s
