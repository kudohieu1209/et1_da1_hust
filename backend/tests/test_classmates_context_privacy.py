"""Synthetic roster sentinels must never enter assistant context or Gemini prompts."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from app.rag.gemini_service import GeminiService
from app.services.chatbot_service import chatbot_service
from app.services.data_loader import data_loader
from app.services.profile_repository import MongoProfileRepository
from testing_support import isolated_database, sample_profiles


ROSTER = {'records': [{'student_id': '20999999', 'student_name': 'PRIVATE_ROSTER_SENTINEL',
                       'class_name': 'Test class', 'email': 'private-roster@example.test'}]}


class ClassmatesContextPrivacyTests(unittest.TestCase):
    def assert_no_roster(self, context):
        text = json.dumps(context, ensure_ascii=False)
        for marker in ('classmates', 'PRIVATE_ROSTER_SENTINEL', '20999999', 'private-roster@example.test'):
            self.assertNotIn(marker, text)

    def test_chatbot_audit_does_not_include_the_stored_classmates_section(self):
        profile = sample_profiles()['20220001']
        profile['school_services'] = {'classmates': copy.deepcopy(ROSTER)}
        repository = MongoProfileRepository(isolated_database())
        repository.save('20220001', profile)
        with mock.patch.object(data_loader, '_profiles', repository):
            token = data_loader.enter_scope(data_loader.load_scope_state('20220001'))
            try:
                result = chatbot_service.process_message('Xem tiến độ học tập của mình')
            finally:
                data_loader.exit_scope(token)
        self.assertEqual(result['intent'], 'DEGREE_AUDIT')
        self.assert_no_roster(result['data_context'])
        self.assertIn('cpa', result['data_context'])

    def test_chatbot_drops_rosters_from_nested_context_and_conversation_focus(self):
        context = {'profile': {'school_services': {'classmates': ROSTER}},
                   'alternatives': [{'classmates': ROSTER, 'course_code': 'MI1111'}]}
        history = [{'role': 'assistant', 'content': 'Câu trả lời kiểm thử', 'data_context': {
            'conversation_context': {'course_codes': [], 'topic_query': '', 'classmates': ROSTER}}}]
        before = copy.deepcopy((context, history))
        with mock.patch.object(chatbot_service, '_process_message', return_value={
                'reply': 'Chào bạn', 'intent': 'SMALL_TALK', 'data_context': context}):
            result = chatbot_service.process_message('chào bạn', history)
        self.assert_no_roster(result['data_context'])
        self.assertEqual(result['data_context']['alternatives'][0]['course_code'], 'MI1111')
        self.assertEqual((context, history), before)

    def test_gemini_prompt_omits_classmates_but_keeps_owner_academic_context(self):
        service = GeminiService.__new__(GeminiService)
        service.api_key = 'fake-test-key'
        service.model_name = 'test-model'
        service.fallback_model = ''
        service.client = mock.Mock()
        service.client.models.generate_content.return_value = SimpleNamespace(text='Đã xử lý [[NGUON: 0]]')
        context = {'classmates': ROSTER, 'school_services': {'classmates': ROSTER},
                   'transcript': [{'code': 'MI1111', 'letter_grade': 'B'}],
                   'nested': [{'classmates': ROSTER, 'cpa': 3.0}]}
        before = copy.deepcopy(context)
        result = service.generate_response('Tư vấn học tập', structured_data=context)
        self.assertTrue(result['success'])
        prompt = service.client.models.generate_content.call_args.kwargs['contents']
        self.assert_no_roster(prompt)
        self.assertIn('MI1111', prompt)
        self.assertIn('transcript', prompt)
        self.assertEqual(context, before)

    def test_gemini_fallback_receives_only_sanitized_context(self):
        service = GeminiService.__new__(GeminiService)
        service.client = None
        context = {'school_services': {'classmates': ROSTER}, 'cpa': 3.0}
        with mock.patch.object(service, '_fallback_synthesis', return_value={}) as fallback:
            service.generate_response('Tư vấn học tập', structured_data=context)
        self.assert_no_roster(fallback.call_args.args[2])
        self.assertEqual(fallback.call_args.args[2]['cpa'], 3.0)
