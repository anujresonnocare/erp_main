# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from unittest.mock import patch
import json

class TestAiQuery(TransactionCase):

    def setUp(self):
        super(TestAiQuery, self).setUp()
        self.AiReportQuery = self.env['ai.report.query']

    def test_basic_instantiation(self):
        """
        Verify basic model structure and default values.
        """
        query_record = self.AiReportQuery.create({
            'name': 'Test Query',
            'user_prompt': 'Show me sales from last 30 days',
        })
        self.assertEqual(query_record.name, 'Test Query')
        self.assertEqual(query_record.chart_type, 'bar')
        
    def test_missing_api_key(self):
        """
        Test that action_generate_query fails gracefully when no API keys are configured
        and it tries to actually hit the LLM.
        """
        query_record = self.AiReportQuery.create({
            'name': 'Test Missing Key',
            'user_prompt': 'Hello',
        })
        with self.assertRaises(UserError):
            query_record.action_generate_query(query_record.user_prompt)

    @patch('odoo.addons.ridhira_ai_chat_report.models.ai_report_query.AiReportQuery._get_llm_response')
    def test_usecase_grouped_pie_chart(self, mock_get_llm_response):
        """
        Use Case: "Show me partners grouped by country as a pie chart"
        (Using res.partner to guarantee it runs on base Odoo without 'sale' installed)
        """
        mock_get_llm_response.side_effect = [
            json.dumps({"model_name": "res.partner"}), # Step 1 response
            json.dumps({
                "domain": [],
                "fields_list": ["name", "country_id"],
                "groupby": ["country_id"],
                "chart_type": "pie"
            }) # Step 2 response
        ]
        
        query_record = self.AiReportQuery.create({
            'name': 'Partners by Country',
            'user_prompt': 'Show me partners grouped by country as a pie chart',
        })
        
        result = query_record.action_generate_query(query_record.user_prompt)
        
        self.assertEqual(result['model_name'], 'res.partner')
        self.assertEqual(result['chart_type'], 'pie')
        self.assertIn('country_id', result['groupby'])
        
    @patch('odoo.addons.ridhira_ai_chat_report.models.ai_report_query.AiReportQuery._get_llm_response')
    def test_usecase_pivot_table(self, mock_get_llm_response):
        """
        Use Case: "Show me active users grouped by company in a pivot table"
        """
        mock_get_llm_response.side_effect = [
            json.dumps({"model_name": "res.users"}), 
            json.dumps({
                "domain": [["active", "=", True]],
                "fields_list": ["name", "company_id"],
                "groupby": ["company_id"],
                "chart_type": "pivot"
            })
        ]
        
        query_record = self.AiReportQuery.create({
            'name': 'Users Pivot',
            'user_prompt': 'Show me active users grouped by company in a pivot table',
        })
        
        result = query_record.action_generate_query(query_record.user_prompt)
        
        self.assertEqual(result['model_name'], 'res.users')
        self.assertEqual(result['chart_type'], 'pivot')
        self.assertIn('company_id', result['groupby'])
        self.assertEqual(result['domain'], [["active", "=", True]])

    @patch('odoo.addons.ridhira_ai_chat_report.models.ai_report_query.AiReportQuery._get_llm_response')
    def test_usecase_invalid_model(self, mock_get_llm_response):
        """
        Use Case: User types gibberish or LLM hallucinates a non-existent model
        """
        mock_get_llm_response.side_effect = [
            json.dumps({"model_name": "fake.model.that.does.not.exist"}), 
        ]
        
        query_record = self.AiReportQuery.create({
            'name': 'Invalid Model Query',
            'user_prompt': 'asdasdasd',
        })
        
        with self.assertRaisesRegex(UserError, "Could not identify a valid Odoo model"):
            query_record.action_generate_query(query_record.user_prompt)
