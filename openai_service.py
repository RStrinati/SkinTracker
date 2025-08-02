import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4"  # Use GPT-4 for better analysis

    async def generate_summary(self, user_logs: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate a weekly summary of user's skin health progress."""
        try:
            # Prepare data for analysis
            summary_data = self._prepare_logs_for_analysis(user_logs)
            
            prompt = f"""
As a skin health expert, analyze the following week's skin health data and provide insights:

{summary_data}

Please provide:
1. Overall skin health trends
2. Product effectiveness insights
3. Trigger pattern analysis
4. Symptom severity changes
5. Personalized recommendations

Keep the response friendly, encouraging, and actionable. Use emojis appropriately.
Limit response to 300-400 words.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful skin health analyst who provides personalized insights based on user data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content
            logger.info("Generated skin health summary")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "I couldn't generate your summary right now. Please try again later."

    async def analyze_photo(self, photo_url: str) -> str:
        """Analyze skin photo for basic observations."""
        try:
            # Note: This is a simplified analysis since GPT-4 Vision is needed for actual photo analysis
            # For now, we'll provide a general analysis prompt
            
            prompt = """
Based on the uploaded skin photo, provide a brief, encouraging analysis focusing on:
1. General skin appearance observations
2. Areas to monitor
3. Photography tips for next time
4. Positive reinforcement

Keep it supportive and professional. Limit to 100-150 words.
Remember: This is not medical advice, just general observations for tracking purposes.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a supportive skin health tracker assistant. Provide general, non-medical observations about skin photos."},
                    {"role": "user", "content": f"Analyze this skin photo URL: {photo_url}\n\n{prompt}"}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
            logger.info("Generated photo analysis")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing photo: {e}")
            return "Photo uploaded successfully! Continue tracking for personalized insights."

    async def analyze_ingredients(
        self, product_name: str, ingredients: List[str], conditions: List[str]
    ) -> str:
        """Check ingredient list against user conditions."""
        try:
            ingredient_list = ", ".join(ingredients)
            condition_list = ", ".join(conditions) or "none"
            prompt = (
                f"Product: {product_name}\n"
                f"Ingredients: {ingredient_list}\n"
                f"User conditions: {condition_list}\n\n"
                "List any ingredients that might conflict with the user's conditions."
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skincare ingredient checker."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.0,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing ingredients: {e}")
            return "Unable to analyze ingredients right now."

    async def answer_skin_question(self, question: str, user_logs: Dict[str, List[Dict[str, Any]]]) -> str:
        """Answer user questions about their skin health based on their data."""
        try:
            # Prepare user data context
            context_data = self._prepare_logs_for_analysis(user_logs)
            
            prompt = f"""
User question: {question}

User's recent skin health data:
{context_data}

As a skin health assistant, provide a helpful, personalized answer based on their data.
Keep it friendly, supportive, and actionable. Include relevant insights from their tracking data.
Limit response to 200-250 words.

Important: This is for tracking purposes only, not medical advice.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful skin health tracking assistant. Answer questions based on user data while being supportive and informative."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logger.info("Generated answer to user question")
            return answer
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return "I couldn't answer your question right now. Please try again later."

    async def generate_product_recommendations(self, user_logs: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate product recommendations based on user's tracking data."""
        try:
            # Analyze user's product usage and symptom patterns
            context_data = self._prepare_logs_for_analysis(user_logs)
            
            prompt = f"""
Based on this user's skin health tracking data, suggest improvements to their skincare routine:

{context_data}

Provide:
1. Products that seem to be working well
2. Potential products to consider adding
3. Products that might be causing issues
4. General routine recommendations

Keep suggestions gentle and encouraging. Limit to 250-300 words.
Remember: These are general suggestions, not medical advice.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skincare routine analyst who provides gentle, data-driven suggestions based on user tracking patterns."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                temperature=0.7
            )
            
            recommendations = response.choices[0].message.content
            logger.info("Generated product recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return "I couldn't generate recommendations right now. Please try again later."

    def _prepare_logs_for_analysis(self, user_logs: Dict[str, List[Dict[str, Any]]]) -> str:
        """Prepare user logs data for AI analysis."""
        try:
            analysis_data = {
                "summary": {
                    "total_products_logged": len(user_logs.get('products', [])),
                    "total_triggers_logged": len(user_logs.get('triggers', [])),
                    "total_symptoms_logged": len(user_logs.get('symptoms', [])),
                    "total_photos_logged": len(user_logs.get('photos', []))
                },
                "products": [],
                "triggers": [],
                "symptoms": [],
                "photos": []
            }
            
            # Process products
            for product in user_logs.get('products', []):
                analysis_data['products'].append({
                    'name': product.get('product_name'),
                    'date': product.get('logged_at')
                })
            
            # Process triggers
            for trigger in user_logs.get('triggers', []):
                analysis_data['triggers'].append({
                    'name': trigger.get('trigger_name'),
                    'date': trigger.get('logged_at')
                })
            
            # Process symptoms
            for symptom in user_logs.get('symptoms', []):
                analysis_data['symptoms'].append({
                    'name': symptom.get('symptom_name'),
                    'severity': symptom.get('severity'),
                    'date': symptom.get('logged_at')
                })
            
            # Process photos (just count and dates for privacy)
            for photo in user_logs.get('photos', []):
                analysis_data['photos'].append({
                    'date': photo.get('logged_at'),
                    'has_analysis': bool(photo.get('ai_analysis'))
                })
            
            # Calculate patterns
            product_counts = {}
            trigger_counts = {}
            symptom_severities = {}
            
            for product in analysis_data['products']:
                name = product['name']
                product_counts[name] = product_counts.get(name, 0) + 1
            
            for trigger in analysis_data['triggers']:
                name = trigger['name']
                trigger_counts[name] = trigger_counts.get(name, 0) + 1
            
            for symptom in analysis_data['symptoms']:
                name = symptom['name']
                severity = symptom['severity']
                if name not in symptom_severities:
                    symptom_severities[name] = []
                symptom_severities[name].append(severity)
            
            # Calculate average severities
            avg_severities = {}
            for symptom, severities in symptom_severities.items():
                avg_severities[symptom] = sum(severities) / len(severities)
            
            analysis_data['patterns'] = {
                'most_used_products': sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                'most_common_triggers': sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                'average_symptom_severities': avg_severities
            }
            
            return json.dumps(analysis_data, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error preparing logs for analysis: {e}")
            return "Error processing user data for analysis."