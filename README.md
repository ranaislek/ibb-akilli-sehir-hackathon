# ibb-hackathon-2025
Yapay Zeka Destekli Başvuru Takip Platformu
=======
# İstanBuilders Complaint Classification System

A machine learning system for classifying Turkish municipal complaints using semantic similarity and storing data in PostgreSQL with pgvector for vector similarity search.

## Features

- **Complaint Classification**: Classifies complaints into 12 categories using Turkish BERT model
- **Vector Database**: Stores complaint embeddings in PostgreSQL with pgvector extension
- **Similarity Search**: Fast semantic search for similar complaints
- **Performance Analysis**: Comprehensive evaluation metrics and visualizations

## Categories

1. su_kanalizasyon (Water & Sewage)
2. atik_yonetimi (Waste Management)
3. temizlik (Cleaning)
4. ulasim_trafik (Transportation & Traffic)
5. yol_altyapi (Road & Infrastructure)
6. yesil_alan_bahce (Green Areas & Gardens)
7. aydinlatma (Lighting)
8. sosyal_yardim (Social Assistance)
9. fatura_odeme (Bills & Payments)
10. basvuru_ruhsat (Applications & Permits)
11. sikayet_takip (Complaint Tracking)
12. dijital_sistem (Digital Systems)

## Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Conda/Miniconda

### 1. Start PostgreSQL with pgvector

```bash
docker-compose up -d
```

This will start a PostgreSQL 16 container with pgvector extension on port 5432.

### 2. Install Python Dependencies

```bash
pip install -q sentence-transformers transformers scikit-learn pandas matplotlib seaborn numpy psycopg2-binary pgvector
```

### 3. Run the Notebook

Open `istanbuilders_final.ipynb` and run all cells in order:

1. **Cell 1**: Install dependencies
2. **Cell 2**: Import libraries
3. **Cell 3**: Define complaint templates
4. **Cell 4**: Load Turkish BERT model
5. **Cell 5**: Build template embeddings
6. **Cell 6**: Define classification function
7. **Cell 7**: Load data from CSV files
8. **Database cells**: Connect to PostgreSQL, create tables, store data
9. **Cell 8**: Run predictions and analysis
10. **Cell 9**: Generate confusion matrix and visualizations
11. **Cell 10**: Save results to CSV

## Database Schema

### departments
- `department_id` (PRIMARY KEY)
- `category_name`
- `description`

### complaints
- `ticket_id` (PRIMARY KEY)
- `complaint_text`
- `department_id` (FOREIGN KEY)
- `predicted_category`
- `prediction_confidence`
- `created_at`

### complaint_embeddings
- `id` (PRIMARY KEY)
- `ticket_id` (FOREIGN KEY)
- `embedding` (vector(768))
- `created_at`

## Vector Similarity Search

The system uses pgvector's cosine similarity operator (`<=>`) for fast semantic search:

```python
search_similar_complaints("Sokakta çöp konteynerleri dolu", model, top_k=5)
```

## Model

Uses Turkish BERT model: `emrecan/bert-base-turkish-cased-mean-nli-stsb-tr`
- Embedding dimension: 768
- Optimized for Turkish sentence embeddings

## Database Configuration

Default configuration (can be changed in `docker-compose.yml`):
- Host: `localhost`
- Port: `5432`
- Database: `complaints_db`
- User: `istanbuilders`
- Password: `istanbuilders123`

## Stopping the Database

```bash
docker-compose down
```

To remove volumes as well:
```bash
docker-compose down -v
```

## Files

- `istanbuilders_final.ipynb` - Main notebook
- `docker-compose.yml` - PostgreSQL + pgvector setup
- `data/complaints.csv` - Sample complaints data
- `data/departments.csv` - Department categories
- `prediction_results.csv` - Classification results (generated)
- `category_performance.csv` - Performance metrics (generated)
- `wrong_predictions.csv` - Misclassified complaints (generated)
>>>>>>> 7779c6e (oley bitti)
