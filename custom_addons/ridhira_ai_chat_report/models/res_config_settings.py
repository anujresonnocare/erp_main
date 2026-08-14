# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ridhira_llm_provider = fields.Selection([
        ('openai', 'OpenAI'),
        ('gemini', 'Google Gemini'),
        ('anthropic', 'Anthropic')
    ], string="LLM Provider", default='gemini', config_parameter='ridhira_ai_chat_report.llm_provider')
    
    ridhira_openai_api_key = fields.Char(string="OpenAI API Key", config_parameter='ridhira_ai_chat_report.openai_api_key')
    ridhira_gemini_api_key = fields.Char(string="Gemini API Key", config_parameter='ridhira_ai_chat_report.gemini_api_key')
    ridhira_anthropic_api_key = fields.Char(string="Anthropic API Key", config_parameter='ridhira_ai_chat_report.anthropic_api_key')
