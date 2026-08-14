# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json
import requests

class AiReportQuery(models.Model):
    _name = 'ai.report.query'
    _description = 'AI Report Query'

    name = fields.Char(string='Query Name', required=True)
    user_prompt = fields.Text(string='User Prompt', required=True)
    model_name = fields.Char(string='Target Model')
    domain = fields.Text(string='Domain (JSON)')
    fields_list = fields.Text(string='Fields (JSON)')
    groupby = fields.Text(string='Group By (JSON)')
    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('line', 'Line Chart'),
        ('pivot', 'Pivot Table'),
    ], string='Chart Type', default='bar')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    def _get_llm_response(self, prompt):
        provider = self.env['ir.config_parameter'].sudo().get_param('ridhira_ai_chat_report.llm_provider', 'gemini')
        
        if provider == 'openai':
            api_key = self.env['ir.config_parameter'].sudo().get_param('ridhira_ai_chat_report.openai_api_key')
            if not api_key:
                raise UserError(_("OpenAI API Key is not configured."))
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise UserError(_("OpenAI API Error: %s") % response.text)
                
        elif provider == 'gemini':
            api_key = self.env['ir.config_parameter'].sudo().get_param('ridhira_ai_chat_report.gemini_api_key')
            if not api_key:
                raise UserError(_("Gemini API Key is not configured."))
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                raise UserError(_("Gemini API Error: %s") % response.text)
                
        elif provider == 'anthropic':
            api_key = self.env['ir.config_parameter'].sudo().get_param('ridhira_ai_chat_report.anthropic_api_key')
            if not api_key:
                raise UserError(_("Anthropic API Key is not configured."))
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            prompt = prompt + "\nRespond with ONLY valid JSON."
            payload["messages"][0]["content"] = prompt
            
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data['content'][0]['text']
            else:
                raise UserError(_("Anthropic API Error: %s") % response.text)

        raise UserError(_("Invalid LLM Provider configured."))

    @api.model
    def action_generate_query(self, user_prompt):
        """
        Translates user prompt into Odoo ORM parameters.
        Returns a dict with domain, fields, groupby, model_name, and chart_type.
        """
        # Step 1: Identify Target Model
        step1_prompt = f"""
        You are an Odoo expert. The user wants to generate a report based on this query: "{user_prompt}"
        Identify the primary Odoo model they are referring to (e.g., 'sale.order', 'purchase.order', 'account.move', 'crm.lead').
        Return ONLY a JSON object with the key "model_name". For example: {{"model_name": "sale.order"}}
        """
        
        step1_res = self._get_llm_response(step1_prompt)
        try:
            model_name = json.loads(step1_res).get('model_name')
        except Exception:
            raise UserError(_("Failed to parse LLM response for model identification."))
            
        if not model_name or model_name not in self.env:
            raise UserError(_("Could not identify a valid Odoo model from your query."))
            
        # Step 2: Fetch fields for the model to provide context
        fields_info = self.env['ir.model.fields'].search_read(
            [('model', '=', model_name), ('ttype', 'in', ['char', 'integer', 'float', 'monetary', 'many2one', 'selection', 'date', 'datetime'])],
            ['name', 'field_description', 'ttype']
        )
        
        fields_context = [{"name": f['name'], "desc": f['field_description'], "type": f['ttype']} for f in fields_info]
        fields_context_str = json.dumps(fields_context[:100]) # Cap at 100 fields
        
        step2_prompt = f"""
        You are an Odoo ORM expert. The user wants a report based on this query: "{user_prompt}"
        The target model is '{model_name}'.
        Here are the available fields: {fields_context_str}
        
        Generate a JSON object with the following keys:
        - "domain": A valid Odoo domain list (e.g., [("state", "=", "sale")]). If no filter is needed, use [].
        - "fields_list": A list of field names to read. Must include any field used in groupby and any numeric field to measure. (e.g., ["partner_id", "amount_total"]).
        - "groupby": A list of field names to group by. (e.g., ["partner_id"]). If none, use [].
        - "chart_type": One of "bar", "pie", "line", "pivot".
        
        Return ONLY the JSON object.
        """
        
        step2_res = self._get_llm_response(step2_prompt)
        try:
            query_data = json.loads(step2_res)
        except Exception:
            raise UserError(_("Failed to parse LLM response for query generation."))
            
        model_fields = self.env[model_name].fields_get()
        valid_fields = [f for f in query_data.get('fields_list', []) if f in model_fields]
        valid_groupby = [g for g in query_data.get('groupby', []) if g in model_fields]
        
        if not valid_fields:
            valid_fields = ['display_name']
            
        return {
            'model_name': model_name,
            'domain': query_data.get('domain', []),
            'fields_list': valid_fields,
            'groupby': valid_groupby,
            'chart_type': query_data.get('chart_type', 'bar')
        }
