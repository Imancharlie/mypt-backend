import openai
from django.conf import settings
from apps.reports.models import AIEnhancementLog
import json


class AIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
        self.max_tokens = getattr(settings, 'OPENAI_MAX_TOKENS', 2000)
    
    def enhance_text(self, text, enhancement_type='improve', user=None):
        """
        Enhance text using OpenAI GPT
        enhancement_type: 'improve', 'expand', 'summarize', 'grammar'
        """
        prompts = {
            'improve': f"Improve the following text for a professional industrial training report. Make it more detailed and technical while maintaining accuracy:\n\n{text}",
            'expand': f"Expand the following text with more technical details and professional language suitable for an industrial training report:\n\n{text}",
            'summarize': f"Create a concise professional summary of the following content for an industrial training report:\n\n{text}",
            'grammar': f"Correct grammar and improve the professional tone of the following text:\n\n{text}"
        }
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional technical writing assistant specializing in industrial training reports. Provide clear, concise, and technically accurate improvements."},
                    {"role": "user", "content": prompts.get(enhancement_type, prompts['improve'])}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            enhanced_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            # Log the enhancement
            if user:
                AIEnhancementLog.objects.create(
                    user=user,
                    content_type='GENERAL',
                    original_text=text[:1000],  # Truncate for storage
                    enhanced_text=enhanced_text[:1000],
                    prompt_used=prompts.get(enhancement_type, prompts['improve'])[:500],
                    tokens_consumed=tokens_used,
                    enhancement_type=enhancement_type
                )
            
            return {
                'success': True,
                'enhanced_text': enhanced_text,
                'tokens_used': tokens_used,
                'original_length': len(text),
                'enhanced_length': len(enhanced_text)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_text': text
            }
    
    def generate_weekly_summary(self, daily_reports, user=None):
        """Generate weekly summary from daily reports"""
        daily_content = []
        for report in daily_reports:
            daily_content.append(f"Day {report.date.strftime('%A')}: {report.description} (Hours: {report.hours_spent})")
        
        combined_text = "\n".join(daily_content)
        prompt = f"Create a professional weekly summary for an industrial training report based on these daily activities:\n\n{combined_text}\n\nFocus on key achievements, skills learned, and overall progress."
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are creating weekly summaries for industrial training reports. Focus on technical skills, practical experience, and professional development."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.6
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Log the generation
            if user:
                AIEnhancementLog.objects.create(
                    user=user,
                    content_type='WEEKLY',
                    original_text=combined_text[:1000],
                    enhanced_text=summary[:1000],
                    prompt_used=prompt[:500],
                    tokens_consumed=response.usage.total_tokens,
                    enhancement_type='summary'
                )
            
            return {
                'success': True,
                'summary': summary,
                'tokens_used': response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def suggest_improvements(self, report_text, report_type='general'):
        """Suggest specific improvements for reports"""
        prompt = f"Analyze the following {report_type} training report and suggest 5 specific improvements to make it more professional and comprehensive:\n\n{report_text}"
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional technical writing reviewer. Provide specific, actionable suggestions for improving industrial training reports."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.5
            )
            
            suggestions = response.choices[0].message.content.strip()
            
            return {
                'success': True,
                'suggestions': suggestions,
                'tokens_used': response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 