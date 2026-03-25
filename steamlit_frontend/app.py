import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api/v1/analyze/combined"

st.set_page_config(page_title="Citizen Complaint Prioritization System", page_icon="🏙️", layout="centered")

# Initialize session state
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "street" not in st.session_state:
    st.session_state.street = ""
if "area" not in st.session_state:
    st.session_state.area = ""
if "postal_code" not in st.session_state:
    st.session_state.postal_code = ""
if "latitude" not in st.session_state:
    st.session_state.latitude = 17.3850
if "longitude" not in st.session_state:
    st.session_state.longitude = 78.4867

st.title("🏙️ Citizen Complaint Prioritization System")
st.write("Upload a civic complaint image and get category, severity, ward, and priority automatically.")

# Add another complaint button (always visible; enabled after successful submission)
col1, col2 = st.columns([0.65, 0.35])
with col2:
    add_another = st.button(
        "➕ Add Another",
        disabled=not st.session_state.submitted
    )

if add_another:
    st.session_state.submitted = False
    st.session_state.last_result = None
    st.session_state.street = ""
    st.session_state.area = ""
    st.session_state.postal_code = ""
    st.session_state.latitude = 17.3850
    st.session_state.longitude = 78.4867
    # Recreate uploader widget to clear selected file
    st.session_state.uploader_key += 1
    st.rerun()

st.divider()

# -------------------------
# Upload image
# -------------------------
uploaded_file = st.file_uploader(
    "📷 Upload complaint image",
    type=["png", "jpg", "jpeg"],
    key=f"complaint_uploader_{st.session_state.uploader_key}"
)

# Preview
if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Complaint Image", use_container_width=True)

st.subheader("📍 Location Details")

street = st.text_input("Street", placeholder="e.g., Road No 10", key="street")
area = st.text_input("Area / Locality", placeholder="e.g., Kukatpally", key="area")
postal_code = st.text_input("Postal Code", placeholder="e.g., 500072", key="postal_code")

col1, col2 = st.columns(2)
with col1:
    latitude = st.number_input("Latitude", format="%.6f", key="latitude")
with col2:
    longitude = st.number_input("Longitude", format="%.6f", key="longitude")

st.divider()

submit = st.button("🚀 Submit Complaint", use_container_width=True, type="primary")


def render_result(result: dict) -> None:
    """Render analysis output from API response."""
    st.success("✅ Complaint analyzed successfully!")

    ward_no = result.get("ward_no")
    if ward_no:
        st.info(f"🏢 Ward Number: {ward_no}")

    st.subheader("🔥 Priority Result")
    st.write(f"**Priority Label:** {result.get('priority_label')}")
    st.write(f"**Priority Score:** {result.get('priority_score')} / 100")
    st.write(f"**Urgency Score:** {result.get('urgency_score')} / 100")

    st.divider()

    st.subheader("🧾 Detected Issues")
    issues = result.get("detected_issues", [])

    if not issues:
        st.warning("No issues detected.")
    else:
        for i, issue in enumerate(issues, 1):
            st.markdown(f"### Issue {i}")
            st.write(f"**Category:** {issue.get('category')}")
            st.write(f"**Department:** {issue.get('department')}")
            st.write(f"**Severity:** {issue.get('severity')}")
            st.divider()

    with st.expander("🔍 View Raw JSON Response"):
        st.json(result)


if st.session_state.last_result:
    render_result(st.session_state.last_result)

if submit:
    if uploaded_file is None:
        st.error("❌ Please upload an image.")
    elif not street or not area or not postal_code:
        st.error("❌ Please fill Street, Area, and Postal Code.")
    else:
        with st.spinner("Analyzing complaint... please wait ⏳"):
            try:
                files = {
                    "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                }

                data = {
                    "street": street,
                    "area": area,
                    "postal_code": postal_code,
                    "latitude": str(latitude),
                    "longitude": str(longitude)
                }

                res = requests.post(API_URL, files=files, data=data, timeout=120)

                if res.status_code != 200:
                    st.error(f"Backend error: {res.status_code}")
                    st.text(res.text)
                else:
                    result = res.json()

                    if not result.get("is_valid"):
                        st.session_state.submitted = False
                        st.session_state.last_result = None
                        st.error("❌ Complaint analysis failed")
                        st.json(result)
                    else:
                        st.session_state.last_result = result
                        st.session_state.submitted = True
                        st.rerun()

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
