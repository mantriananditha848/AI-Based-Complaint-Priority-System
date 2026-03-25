from app.services.severity_model_loader import get_severity_model
def predict_severity(image_path: str, category: str):

    # Rule: Electric hazard always high
    if category == "Electric wire hazard":
        return "High"

    model = get_severity_model(category)

    if model is None:
        return "Medium"

    results = model(image_path)

    probs = results[0].probs.data
    names = results[0].names

    severity = names[int(probs.argmax())]

    return severity