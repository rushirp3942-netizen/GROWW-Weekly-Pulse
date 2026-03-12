import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class GroqAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY in .env file.")
        self.client = Groq(api_key=self.api_key)

    def analyze_reviews(self, reviews_data):
        """
        Groups reviews into themes, extracts quotes, and generates action ideas.
        Follows the architecture for 'GROWW Weekly Pulse'.
        """
        # Select a representative sample (latest, highest impact, and mixed sentiment)
        # We'll take the latest 150 reviews to stay within token limits while being comprehensive.
        sample_size = min(len(reviews_data), 150)
        reviews_for_ai = [
            f"ID: {r.get('review_id')} | Rating: {r['rating']} | Content: {r['content']}" 
            for r in reviews_data[:sample_size]
        ]
        reviews_text = "\n---\n".join(reviews_for_ai)

        prompt = f"""
        You are an expert product analyst at GROWW. Your task is to transform {sample_size} user reviews into a high-impact 'Weekly Pulse' report.
        
        Input Data:
        {reviews_text}
        
        Required Tasks:
        1. Theme Generation: Identify 3-5 recurring themes (pain points, feature requests, or praise).
        2. Review Sorting: For each theme, provide a concise summary of what users are saying.
        3. Sentiment Analysis: Determine if the overall sentiment for each theme is Positive, Negative, or Neutral.
        4. User Voices: Extract 3 verbatim quotes that are most representative of the general sentiment.
        5. Growth Roadmap: Generate 3 actionable ideas for the Product/Growth teams.

        Response Format (Strict JSON):
        {{
            "pulse_summary": "A 2-sentence executive summary of this week's app health.",
            "themes": [
                {{
                    "name": "Theme Title",
                    "description": "Elaborate on what users are specifically experiencing under this theme.",
                    "sentiment": "Positive/Negative/Neutral",
                    "impact_score": 1-10
                }}
            ],
            "top_quotes": [
                "Quote 1",
                "Quote 2",
                "Quote 3"
            ],
            "action_ideas": [
                "Strategic Idea 1",
                "Strategic Idea 2",
                "Strategic Idea 3"
            ]
        }}
        
        Strict Guidelines:
        - DO NOT include any PII (names, phone numbers, emails).
        - If a quote contains PII, redact it (e.g., [Name]).
        - Output ONLY the raw JSON.
        """

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional Product Analyst at a top fintech company."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(completion.choices[0].message.content)

if __name__ == "__main__":
    # Example usage (requires GROQ_API_KEY)
    try:
        # Looking for reviews.json in the parent (root) directory
        with open('../reviews.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analyzer = GroqAnalyzer()
        report = analyzer.analyze_reviews(data)
        
        with open('pulse_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
            
        print("Pulse report generated and saved to pulse_report.json")
    except Exception as e:
        print(f"Error: {e}")
