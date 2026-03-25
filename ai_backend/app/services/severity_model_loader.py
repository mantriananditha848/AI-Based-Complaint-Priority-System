from ultralytics import YOLO

# Load models once when server starts
garbage_model = YOLO("app/models/best_garbage.pt")
road_model = YOLO("app/models/best_road.pt")
water_model = YOLO("app/models/best_water.pt")


def get_severity_model(category: str):

    if category == "Garbage/Waste accumulation":
        return garbage_model

    elif category == "Potholes/Road damage":
        return road_model

    elif category in [
        "Water leakage",
        "Drainage overflow",
        "Manholes/drainage opening damage"
    ]:
        return water_model

    return None