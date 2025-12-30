import streamlit as st
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Page config
st.set_page_config(
    page_title="İBB Çözüm Merkezi",
    page_icon="🏛️",
    layout="wide"
)

# Custom CSS for İBB blue color theme
st.markdown("""
<style>
    /* White background */
    .stApp {
        background-color: white;
    }
    /* Blue header/navbar area */
    header[data-testid="stHeader"] {
        background-color: #093b84 !important;
    }
    /* Main content area */
    .main .block-container {
        background-color: white;
        padding: 2rem;
    }
    /* Title and headers in blue */
    h1, h2, h3 {
        color: #093b84 !important;
    }
    /* All text elements in blue */
    p, label, .stMarkdown, .stText, div[data-testid="stMarkdownContainer"] {
        color: #093b84 !important;
    }
    /* Selectbox labels and text */
    .stSelectbox label, .stTextInput label, .stTextArea label {
        color: #093b84 !important;
    }
    /* Blue buttons */
    .stButton>button {
        background-color: #093b84;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #072d66;
        color: white;
    }
    /* Form submit button */
    .stForm button[kind="primary"],
    .stForm button[type="submit"] {
        background-color: #f0f0f0 !important;
        border-color: #093b84 !important;
        color: #093b84 !important;
        font-weight: bold !important;
    }
    .stForm button[kind="primary"]:hover,
    .stForm button[type="submit"]:hover {
        background-color: #e0e0e0 !important;
        border-color: #093b84 !important;
        color: #093b84 !important;
    }
    /* Override any default button styles */
    button[data-testid="stFormSubmitButton"] > button {
        background-color: #f0f0f0 !important;
        border-color: #093b84 !important;
        color: #093b84 !important;
    }
    button[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #e0e0e0 !important;
        border-color: #093b84 !important;
        color: #093b84 !important;
    }
    /* Light gray dropdowns and input boxes */
    .stSelectbox [data-baseweb="select"] > div {
        background-color: #f0f0f0 !important;
        border-color: #093b84 !important;
    }
    .stTextInput input, .stTextArea textarea {
        background-color: #f0f0f0 !important;
        border-color: #093b84 !important;
    }
    .stSelectbox [data-baseweb="select"] {
        border-color: #093b84 !important;
    }
    /* Text color inside boxes - İBB blue */
    .stTextInput input, .stTextArea textarea {
        color: #093b84 !important;
    }
    .stTextInput input:disabled {
        color: #093b84 !important;
        -webkit-text-fill-color: #093b84 !important;
    }
    /* Placeholder text in blue */
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #093b84 !important;
        opacity: 0.7;
    }
    .stSelectbox [data-baseweb="select"] div {
        color: #093b84 !important;
    }
    /* Dropdown menu options - light gray */
    [data-baseweb="popover"] {
        background-color: #f0f0f0 !important;
    }
    [data-baseweb="menu"] {
        background-color: #f0f0f0 !important;
    }
    [role="option"] {
        background-color: #f0f0f0 !important;
        color: #093b84 !important;
    }
    [role="option"]:hover {
        background-color: #e0e0e0 !important;
    }
    .stSelectbox [data-baseweb="select"]:focus-within {
        border-color: #093b84 !important;
    }
    /* Sidebar if exists */
    [data-testid="stSidebar"] {
        background-color: #093b84;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='complaints_db',
        user='istanbuilders',
        password='istanbuilders123'
    )

# Load model
@st.cache_resource
def load_model():
    return SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')

# Get Istanbul districts from database
@st.cache_data(ttl=3600)
def get_istanbul_districts():
    """Get all Istanbul districts from pk_ilce table"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ilce_adi, lat, lng
        FROM pk_ilce
        WHERE il_id = 34
        ORDER BY ilce_adi
    """)
    districts = cur.fetchall()
    cur.close()
    return {d[0]: (d[1], d[2]) for d in districts}

# Get neighborhoods from database
def get_neighborhoods_for_district(district):
    """Get neighborhoods for a district from pk_mahalle table"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT mahalle_adi
        FROM pk_mahalle
        WHERE ilce_adi = %s
        ORDER BY mahalle_adi
    """, (district,))
    neighborhoods = [row[0] for row in cur.fetchall()]
    cur.close()
    # Return district center as fallback if no neighborhoods found
    return neighborhoods if neighborhoods else [district + ' Merkez']

# Get neighborhood coordinates from database
def get_neighborhood_coordinates(district, neighborhood):
    """Get coordinates for a specific neighborhood"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT lat, lng
            FROM pk_mahalle
            WHERE ilce_adi = %s AND mahalle_adi = %s
        """, (district, neighborhood))
        result = cur.fetchone()
        cur.close()
        # Check if we have valid coordinates (not NULL)
        if result and result[0] is not None and result[1] is not None:
            return result[0], result[1]
    except:
        pass
    # Fallback to district center
    districts = get_istanbul_districts()
    return districts.get(district, (41.0082, 28.9784))

# Get next complaint ID
def get_next_complaint_id():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(complaint_id) FROM complaints")
        result = cur.fetchone()[0]
        cur.close()
        return (result + 1) if result else 1
    except Exception as e:
        st.error(f"Complaint ID alınamadı: {e}")
        return 1

# Classify complaint
def classify_complaint(complaint_text, model):
    """Classify complaint using similarity to existing complaints"""
    try:
        import json
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get random sample of existing complaints
        cur.execute("""
            SELECT ce.embedding, c.final_category
            FROM complaint_embeddings ce
            JOIN complaints c ON ce.complaint_id = c.complaint_id
            WHERE c.final_category != 'diğer'
            ORDER BY RANDOM()
            LIMIT 100
        """)
        
        samples = cur.fetchall()
        cur.close()
        
        if not samples:
            return 'diğer', 0.0
        
        # Encode new complaint
        new_embedding = model.encode([complaint_text])[0]
        
        # Build embeddings matrix properly
        sample_embeddings = []
        categories = []
        
        for embedding, category in samples:
            # Parse embedding - it might be stored as string/JSON
            if isinstance(embedding, str):
                try:
                    emb_array = np.array(json.loads(embedding), dtype=np.float32)
                except:
                    continue
            elif isinstance(embedding, (list, tuple)):
                emb_array = np.array(embedding, dtype=np.float32)
            elif isinstance(embedding, np.ndarray):
                emb_array = embedding.astype(np.float32)
            else:
                continue  # Skip invalid embeddings
            
            # Ensure it's 1D with correct length
            if emb_array.ndim == 1 and len(emb_array) == 768:
                sample_embeddings.append(emb_array)
                categories.append(category)
        
        if not sample_embeddings:
            return 'diğer', 0.0
        
        # Stack embeddings into 2D array (n_samples, 768)
        sample_embeddings = np.vstack(sample_embeddings)
        
        # Calculate cosine similarities
        similarities = np.dot(sample_embeddings, new_embedding) / (
            np.linalg.norm(sample_embeddings, axis=1) * np.linalg.norm(new_embedding)
        )
        
        # Get best match
        best_idx = np.argmax(similarities)
        predicted_category = categories[best_idx]
        confidence = float(similarities[best_idx])
        
        return predicted_category, confidence
        
    except Exception as e:
        st.error(f"Sınıflandırma hatası: {e}")
        return 'diğer', 0.0

# Save complaint to database
def save_complaint(complaint_id, complaint_text, district, neighborhood, latitude, longitude, 
                   predicted_category, confidence, final_category, model):
    """Save complaint and its embedding to database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get department_id
        cur.execute("""
            SELECT department_id FROM departments 
            WHERE category_name = %s
        """, (final_category,))
        result = cur.fetchone()
        department_id = result[0] if result else None
        
        # Insert complaint
        cur.execute("""
            INSERT INTO complaints (
                complaint_id, complaint_text, department_id, 
                district, neighborhood, latitude, longitude,
                predicted_category, prediction_confidence, final_category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            complaint_id, complaint_text, department_id,
            district, neighborhood, latitude, longitude,
            predicted_category, confidence, final_category
        ))
        
        # Generate and save embedding
        embedding = model.encode([complaint_text])[0]
        embedding_list = embedding.tolist()
        
        cur.execute("""
            INSERT INTO complaint_embeddings (complaint_id, embedding)
            VALUES (%s, %s)
        """, (complaint_id, embedding_list))
        
        conn.commit()
        cur.close()
        
    except Exception as e:
        conn.rollback()
        raise e

# Main UI
st.title("🏛️ İBB Çözüm Merkezi")
st.subheader("Vatandaş Başvuru Portalı")

st.markdown("---")

# Get districts from database
district_coords = get_istanbul_districts()

# District selection outside form for dynamic neighborhood update
st.write("### 📝 Yeni Başvuru")

col1, col2 = st.columns(2)

with col1:
    # District selection
    district = st.selectbox(
        "İlçe Seçiniz",
        options=sorted(list(district_coords.keys())),
        key="district"
    )

with col2:
    # Neighborhood selection based on district - updates dynamically
    neighborhoods = get_neighborhoods_for_district(district)
    neighborhood = st.selectbox(
        "Mahalle Seçiniz",
        options=neighborhoods,
        key="neighborhood"
    )

# Get neighborhood coordinates from database
coords = get_neighborhood_coordinates(district, neighborhood)

# Show coordinates (updates dynamically)
st.text_input("📍 Konum (Enlem, Boylam)", 
              value=f"{coords[0]:.6f}, {coords[1]:.6f}", 
              disabled=True)

# Complaint form
with st.form("complaint_form"):
    # Complaint text
    complaint_text = st.text_area(
        "Başvuru Açıklaması",
        placeholder="Lütfen başvurunuzu detaylı bir şekilde açıklayınız...",
        height=200,
        key="complaint_text"
    )
    
    # Submit button
    submit = st.form_submit_button("📤 Başvuruyu Gönder", use_container_width=True)
    
    if submit:
        if not complaint_text or len(complaint_text.strip()) < 10:
            st.error("⚠️ Lütfen en az 10 karakter uzunluğunda bir açıklama giriniz.")
        else:
            with st.spinner("İşleminiz yapılıyor..."):
                try:
                    # Get next complaint ID
                    complaint_id = get_next_complaint_id()
                    
                    # Classify complaint
                    model = load_model()
                    predicted_category, confidence = classify_complaint(complaint_text, model)
                    
                    # Determine final category
                    final_category = predicted_category if confidence >= 0.34 else 'diğer'
                    
                    # Save to database
                    save_complaint(
                        complaint_id=complaint_id,
                        complaint_text=complaint_text,
                        district=district,
                        neighborhood=neighborhood,
                        latitude=coords[0],
                        longitude=coords[1],
                        predicted_category=predicted_category,
                        confidence=confidence,
                        final_category=final_category,
                        model=model
                    )
                    
                    st.success(f"✅ Başvurunuz başarıyla kaydedildi!")
                    st.info(f"**Başvuru Numaranız:** #{complaint_id}")
                    
                    if final_category != 'diğer':
                        st.success(f"**Kategori:** {final_category}")
                        st.info(f"**Güven Skoru:** {confidence:.2%}")
                        st.info(f"Başvurunuz **{final_category}** departmanına yönlendirildi.")
                    else:
                        st.warning(f"**Kategori:** Manuel İnceleme Gerekli")
                        st.info(f"**Güven Skoru:** {confidence:.2%}")
                        st.info("Başvurunuz manuel inceleme için **diğer** kategorisine yönlendirildi.")
                    
                except Exception as e:
                    st.error(f"❌ Hata oluştu: {e}")
