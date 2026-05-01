# SaveAlife with IBM

**AI-coordinated trauma response — built solo with IBM Bob**

An intelligent trauma response system for road accidents that uses IBM watsonx.ai (Granite 3 Instruct) to triage accident reports, provide first-aid guidance, and coordinate with nearby hospitals, pharmacies, and blood banks.

Built for the IBM Bob Dev Day Hackathon — demonstrating how Bob accelerates integration of diverse healthcare data sources.

## Features

- 🚨 **Instant Triage**: AI agents assess accident severity from bystander reports
- 🏥 **Smart Coordination**: Automatically alerts appropriate healthcare facilities
- 💊 **Resource Matching**: Finds nearby pharmacies and blood banks based on needs
- 🔌 **Flexible Data Integration**: Adapter pattern handles CSV, JSON, and unstructured text sources

## Tech Stack

- **Frontend**: Streamlit
- **AI/LLM**: IBM watsonx.ai (Granite 3 Instruct) via ibm-watsonx-ai SDK
- **Data Processing**: pandas
- **Configuration**: python-dotenv

## Setup

### Prerequisites

- Python 3.11 or higher
- IBM watsonx.ai account with API credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IBM_HACKATHON
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your IBM watsonx.ai credentials
# WATSONX_API_KEY=your_api_key_here
# WATSONX_PROJECT_ID=your_project_id_here
# WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

5. Run the application:
```bash
streamlit run app.py
```

## Project Structure

```
IBM_HACKATHON/
├── app.py                    # Streamlit UI entry point
├── pipeline.py               # Agent orchestration
├── config.py                 # Configuration constants
├── prompts.py                # LLM prompt templates
├── agents/                   # AI agent modules
├── data_sources/             # Data adapter pattern
├── data/                     # Sample facility data
└── utils/                    # Utility modules
```

## License

MIT License - Built for IBM Bob Dev Day Hackathon 2026